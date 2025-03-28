import json
import kubernetes
import logging

from .models import Namespace
from core.settings import env
from django.utils import timezone
from time import time, sleep

from apps.users.models import User

with open('apps/infra/charts/vm.json') as f:
    VM_TEMPLATE = json.load(f)

# Distro -> Image tag
IMAGE_TAGS = {
    'ubuntu-23.10-server-cloudimg': 'image-t5gzn',
    'windows-10-22h2': 'image-dccfr',
}

NETWORKS = {
    'private': {
        "affinity": False,
    },
    'vlab': {
        "affinity": True,
        "label": 'network.harvesterhci.io/vlab',
    },
    'khepri': {
        "affinity": True,
        "label": 'network.harvesterhci.io/khepri',
    },
}

RESOURCE_TOL = 0.8


def create_secret(client: kubernetes.client, *, ns: str, secret_name: str, secret_data: dict) -> bool:
    v1 = kubernetes.client.CoreV1Api(client)
    secret_metadata = kubernetes.client.V1ObjectMeta(name=secret_name)
    secret_spec = kubernetes.client.V1Secret(metadata=secret_metadata, data=secret_data)
    try:
        v1.create_namespaced_secret(namespace=ns, body=secret_spec)
        return True
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:
            logging.error(f"Secret {secret_name} already exists in namespace {ns}")
        else:
            logging.exception(f"Error creating secret {secret_name} in namespace {ns}: {e}")
        return False


def create_pvc(v1: kubernetes.client, *, ns: str, pvc_name: str, pvc_size: str, pvcid: str,
               image: str = '') -> str | None:
    metadata = {
        "namespace": ns,
        "name": pvc_name,
        "labels": {
            "pvcid": pvcid,
        }
    }

    if image:
        metadata["annotations"] = {"harvesterhci.io/imageId": f"harvester-public/{IMAGE_TAGS[image]}"},

    claim_spec = {
        "access_modes": ["ReadWriteMany"],
        "storage_class_name": f"longhorn-{IMAGE_TAGS[image]}" if image else "longhorn",
        "resources": v1.V1ResourceRequirements(requests={"storage": f"{pvc_size}Gi"}),
        "volume_mode": "Block",
    }

    metadata = v1.V1ObjectMeta(**metadata)
    claim_spec = v1.V1PersistentVolumeClaimSpec(**claim_spec)
    pvc = v1.V1PersistentVolumeClaim(metadata=metadata, spec=claim_spec)

    try:
        v1.CoreV1Api().create_namespaced_persistent_volume_claim(namespace=ns, body=pvc)
        return pvc_name
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:
            logging.error(f"PVC {pvc_name} already exists in namespace {ns}")
        else:
            logging.exception(f"Error creating PVC {pvc_name} in namespace {ns}: {e}")
        return None


def get_vol_claim_templ(*, pvc_disk_name: str, distro: str, size: int) -> dict:
    """
    params:
    disk_name: str Main existing disk name (eg test-1-disk-abcde)
    image: str Image name (eg ubuntu-23.10-server-cloudimg)
    size: int Size of the disk in GB
    """
    if 'windows' in distro:
        pass
    else:
        return {
            "metadata": {
                "name": pvc_disk_name,
                "annotations": {
                    "harvesterhci.io/imageId": f"harvester-public/{IMAGE_TAGS[distro]}"
                }
            },
            "spec": {
                "accessModes": [
                    "ReadWriteMany"
                ],
                "resources": {
                    "requests": {
                        "storage": f"{size}Gi"
                    }
                },
                "volumeMode": "Block",
                "storageClassName": f"longhorn-{IMAGE_TAGS[distro]}"
            }
        }


def get_disk_spec(*, d_name: str, boot_order: int, bus: str = 'virtio') -> dict:
    return {
        "name": d_name,
        "disk": {
            "bus": bus
        },
        "bootOrder": boot_order,
    }


def get_interface_spec(*, n_provider: str, mac_address: str) -> dict:
    return {
        n_provider: {},
        "macAddress": mac_address,
        "model": "virtio",
        "name": "default"
    }


def get_network_config(*, n_name: str) -> dict:
    network = {
        "name": "default",
    }
    if n_name == 'private':
        network['pod'] = {}
    else:
        network['multus'] = {
            "networkName": f"harvester-public/{n_name}"
        }
    return network


def get_vol_config(*, d_name: str, pvc_name: str = '', secret_name: str = ''):
    if d_name == 'cloudinitdisk':
        return {
            "name": "cloudinitdisk",
            "cloudInitNoCloud": {
                "secretRef": {
                    "name": secret_name
                },
                # "networkDataSecretRef": {
                #     "name": secret_name
                # }
            }
        }
    else:
        return {
            "name": d_name,
            "persistentVolumeClaim": {
                "claimName": pvc_name
            }
        }


def get_affinity(*, n_name: str) -> dict:
    if NETWORKS[n_name]['affinity']:
        return {
            "requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [
                    {
                        "matchExpressions": [
                            {
                                "key": NETWORKS[n_name]['label'],
                                "operator": "In",
                                "values": [
                                    "true"
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    return {}


def fill_vm_template(*, ns: str, name: str, memory: int, disk: int, distro: str, vmid: str,
                     create_time: timezone, cpu: int, network_name: str, mac_address: str, hostname: str,
                     cloudinit_secret: str, pvc_name: str) -> dict:
    with open('apps/infra/charts/vm.json') as f:
        vm_template = json.load(f)

    # vm_template = deepcopy(VM_TEMPLATE)

    vm_template['metadata']['namespace'] = ns

    vm_template['metadata']['name'] = name

    vm_template['metadata']['annotations']['harvesterhci.io/volumeClaimTemplates'] = (
        json.dumps([
            get_vol_claim_templ(pvc_disk_name=pvc_name, distro=distro, size=disk)
        ]))

    vm_template['metadata']['labels']['harvesterhci.io/os'] = 'windows' if 'windows' in distro else 'linux'

    vm_template['metadata']['labels']['vmid'] = vmid
    vm_template['metadata']['labels']['distro'] = distro

    vm_template['spec']['template']['metadata']['creationTimestamp'] = create_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    vm_template['spec']['template']['metadata']['labels']['harvesterhci.io/vmName'] = name

    vm_template['spec']['template']['spec']['domain']['cpu']['cores'] = cpu
    vm_template['spec']['template']['spec']['domain']['cpu']['sockets'] = 1
    vm_template['spec']['template']['spec']['domain']['cpu']['threads'] = 1

    vm_template['spec']['template']['spec']['domain']['devices']['disks'] = \
        [
            get_disk_spec(d_name=dn, boot_order=order + 1) for order, dn in enumerate(['rootdisk', 'cloudinitdisk'])
        ]

    vm_template['spec']['template']['spec']['domain']['devices']['interfaces'] = \
        [
            get_interface_spec(n_provider='masquerade' if network_name == 'private' else 'bridge',
                               mac_address=mac_address)
        ]

    vm_template['spec']['template']['spec']['domain']['memory']['guest'] = f"{memory}G"

    vm_template['spec']['template']['spec']['domain']['firmware']['serial'] = vmid

    vm_template['spec']['template']['spec']['domain']['resources']['limits']['cpu'] = cpu
    vm_template['spec']['template']['spec']['domain']['resources']['limits']['memory'] = f"{memory}G"

    vm_template['spec']['template']['spec']['domain']['resources']['requests']['cpu'] = f"{cpu * RESOURCE_TOL}"
    vm_template['spec']['template']['spec']['domain']['resources']['requests']['memory'] = \
        f"{int(memory * 1000 * RESOURCE_TOL)}M"

    vm_template['spec']['template']['spec']['networks'] = \
        [
            get_network_config(n_name=network_name)
        ]

    vm_template['spec']['template']['spec']['hostname'] = hostname
    vm_template['spec']['template']['spec']['volumes'] = \
        [
            get_vol_config(d_name='cloudinitdisk', secret_name=cloudinit_secret),
            get_vol_config(d_name='rootdisk', pvc_name=pvc_name)
        ]

    vm_template['spec']['template']['spec']['affinity'] = get_affinity(n_name=network_name)

    return vm_template


def provision_vm(client: kubernetes.client, namespace: str, vm_name: str, cpu: int, memory: int, disk: int,
                 pvc_name: str, os: str, cloudinit_secret: str, create_time: str, mac_address: str, vm_id: int):
    values = {
        "namespace": namespace,
        "boot_spec": get_vol_claim_templ(pvc_name, os, disk),
        "os": os,
        "vm_id": vm_id,
        "vm_name": vm_name,
        "create_time": create_time,
        "mac_address": mac_address,
        "cpu": cpu,
        "memory": memory,
        "pvc_name": pvc_name,
        "cloudinit_secret": cloudinit_secret,
    }

    v1 = kubernetes.client.CustomObjectsApi(client)

    try:
        v1.create_namespaced_custom_object(
            body='',
            namespace=namespace,
            group="kubevirt.io",
            version="v1",
            plural="virtualmachines",
        )

    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:
            logging.error(f"VM {vm_name} already exists in namespace {namespace}")
        else:
            logging.exception(f"Error creating VM {vm_name} in namespace {namespace}: {e}")
        return False


# def create_vm(spec: dict, user: User):
#     create_t = timezone.now()
#     vmid = str(uuid.uuid4())
#     disk_name = f"{spec['k8sName']}-disk-0-{random_str(4)}"
#     spec['network_type'] = 'khepri' if spec['network_type'] == 'public' else spec['network_type']
#
#     vm_template = fill_vm_template(
#         ns=user.namespace.all().first().name,
#         name=spec['k8sName'],
#         memory=spec['ram'],
#         disk=spec['disk'],
#         distro=spec['os'],
#         vmid=vmid,
#         create_time=create_t,
#         cpu=spec['cpu'],
#         network_name=spec['network_type'],
#         mac_address=spec['mac'],
#         hostname=spec['k8sName'],
#         cloudinit_secret=spec['k8sName'],
#         pvc_name=spec['pvc_name'],
#     )
#
#     # pprint(vm_template)
#
#     with open("vm_template.yaml", 'w') as f:
#         yaml.dump(vm_template, f)


def gen_ns_network_policy(nsid: str) -> kubernetes.client.V1NetworkPolicy:
    network_policy = kubernetes.client.V1NetworkPolicy(
        api_version="networking.k8s.io/v1",
        kind="NetworkPolicy",
        metadata=kubernetes.client.V1ObjectMeta(
            name="net-policy-0",
            namespace=nsid
        ),
        spec=kubernetes.client.V1NetworkPolicySpec(
            pod_selector=kubernetes.client.V1LabelSelector(
                match_labels={}
            ),
            policy_types=["Ingress", "Egress"],
            ingress=[
                # Allow ingress from traefik and osiris-net namespaces
                kubernetes.client.V1NetworkPolicyIngressRule(
                    _from=[
                        # Allow from traefik namespace
                        kubernetes.client.V1NetworkPolicyPeer(
                            namespace_selector=kubernetes.client.V1LabelSelector(
                                match_labels={
                                    "kubernetes.io/metadata.name": "traefik"
                                }
                            )
                        ),
                        # Allow from osiris-net namespace
                        kubernetes.client.V1NetworkPolicyPeer(
                            namespace_selector=kubernetes.client.V1LabelSelector(
                                match_labels={
                                    "kubernetes.io/metadata.name": "osiris-net"
                                }
                            )
                        ),
                        # Allow from same namespace
                        kubernetes.client.V1NetworkPolicyPeer(
                            namespace_selector=kubernetes.client.V1LabelSelector(
                                match_labels={
                                    "kubernetes.io/metadata.name": nsid
                                }
                            )
                        )
                    ]
                )
            ],
            egress=[
                # Allow DNS resolution
                kubernetes.client.V1NetworkPolicyEgressRule(
                    to=[
                        kubernetes.client.V1NetworkPolicyPeer(
                            namespace_selector=kubernetes.client.V1LabelSelector(
                                match_labels={"kubernetes.io/metadata.name": "kube-system"}
                            ),
                            pod_selector=kubernetes.client.V1LabelSelector(
                                match_labels={"k8s-app": "kube-dns"}
                            )
                        )
                    ],
                    ports=[
                        kubernetes.client.V1NetworkPolicyPort(port=53, protocol="UDP"),
                        kubernetes.client.V1NetworkPolicyPort(port=53, protocol="TCP")
                    ]
                ),
                # Allow internet access
                kubernetes.client.V1NetworkPolicyEgressRule(
                    to=[
                        kubernetes.client.V1NetworkPolicyPeer(
                            ip_block=kubernetes.client.V1IPBlock(
                                cidr="0.0.0.0/0",
                                _except=[
                                    "10.0.79.0/24",  # Block internal network
                                ]
                            )
                        )
                    ]
                ),
                # Allow same namespace communication
                kubernetes.client.V1NetworkPolicyEgressRule(
                    to=[
                        kubernetes.client.V1NetworkPolicyPeer(
                            namespace_selector=kubernetes.client.V1LabelSelector(
                                match_labels={
                                    "kubernetes.io/metadata.name": nsid
                                }
                            )
                        )
                    ]
                )
            ]
        )
    )
    return network_policy


def create_namespace(nsid) -> bool:
    if env.k8s_api_client is None:
        return False

    core_v1 = kubernetes.client.CoreV1Api(env.k8s_api_client)
    networking_v1 = kubernetes.client.NetworkingV1Api(env.k8s_api_client)
    namespace_metadata = kubernetes.client.V1ObjectMeta(name=nsid)
    namespace_spec = kubernetes.client.V1Namespace(metadata=namespace_metadata)
    net_policy = gen_ns_network_policy(nsid)

    try:
        core_v1.create_namespace(body=namespace_spec)
        networking_v1.create_namespaced_network_policy(namespace=nsid, body=net_policy)
        return True
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:
            return True
        return False


def k8s_delete_namespace(nsid) -> bool:
    if env.k8s_api_client is None:
        return False

    core_v1 = kubernetes.client.CoreV1Api(env.k8s_api_client)
    networking_v1 = kubernetes.client.NetworkingV1Api(env.k8s_api_client)

    try:
        core_v1.delete_namespace(name=nsid)
        networking_v1.delete_namespaced_network_policy(name='net-policy-0', namespace=nsid)
        return True
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            return True
        return False
