import kubernetes
import logging

from base64 import b64encode
from datetime import datetime

from core.settings import env

from .models import Container, ContainerApp
from ..secret_store.models import Secret

from ..infra.constants import RESTART_POLICIES, NYU_SUBNETS


class AppResource:
    def __init__(self, app: ContainerApp):
        self.apps_v1 = kubernetes.client.AppsV1Api(env.k8s_api_client)
        self.core_v1 = kubernetes.client.CoreV1Api(env.k8s_api_client)
        self.networking_v1 = kubernetes.client.NetworkingV1Api(env.k8s_api_client)
        self.custom_objects = kubernetes.client.CustomObjectsApi(env.k8s_api_client)
        self.app = app
        self.containers = app.containers.all()
        self.main_container = app.containers.get(type='main')
        self.volumes = app.volumes.all()
        self.nsid = app.namespace.nsid
        self.ip_rule = app.ip_rule

        self.pull_secrets = set()

    def apply(self):
        self.create_pull_secrets()
        self.delete_pvc()
        self.create_pvc()
        self.create_secrets()
        self.create_deployment()
        self.create_service()
        self.create_fw_rules()
        self.create_ingress()
        self.create_autoscaler()
        self.app.state = 'active'
        self.app.save()

    def delete(self):
        try:
            self.app.state = 'deleting'
            self.app.save()

            self.delete_pvc(del_all=True)
            self.core_v1.delete_namespaced_service(name=f'svc-{self.app.appid}', namespace=self.nsid)
            self.custom_objects.delete_namespaced_custom_object(name=f"ingress-{self.app.appid}",
                                                                group="traefik.io",
                                                                version="v1alpha1",
                                                                namespace=self.nsid,
                                                                plural="ingressroutes")
            self.custom_objects.delete_namespaced_custom_object(name=f"scaler-{self.app.appid}",
                                                                group="keda.sh",
                                                                version="v1alpha1",
                                                                namespace=self.nsid,
                                                                plural="scaledobjects")
            self.custom_objects.delete_namespaced_custom_object(name=f"fw-rules-{self.app.appid}",
                                                                group="traefik.io",
                                                                version="v1alpha1",
                                                                namespace=self.nsid,
                                                                plural="middlewares")
            self.apps_v1.delete_namespaced_deployment(name=f'app-{self.app.appid}', namespace=self.nsid)

            for container in self.app.containers.all():
                container.delete()
            for custom_domain in self.app.custom_domains.all():
                custom_domain.delete()
            self.app.delete()

        except kubernetes.client.exceptions.ApiException as e:
            logging.error(f"Failed to delete app {self.app.appid}", exc_info=True)
            raise e

    def create_pull_secrets(self):
        secrets = set()
        ocr_auths = dict()

        for container in self.containers:
            if container.pull_secret:
                secrets.add(container.pull_secret.secretid)

            elif crid := container.metadata.get('crid'):  # Osiris Container Registry
                if crid not in ocr_auths:
                    ocr_auths[crid] = container.gen_oc_auth_data()

        def create(name, data=None):
            secret_spec = None
            try:
                secret_spec = kubernetes.client.V1Secret(
                    metadata=kubernetes.client.V1ObjectMeta(
                        name=name,
                        namespace=self.nsid
                    ),
                    type='kubernetes.io/dockerconfigjson',
                    data=data,
                )
                self.core_v1.create_namespaced_secret(namespace=self.nsid, body=secret_spec)

            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 409:
                    self.core_v1.replace_namespaced_secret(
                        name=name,
                        namespace=self.nsid,
                        body=secret_spec
                    )
                else:
                    logging.error(f"Failed to create secret {name}", exc_info=True)
                    raise e
            finally:
                self.pull_secrets.add(name)

        for secretid in secrets:
            user_secret = Secret.objects.get(secretid=secretid)
            auth_data_str = user_secret.values().get('.dockerconfigjson')

            if not auth_data_str:
                continue

            auth_data = b64encode(auth_data_str.encode()).decode()
            create('pull-secret-' + secretid, data={".dockerconfigjson": auth_data})

        for crid, auth_data in ocr_auths.items():
            create('pull-secret-' + crid, data={".dockerconfigjson": auth_data})

    def create_secrets(self):
        secrets = set()

        # Create volume secrets
        for vol in self.app.volumes.all():
            if vol.type != 'secret':
                continue

            try:
                user_secret = Secret.objects.get(secretid=vol.metadata.get('secretid'))
            except Secret.DoesNotExist:
                continue

            secret_spec = kubernetes.client.V1Secret(
                metadata=kubernetes.client.V1ObjectMeta(
                    name='secret-' + user_secret.secretid,
                    namespace=self.nsid
                ),
                type='Opaque',
                string_data=user_secret.data
            )

            try:
                secret = self.core_v1.create_namespaced_secret(namespace=self.nsid, body=secret_spec)
                secrets.add(secret)
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 409:
                    secret = self.core_v1.replace_namespaced_secret(
                        name='secret-' + user_secret.secretid,
                        namespace=self.nsid,
                        body=secret_spec
                    )
                    secrets.add(secret)
                else:
                    logging.error(f"Failed to create secret secret-{user_secret.secretid}", exc_info=True)
                    raise e

        # Create env secrets
        for container in self.app.containers.all():
            if container.env_secret:
                try:
                    user_secret = Secret.objects.get(secretid=container.env_secret.secretid)
                except Secret.DoesNotExist:
                    continue

                secret_spec = kubernetes.client.V1Secret(
                    metadata=kubernetes.client.V1ObjectMeta(
                        name='secret-' + container.env_secret.secretid,
                        namespace=self.nsid
                    ),
                    type='Opaque',
                    string_data=user_secret.data
                )

                try:
                    secret = self.core_v1.create_namespaced_secret(namespace=self.nsid, body=secret_spec)
                    secrets.add(secret)
                except kubernetes.client.exceptions.ApiException as e:
                    if e.status == 409:
                        secret = self.core_v1.replace_namespaced_secret(
                            name='secret-' + container.env_secret.secretid,
                            namespace=self.nsid,
                            body=secret_spec
                        )
                        secrets.add(secret)
                    else:
                        logging.error(f"Failed to create secret secret-{container.env_secret.secretid}", exc_info=True)
                        raise e

        return list(secrets)

    def create_pvc(self) -> list[kubernetes.client.V1PersistentVolumeClaim]:
        pvcs = []
        for vol in self.volumes:
            if vol.type not in ('block', 'fs'):
                continue

            pvc_spec = kubernetes.client.V1PersistentVolumeClaim(
                metadata=kubernetes.client.V1ObjectMeta(
                    name='vol-' + vol.volid,
                    namespace=self.nsid
                ),
                spec=kubernetes.client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteMany", "ReadWriteOnce"],
                    volume_mode="Block" if vol.type == 'block' else "Filesystem",
                    resources=kubernetes.client.V1ResourceRequirements(
                        requests={"storage": f"{vol.size}Gi"}
                    ),
                    storage_class_name="ceph-rbd"
                )
            )
            try:
                pvc = self.core_v1.create_namespaced_persistent_volume_claim(namespace=self.nsid, body=pvc_spec)
                pvcs.append(pvc)
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 409:
                    pass
                else:
                    logging.error(f"Failed to create pvc vol-{vol.volid}", exc_info=True)
                    raise e

        return pvcs

    def delete_pvc(self, del_all=False):
        volumes_to_delete = self.app.metadata.get('volumes_to_del', [])

        if del_all:
            volumes_to_delete += [vol.volid for vol in self.volumes]

        for volid in volumes_to_delete:
            try:
                vol = self.volumes.get(volid=volid)
                if vol.type in ('block', 'fs'):
                    self.core_v1.delete_namespaced_persistent_volume_claim(name='vol-' + volid, namespace=self.nsid)

                vol.delete()
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    continue
                else:
                    logging.error(f"Failed to delete pvc vol-{volid}", exc_info=True)
                    raise e

    def gen_container_resource_spec(self, container: Container) -> kubernetes.client.V1ResourceRequirements:
        return kubernetes.client.V1ResourceRequirements(
            requests={
                'cpu': "{:.2f}".format(container.cpu / 2),
                'memory': "{:.2f}G".format(container.memory / 2)
            },
            limits={
                'cpu': "{:.2f}".format(container.cpu),
                'memory': "{:.2f}G".format(container.memory)
            }
        )

    def gen_container_port_spec(self, container: Container) -> list[kubernetes.client.V1ContainerPort]:
        ports = []
        if container.port:
            ports.append(
                kubernetes.client.V1ContainerPort(
                    container_port=container.port,
                    protocol=container.port_protocol.upper()
                )
            )
        return ports

    def gen_volume_mount_spec(self, container: Container) -> list[kubernetes.client.V1VolumeMount]:
        volume_mounts = []

        for vol in self.volumes:
            container_mode = vol.metadata.get('ca_mode', {}).get(container.type)
            if container_mode:
                if vol.type in ('block', 'fs'):
                    v_name = f"vol-{vol.volid}"
                elif vol.type == 'temp':
                    v_name = f"temp-{vol.volid}"
                elif vol.type == 'secret':
                    v_name = f"secret-{vol.metadata.get('secretid')}"
                else:
                    continue

                volume_mounts.append(
                    kubernetes.client.V1VolumeMount(
                        name=v_name,
                        mount_path=vol.mount_path,
                        read_only=(container_mode == 'ro')
                    )
                )

        return volume_mounts

    def gen_volume_spec(self) -> list[kubernetes.client.V1Volume]:
        volumes = []

        for volume in self.volumes:
            if volume.type in ('block', 'fs'):
                volumes.append(
                    kubernetes.client.V1Volume(
                        name=f"vol-{volume.volid}",
                        persistent_volume_claim=kubernetes.client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=f"vol-{volume.volid}"
                        )
                    )
                )
            elif volume.type == 'secret':
                volumes.append(
                    kubernetes.client.V1Volume(
                        name=f"secret-{volume.metadata['secretid']}",
                        secret=kubernetes.client.V1SecretVolumeSource(
                            secret_name=f"secret-{volume.metadata.get('secretid')}"
                        )
                    )
                )
            elif volume.type == 'temp':
                volumes.append(
                    kubernetes.client.V1Volume(
                        name=f"temp-{volume.volid}",
                        empty_dir=kubernetes.client.V1EmptyDirVolumeSource(medium='Memory', size_limit="100Mi")
                    )
                )

        return volumes

    def create_container_spec(self, container: Container) -> kubernetes.client.V1Container:
        container_spec = kubernetes.client.V1Container(
            name=f"{container.type}-{container.containerid}",
            image=container.image,
            image_pull_policy='Always',
            resources=self.gen_container_resource_spec(container),
            ports=self.gen_container_port_spec(container),
            volume_mounts=self.gen_volume_mount_spec(container),
        )

        if container.command:
            container_spec.command = container.command

        if container.args:
            container_spec.args = container.args

        if container.env_secret:
            container_spec.env_from = [
                kubernetes.client.V1EnvFromSource(
                    secret_ref=env.k8s_client.V1SecretEnvSource(
                        name='secret-' + container.env_secret.secretid
                    )
                )
            ]

        if container.pull_secret:
            container_spec.image_pull_secrets = [
                kubernetes.client.V1LocalObjectReference(name='pull-secret-' + container.pull_secret.secretid)
            ]

        elif crid := container.metadata.get('crid'):
            container_spec.image_pull_secrets = [
                kubernetes.client.V1LocalObjectReference(name='pull-secret-' + crid)
            ]

        return container_spec

    def gen_pull_secret_spec(self) -> list[kubernetes.client.V1LocalObjectReference]:
        return [kubernetes.client.V1LocalObjectReference(name=secretid) for secretid in self.pull_secrets]

    def create_deployment(self) -> kubernetes.client.V1Deployment:
        main_containers = [self.main_container]
        sidecar_containers = [c for c in self.containers if c.type == 'sidecar']
        init_containers = [c for c in self.containers if c.type == 'init']

        deployment = kubernetes.client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=kubernetes.client.V1ObjectMeta(
                name='app-' + self.app.appid,
                namespace=self.nsid,
                labels={'appid': self.app.appid}
            ),
            spec=kubernetes.client.V1DeploymentSpec(
                replicas=self.app.scaler.min_replicas,
                selector=kubernetes.client.V1LabelSelector(
                    match_labels={'appid': self.app.appid}
                ),
                template=kubernetes.client.V1PodTemplateSpec(
                    metadata=kubernetes.client.V1ObjectMeta(
                        labels={'appid': self.app.appid}
                    ),
                    spec=kubernetes.client.V1PodSpec(
                        runtime_class_name="kata-clh",
                        restart_policy=RESTART_POLICIES[self.app.restart_policy],
                        init_containers=[self.create_container_spec(c) for c in init_containers],
                        containers=[self.create_container_spec(c) for c in main_containers + sidecar_containers],
                        volumes=self.gen_volume_spec(),
                        image_pull_secrets=self.gen_pull_secret_spec()
                    )
                )
            )
        )

        try:
            return self.apps_v1.create_namespaced_deployment(namespace=self.nsid, body=deployment)
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 409:
                return self.apps_v1.replace_namespaced_deployment(name='app-' + self.app.appid,
                                                                  namespace=self.nsid,
                                                                  body=deployment
                                                                  )
            else:
                logging.error(f"Failed to create deployment app-{self.app.appid}", exc_info=True)
                raise e

    def create_service(self):
        port_config = {
            'port': self.main_container.port,
            'protocol': self.main_container.port_protocol.upper(),
            'target_port': self.main_container.port
        }

        if self.app.connection_protocol in ('tcp', 'udp'):
            port_config['node_port'] = self.app.connection_port

        service_spec = kubernetes.client.V1Service(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f'svc-{self.app.appid}',
                namespace=self.nsid,
                labels={'appid': self.app.appid}
            ),
            spec=kubernetes.client.V1ServiceSpec(
                type='ClusterIP' if self.app.connection_protocol == 'http' else 'NodePort',
                selector={'appid': self.app.appid},
                ports=[kubernetes.client.V1ServicePort(**port_config)],
                session_affinity='ClientIP'
            )
        )

        try:
            self.core_v1.create_namespaced_service(namespace=self.nsid, body=service_spec)
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 409:
                self.core_v1.replace_namespaced_service(name=f'svc-{self.app.appid}',
                                                        namespace=self.nsid,
                                                        body=service_spec
                                                        )
            else:
                logging.error(f"Failed to create service svc-{self.app.appid}", exc_info=True)
                raise e

    def create_fw_rules(self):
        if self.app.connection_protocol == 'http':
            ip_rules = {
                "apiVersion": "traefik.io/v1alpha1",
                "kind": "Middleware",
                "metadata": {
                    "name": "iprules-" + self.app.appid,
                    "namespace": self.nsid
                },
                "spec": {
                    "plugin": {
                        "iprules": {
                            "deny": self.ip_rule.deny,
                            "allow": self.ip_rule.allow,
                            "precedence": self.ip_rule.precedence
                        }
                    }
                }
            }

            middlewares = [ip_rules]

            if self.ip_rule.nyu_only:
                nyu_only = {
                    "apiVersion": "traefik.io/v1alpha1",
                    "kind": "Middleware",
                    "metadata": {
                        "name": "nyu-only-" + self.app.appid,
                        "namespace": self.nsid
                    },
                    "spec": {
                        "ipAllowList": {
                            "sourceRange": NYU_SUBNETS
                        }
                    }
                }

                middlewares.append(nyu_only)

            for middleware in middlewares:
                try:
                    self.custom_objects.create_namespaced_custom_object(group="traefik.io",
                                                                        version="v1alpha1",
                                                                        namespace=self.nsid,
                                                                        plural="middlewares",
                                                                        body=middleware)
                except kubernetes.client.exceptions.ApiException as e:
                    if e.status == 409:
                        self.custom_objects.replace_namespaced_custom_object(name="fw-rules-" + self.app.appid,
                                                                             group="traefik.io",
                                                                             version="v1alpha1",
                                                                             namespace=self.nsid,
                                                                             plural="middlewares",
                                                                             body=middleware)
                    else:
                        logging.error(f"Failed to create middleware {middleware['metadata']['name']}", exc_info=True)
                        raise e

        else:  # TODO TCP/UDP LB rules
            pass

    def create_ingress(self):
        if self.app.connection_protocol != 'http':
            return None

        hosts = [f"{self.app.slug}.{env.container_apps_domain}"]

        for domain in self.app.custom_domains.all():
            hosts.append(domain.name)

        def generate_route(host: str):
            return {
                "match": f"Host(`{host}`)",
                "kind": "Rule",
                "services": [{
                    "name": f'svc-{self.app.appid}',
                    "port": self.main_container.port
                }],
                "middlewares": [{
                    "name": "iprules-" + self.app.appid
                }]
            }

        ingress_route = {
            "apiVersion": "traefik.io/v1alpha1",
            "kind": "IngressRoute",
            "metadata": {
                "name": f"ingress-{self.app.appid}",
                "namespace": self.nsid
            },
            "spec": {
                "entryPoints": ["websecure", "web"],
                "routes": [generate_route(host) for host in hosts],
            }
        }

        if self.ip_rule.nyu_only:
            ingress_route['spec']['routes'][0]['middlewares'].append({"name": "nyu-only-" + self.app.appid})

        if self.app.pass_tls:
            ingress_route['spec']['tls'] = {"passthrough": True}
        else:
            ingress_route['spec']['tls'] = {"certResolver": "letsencrypt"}

        try:
            self.custom_objects.create_namespaced_custom_object(group="traefik.io",
                                                                version="v1alpha1",
                                                                namespace=self.nsid,
                                                                plural="ingressroutes",
                                                                body=ingress_route)
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 409:
                self.custom_objects.replace_namespaced_custom_object(
                    name=f"ingress-{self.app.appid}",
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=self.nsid,
                    plural="ingressroutes",
                    body=ingress_route)
            else:
                logging.error(f"Failed to create ingress ingress-{self.app.appid}", exc_info=True)
                raise e

    def create_autoscaler(self):
        scalers = self.app.scaler.scalers

        if scalers == []:  # Delete autoscaler if no scalers are defined
            try:
                self.custom_objects.delete_namespaced_custom_object(name="scaler-" + self.app.appid,
                                                                    group="keda.sh",
                                                                    version="v1alpha1",
                                                                    namespace=self.nsid,
                                                                    plural="scaledobjects")
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    return None
                else:
                    logging.error(f"Failed to delete autoscaler scaler-{self.app.appid}", exc_info=True)
                    raise e

            return None

        triggers = lambda t, v: {
            "type": t,
            "metadata": {
                "type": "Utilization",
                "value": v,
                "scalingModifiers": {
                    "formula": "avg * 2"
                }
            }
        }

        scaled_object = {
            "apiVersion": "keda.sh/v1alpha1",
            "kind": "ScaledObject",
            "metadata": {
                "name": "scaler-" + self.app.appid,
                "namespace": self.nsid
            },
            "spec": {
                "scaleTargetRef": {
                    "name": "app-" + self.app.appid,
                    "kind": "Deployment"
                },
                "minReplicaCount": self.app.scaler.min_replicas,
                "maxReplicaCount": self.app.scaler.max_replicas,
                "pollingInterval": 15,
                "cooldownPeriod": 60,
                "triggers": [triggers(scaler['type'], scaler['target']) for scaler in scalers],
                "advanced": {
                    "restoreToOriginalReplicaCount": True,
                    "horizontalPodAutoscalerConfig": {
                        "behavior": {
                            "scaleDown": {
                                "stabilizationWindowSeconds": self.app.scaler.scaledown_stb_window,
                                "policies": [
                                    {
                                        "type": "Percent",
                                        "value": 100,
                                        "periodSeconds": 10
                                    }
                                ]
                            },
                            "scaleUp": {
                                "stabilizationWindowSeconds": self.app.scaler.scaleup_stb_window,
                                "policies": [
                                    {
                                        "type": "Percent",
                                        "value": 100,
                                        "periodSeconds": 10
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        try:
            self.custom_objects.create_namespaced_custom_object(group="keda.sh",
                                                                version="v1alpha1",
                                                                namespace=self.nsid,
                                                                plural="scaledobjects",
                                                                body=scaled_object)

        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 409:
                self.custom_objects.replace_namespaced_custom_object(name="scaler-" + self.app.appid,
                                                                     group="keda.sh",
                                                                     version="v1alpha1",
                                                                     namespace=self.nsid,
                                                                     plural="scaledobjects",
                                                                     body=scaled_object)
            else:
                logging.error(f"Failed to create autoscaler scaler-{self.app.appid}", exc_info=True)
                raise e

    def redeploy(self):
        try:
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": datetime.now().isoformat()
                            }
                        }
                    }
                }
            }
            self.apps_v1.patch_namespaced_deployment(name='app-' + self.app.appid, namespace=self.nsid, body=patch)

        except kubernetes.client.exceptions.ApiException as e:
            logging.error(f"Failed to redeploy app {self.app.appid}", exc_info=True)
            raise e
