import re
import kubernetes

from json import loads as json_loads

from core.settings import env
from ..k8s.models import PVC
from ..k8s.constants import RESTART_POLICIES

from ..secret_store.models import Secret
from .models import Container, ContainerApp, HPA


def validate_container_spec(spec: dict, user) -> tuple[bool, [str | None]]:
    if not spec.get('image'):
        return False, 'image is required'

    ns_roles = ('owner', 'manager')

    if pull_secret := spec.get('pull_secret'):
        try:
            p_secret = Secret.objects.get(secretid=pull_secret)
            if p_secret.namespace.get_role(user) not in ns_roles:
                return False, 'Secret not found or no permission to access'
            if p_secret.type != 'auth':
                return False, 'Only auth secrets are allowed'
        except Exception:
            return False, 'Secret not found or no permission to access'

    if env_secret := spec.get('env_secret'):
        try:
            e_secret = Secret.objects.get(secretid=env_secret)
            if e_secret.namespace.get_role(user) not in ns_roles:
                return False, 'Secret not found or no permission to access'
            if e_secret.type != 'opaque':
                return False, 'Only opaque secrets are allowed'
        except Exception:
            return False, 'Secret not found or no permission to access'

    port = spec.get('port')
    if not port:
        return False, 'port is required'
    if not isinstance(port, int):
        return False, 'port must be an integer'

    port_protocol = spec.get('port_protocol')
    if not port_protocol:
        return False, 'port_protocol is required'
    if port_protocol not in ('tcp', 'udp'):
        return False, 'Invalid port_protocol'

    if command := spec.get('command'):
        if not isinstance(command, list):
            return False, 'command must be a list'
        for each in command:
            if not isinstance(each, str):
                return False, 'command must be a list of strings'

    if args := spec.get('args'):
        if not isinstance(args, list):
            return False, 'args must be a list'
        for each in args:
            if not isinstance(each, str):
                return False, 'args must be a list of strings'

    cpu_request = spec.get('cpu_request')
    if not cpu_request:
        return False, 'cpu_request is required'
    if not isinstance(cpu_request, int) or isinstance(cpu_request, float):
        return False, 'cpu_request must be an int or float'

    memory_request = spec.get('memory_request')
    if not memory_request:
        return False, 'memory_request is required'
    if not isinstance(memory_request, int) or isinstance(memory_request, float):
        return False, 'memory_request must be an int or float'

    cpu_limit = spec.get('cpu_limit')
    if not cpu_limit:
        return False, 'cpu_limit is required'
    if not isinstance(cpu_limit, int) or isinstance(cpu_limit, float):
        return False, 'cpu_limit must be an int or float'

    memory_limit = spec.get('memory_limit')
    if not memory_limit:
        return False, 'memory_limit is required'
    if not isinstance(memory_limit, int) or isinstance(memory_limit, float):
        return False, 'memory_limit must be an int or float'

    return True, None


def validate_hpa_spec(spec: dict) -> tuple[bool, [str | None]]:
    """
    Validate HPA spec for deployment
    """
    enable = spec.get('enable')
    if not isinstance(enable, bool):
        return False, 'enable must be a boolean'
    if not enable:
        return True, None

    min_replicas = spec.get('min_replicas')
    if not min_replicas:
        return False, 'min_replicas is required'
    if not isinstance(min_replicas, int):
        return False, 'min_replicas must be an integer'

    max_replicas = spec.get('max_replicas')
    if not max_replicas:
        return False, 'max_replicas is required'
    if not isinstance(max_replicas, int):
        return False, 'max_replicas must be an integer'

    scaleup_stb_window = spec.get('scaleup_stb_window')
    if not scaleup_stb_window:
        return False, 'scaleup_stb_window is required'
    if not isinstance(scaleup_stb_window, int):
        return False, 'scaleup_stb_window must be an integer'

    scaledown_stb_window = spec.get('scaledown_stb_window')
    if not scaledown_stb_window:
        return False, 'scaledown_stb_window is required'
    if not isinstance(scaledown_stb_window, int):
        return False, 'scaledown_stb_window must be an integer'

    cpu_trigger = spec.get('cpu_trigger')
    if not cpu_trigger:
        return False, 'cpu_trigger is required'
    if not isinstance(cpu_trigger, int):
        return False, 'cpu_trigger must be an integer'

    memory_trigger = spec.get('memory_trigger')
    if not memory_trigger:
        return False, 'memory_trigger is required'
    if not isinstance(memory_trigger, int):
        return False, 'memory_trigger must be an integer'


DOMAIN_REGEX = re.compile(r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.(?:[A-Za-z]{2,6}|[A-Za-z0-9-]{2,}\.[A-Za-z]{2,6})$')
SLUG_REGEX = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def validate_app_spec(spec: dict, user) -> tuple[bool, [str | None]]:
    """
    Validate container create spec
    """
    if not spec.get('name'):
        return False, 'name is required'
    if not isinstance(spec['name'], str):
        return False, 'name must be a string'

    main = spec.get('main')
    if not main:
        return False, 'main container config is required'
    if not isinstance(main, dict):
        return False, 'main must be an object'
    valid, err = validate_container_spec(main, user)
    if not valid:
        return False, err

    if sidecar := spec.get('sidecar'):
        if not isinstance(sidecar, dict):
            return False, 'sidecar must be an object'
        valid, err = validate_container_spec(sidecar, user)
        if not valid:
            return False, err

    if init := spec.get('init'):
        if not isinstance(sidecar, dict):
            return False, 'init must be an object'
        valid, err = validate_container_spec(init, user)
        if not valid:
            return False, err

    if custom_domain := spec.get('custom_domain'):
        if not isinstance(custom_domain, list):
            return False, 'custom_domain must be an array'
        for each in custom_domain:
            if not isinstance(each, dict):
                return False, 'custom_domain must be an array of objects'
            if not isinstance(each.get('name'), str):
                return False, 'name is required for custom_domain'
            if not DOMAIN_REGEX.match(each['name']):
                return False, 'Invalid custom domain'
            if not isinstance(each.get('gen_cert'), bool):
                return False, 'gen_cert must be a bool'

    if volumes := spec.get('volumes'):
        if not isinstance(volumes, list):
            return False, 'volumes must be an array'
        for each in volumes:
            if not isinstance(each, dict):
                return False, 'volumes must be an array of objects'
            if not isinstance(each.get('name'), str):
                return False, 'name is required for volumes'
            if not isinstance(each.get('size'), int):
                return False, 'size is required for volumes'
            if not isinstance(each.get('mount_path'), str):
                return False, 'mount_path is required for volumes'

            if not isinstance(each.get('mode'), dict):
                return False, 'mode is required for volumes'
            v_modes = ('', 'ro', 'rw')
            if not each['mode'].get('init') in v_modes:
                return False, 'init is required for mode'
            if not each['mode'].get('main') in v_modes:
                return False, 'main is required for mode'
            if not each['mode'].get('sidecar') in v_modes:
                return False, 'sidecar is required for mode'

    if hpa := spec.get('autoscale'):
        if not isinstance(hpa, dict):
            return False, 'hpa must be an object'
        valid, err = validate_hpa_spec(hpa)
        if not valid:
            return False, err

    r_policy = spec.get('restart_policy')
    if not r_policy:
        return False, 'restart_policy is required'

    if r_policy not in ('always', 'on_failure', 'never'):
        return False, 'Invalid restart_policy'

    if not spec.get('connection_protocol'):
        return False, 'connection_protocol is required'

    if spec['connection_protocol'] not in ('http', 'tcp', 'udp'):
        return False, 'Invalid connection_protocol'

    slug = spec.get('slug')
    if not slug:
        return False, 'slug is required'
    if not isinstance(slug, str):
        return False, 'slug must be a string'
    if len(slug) < 3 or len(slug) > 63:
        return False, 'slug should be between 3 and 63 characters'
    if not SLUG_REGEX.match(slug):
        return False, 'Invalid slug'

    if not spec.get('exposed_public'):
        return False, 'exposed_public is required'

    if not isinstance(spec['exposed_public'], bool):
        return False, 'exposed_public must be a boolean'

    if replica := spec.get('replicas'):
        if not isinstance(replica, int):
            return False, 'replicas must be an integer'
        if replica < 1:
            return False, 'replicas must be greater than or equal to 0'
    return True, None


def validate_hpa_update_spec(spec: dict) -> tuple[bool, [str | None]]:
    """
    Validate HPA update spec
    """
    enable = spec.get('enable')
    if enable is not None:
        if not isinstance(enable, bool):
            return False, 'enable must be a boolean'

    min_replicas = spec.get('min_replicas')

    if min_replicas is not None:
        if not isinstance(min_replicas, int):
            return False, 'min_replicas must be an integer'

    max_replicas = spec.get('max_replicas')
    if max_replicas is not None:
        if not isinstance(max_replicas, int):
            return False, 'max_replicas must be an integer'

    scaleup_stb_window = spec.get('scaleup_stb_window')
    if scaleup_stb_window is not None:
        if not isinstance(scaleup_stb_window, int):
            return False, 'scaleup_stb_window must be an integer'
        if scaleup_stb_window < 0:
            return False, 'scaleup_stb_window must be greater than or equal to 0'

    scaledown_stb_window = spec.get('scaledown_stb_window')
    if scaledown_stb_window is not None:
        if not isinstance(scaledown_stb_window, int):
            return False, 'scaledown_stb_window must be an integer'
        if scaledown_stb_window < 0:
            return False, 'scaledown_stb_window must be greater than or equal to 0'

    cpu_trigger = spec.get('cpu_trigger')
    if cpu_trigger is not None:
        if not isinstance(cpu_trigger, int):
            return False, 'cpu_trigger must be an integer'
        if cpu_trigger < 1:
            return False, 'cpu_trigger must be greater than 1%'

    memory_trigger = spec.get('memory_trigger')
    if memory_trigger is not None:
        if not isinstance(memory_trigger, int):
            return False, 'memory_trigger must be an integer'
        if memory_trigger < 1:
            return False, 'memory_trigger must be greater than 1%'


def validate_app_update_spec(spec: dict, user) -> tuple[bool, [str | None]]:
    """
    Validate container update spec
    """
    if name := spec.get('name'):
        if not isinstance(name, str):
            return False, 'name must be a string'

    if main := spec.get('main'):
        if main == {}:
            return False, 'main container config is required'
        if not isinstance(main, dict):
            return False, 'main must be an object'
        valid, err = validate_container_spec(main, user)
        if not valid:
            return False, err

    if sidecar := spec.get('sidecar'):
        if not isinstance(sidecar, dict):
            return False, 'sidecar must be an object'
        valid, err = validate_container_spec(sidecar, user)
        if not valid:
            return False, err

    if init := spec.get('init'):
        if not isinstance(sidecar, dict):
            return False, 'init must be an object'
        valid, err = validate_container_spec(init, user)
        if not valid:
            return False, err

    if custom_domain := spec.get('custom_domain'):
        if not isinstance(custom_domain, list):
            return False, 'custom_domain must be an array'
        for each in custom_domain:
            if not isinstance(each, dict):
                return False, 'custom_domain must be an array of objects'
            if not isinstance(each.get('name'), str):
                return False, 'name is required for custom_domain'
            if not DOMAIN_REGEX.match(each['name']):
                return False, 'Invalid custom domain'
            if not isinstance(each.get('gen_cert'), bool):
                return False, 'gen_cert must be a bool'

    if volumes := spec.get('volumes'):
        if not isinstance(volumes, list):
            return False, 'volumes must be an array'
        for each in volumes:
            if not isinstance(each, dict):
                return False, 'volumes must be an array of objects'
            if volid := each.get('volid'):
                if not isinstance(volid, str):
                    return False, 'volid must be a string'
            if not isinstance(each.get('name'), str):
                return False, 'name is required for volumes'
            if not isinstance(each.get('mount_path'), str):
                return False, 'mount_path is required for volumes'
            if not isinstance(each.get('mode'), dict):
                return False, 'mode is required for volumes'
            v_modes = ('', 'ro', 'rw')
            if not each['mode'].get('init') in v_modes:
                return False, 'init is required for mode'
            if not each['mode'].get('main') in v_modes:
                return False, 'main is required for mode'
            if not each['mode'].get('sidecar') in v_modes:
                return False, 'sidecar is required for mode'

    if hpa := spec.get('autoscale'):
        if not isinstance(hpa, dict):
            return False, 'hpa must be an object'
        valid, err = validate_hpa_update_spec(hpa)
        if not valid:
            return False, err

    if r_policy := spec.get('restart_policy'):
        if r_policy not in ('always', 'on_failure', 'never'):
            return False, 'Invalid restart_policy'

        if not spec.get('connection_protocol'):
            return False, 'connection_protocol is required'

        if spec['connection_protocol'] not in ('http', 'tcp', 'udp'):
            return False, 'Invalid connection_protocol'

    if exp_pub := spec.get('exposed_public'):
        if not isinstance(exp_pub, bool):
            return False, 'exposed_public must be a boolean'

    if replica := spec.get('replicas'):
        if not isinstance(replica, int):
            return False, 'replicas must be an integer'
        if replica < 1:
            return False, 'replicas must be greater than or equal to 0'
    return True, None


class KubernetesResource:
    def __init__(self, k8s_client):
        self.apps_v1 = env.k8s_client.AppsV1Api(k8s_client)
        self.core_v1 = env.k8s_client.CoreV1Api(k8s_client)
        self.autoscaling_v2 = env.k8s_client.AutoscalingV2Api(k8s_client)
        self.networking_v1 = env.k8s_client.NetworkingV1Api(k8s_client)

    def create_pvc(self, pvc: PVC) -> kubernetes.client.V1PersistentVolumeClaim:
        pvc_spec = env.k8s_client.V1PersistentVolumeClaim(
            metadata=env.k8s_client.V1ObjectMeta(
                name=pvc.name,
                namespace=pvc.namespace.nsid
            ),
            spec=env.k8s_client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteMany"],
                resources=env.k8s_client.V1ResourceRequirements(
                    requests={
                        "storage": f"{pvc.size}Gi"
                    }
                ),
                storage_class_name="longhorn"
            )
        )

        return self.core_v1.create_namespaced_persistent_volume_claim(
            namespace=pvc.namespace.nsid,
            body=pvc_spec
        )

    def create_container_resources(self, container: Container) -> kubernetes.client.V1ResourceRequirements:
        return env.k8s_client.V1ResourceRequirements(
            requests={
                'cpu': f'{container.cpu_request}',
                'memory': f'{container.memory_request}GB'
            },
            limits={
                'cpu': f'{container.cpu_limit}',
                'memory': f'{container.memory_limit}GB'
            }
        )

    def create_container_ports(self, container: Container) -> list[kubernetes.client.V1ContainerPort]:
        ports = []
        if container.port:
            ports.append(
                env.k8s_client.V1ContainerPort(
                    container_port=container.port,
                    protocol=container.port_protocol.upper()
                )
            )
        return ports

    def create_volume_mounts(self, container: Container, app: ContainerApp) -> list[kubernetes.client.V1VolumeMount]:
        volume_mounts = []

        for pvc in app.pvcs.all():
            container_mode = getattr(pvc.container_app_mode, container.type, '')
            if container_mode:
                volume_mounts.append(
                    env.k8s_client.V1VolumeMount(
                        name=f"pvc-{pvc.pvcid}",
                        mount_path=pvc.mount_path,
                        read_only=(container_mode == 'ro')
                    )
                )

        return volume_mounts

    def create_container_spec(self, container: Container, app: ContainerApp) -> kubernetes.client.V1Container:
        container_spec = env.k8s_client.V1Container(
            name=f"{container.type}-{container.containerid}",
            image=container.image,
            resources=self.create_container_resources(container),
            ports=self.create_container_ports(container),
            volume_mounts=self.create_volume_mounts(container, app)
        )

        if container.command:
            container_spec.command = container.command
        if container.args:
            container_spec.args = container.args

        if container.env_secret:
            container_spec.env_from = [
                env.k8s_client.V1EnvFromSource(
                    secret_ref=env.k8s_client.V1SecretEnvSource(
                        name=container.env_secret.secretid
                    )
                )
            ]

        return container_spec

    def create_volumes(self, app: ContainerApp) -> list[kubernetes.client.V1Volume]:
        volumes = []
        for pvc in app.pvcs.all():
            volumes.append(
                env.k8s_client.V1Volume(
                    name=f"pvc-{pvc.pvcid}",
                    persistent_volume_claim=env.k8s_client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pvc.pvcid
                    )
                )
            )

        return volumes

    def create_image_pull_secrets(self, containers: list[Container]) -> list[kubernetes.client.V1LocalObjectReference]:
        secrets = set()
        for container in containers:
            if container.pull_secret:
                secrets.add(container.pull_secret.secretid)

        return [env.k8s_client.V1LocalObjectReference(name=secret) for secret in secrets]

    def create_deployment(self, app: ContainerApp) -> kubernetes.client.V1Deployment:
        """Create a Kubernetes deployment."""
        containers = app.containers.all()
        init_containers = [c for c in containers if c.type == 'init']
        main_containers = [c for c in containers if c.type == 'main']
        sidecar_containers = [c for c in containers if c.type == 'sidecar']

        pod_template = env.k8s_client.V1PodTemplateSpec(
            metadata=env.k8s_client.V1ObjectMeta(
                labels={
                    'app': app.slug,
                    'app-id': app.appid
                }
            ),
            spec=env.k8s_client.V1PodSpec(
                restart_policy=RESTART_POLICIES[app.restart_policy],
                init_containers=[self.create_container_spec(c, app) for c in init_containers],
                containers=[self.create_container_spec(c, app) for c in main_containers + sidecar_containers],
                volumes=self.create_volumes(app),
                image_pull_secrets=self.create_image_pull_secrets(containers)
            )
        )

        deployment = env.k8s_client.V1Deployment(
            metadata=env.k8s_client.V1ObjectMeta(
                name=app.slug,
                namespace=app.namespace.name,
                labels={
                    'app': app.slug,
                    'app-id': app.appid
                }
            ),
            spec=env.k8s_client.V1DeploymentSpec(
                replicas=app.replicas,
                selector=env.k8s_client.V1LabelSelector(
                    match_labels={
                        'app': app.slug,
                        'app-id': app.appid
                    }
                ),
                template=pod_template
            )
        )

        return self.apps_v1.create_namespaced_deployment(
            namespace=app.namespace.name,
            body=deployment
        )

    def create_service(self, app: ContainerApp) -> list[kubernetes.client.V1Service] | None:
        if not app.connection_port:
            return None

        service_spec = env.k8s_client.V1Service(
            metadata=env.k8s_client.V1ObjectMeta(
                name=app.slug,
                namespace=app.namespace.name,
                labels={
                    'app': app.slug,
                    'app-id': app.appid
                }
            ),
            spec=env.k8s_client.V1ServiceSpec(
                selector={
                    'app': app.slug,
                    'app-id': app.appid
                },
                ports=[
                    env.k8s_client.V1ServicePort(
                        port=app.connection_port,
                        protocol=app.connection_protocol.upper(),
                        target_port=app.connection_port
                    )
                ]
            )
        )

        return self.core_v1.create_namespaced_service(
            namespace=app.namespace.name,
            body=service_spec
        )

    def create_hpa(self, app: ContainerApp) -> list[kubernetes.client.V2HorizontalPodAutoscaler] | None:
        if not app.hpa or not app.hpa.enable:
            return None

        metrics = []

        metrics.append(
            env.k8s_client.V2MetricSpec(
                type="Resource",
                resource=env.k8s_client.V2ResourceMetricSource(
                    name="cpu",
                    target=env.k8s_client.V2MetricTarget(
                        type="Utilization",
                        average_utilization=app.hpa.cpu_trigger
                    )
                )
            )
        )

        metrics.append(
            env.k8s_client.V2MetricSpec(
                type="Resource",
                resource=env.k8s_client.V2ResourceMetricSource(
                    name="memory",
                    target=env.k8s_client.V2MetricTarget(
                        type="Utilization",
                        average_utilization=app.hpa.memory_trigger
                    )
                )
            )
        )

        hpa_spec = env.k8s_client.V2HorizontalPodAutoscaler(
            metadata=env.k8s_client.V1ObjectMeta(
                name=app.slug,
                namespace=app.namespace.name
            ),
            spec=env.k8s_client.V2HorizontalPodAutoscalerSpec(
                scale_target_ref=env.k8s_client.V2CrossVersionObjectReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name=app.slug
                ),
                min_replicas=app.hpa.min_replicas,
                max_replicas=app.hpa.max_replicas,
                metrics=metrics,
                behavior=env.k8s_client.V2HorizontalPodAutoscalerBehavior(
                    scale_up=env.k8s_client.V2HPAScalingRules(
                        stabilization_window_seconds=app.hpa.scaleup_stb_window
                    ),
                    scale_down=client.V2HPAScalingRules(
                        stabilization_window_seconds=app.hpa.scaledown_stb_window
                    )
                )
            )
        )

        return self.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
            namespace=app.namespace.name,
            body=hpa_spec
        )

    def create_ingress(self, app: ContainerApp) -> list[kubernetes.client.V1Ingress] | None:
        if not app.exposed_public or not app.custom_domains.exists():
            return None

        rules = []
        tls = []
        for domain in app.custom_domains.all():
            rules.append(
                env.k8s_client.V1IngressRule(
                    host=domain.name,
                    http=env.k8s_client.V1HTTPIngressRuleValue(
                        paths=[
                            env.k8s_client.V1HTTPIngressPath(
                                path="/",
                                path_type="Prefix",
                                backend=env.k8s_client.V1IngressBackend(
                                    service=env.k8s_client.V1IngressServiceBackend(
                                        name=app.slug,
                                        port=env.k8s_client.V1ServiceBackendPort(
                                            number=app.connection_port
                                        )
                                    )
                                )
                            )
                        ]
                    )
                )
            )

            if domain.gen_tls_cert:
                tls.append(
                    env.k8s_client.V1IngressTLS(
                        hosts=[domain.name],
                        secret_name=f"tls-{app.slug}-{domain.name}"
                    )
                )

        ingress_spec = env.k8s_client.V1Ingress(
            metadata=env.k8s_client.V1ObjectMeta(
                name=app.slug,
                namespace=app.namespace.name,
                annotations={
                    'kubernetes.io/ingress.class': 'nginx',
                    'cert-manager.io/cluster-issuer': 'letsencrypt-prod'
                }
            ),
            spec=env.k8s_client.V1IngressSpec(
                rules=rules,
                tls=tls if tls else None
            )
        )

        return self.networking_v1.create_namespaced_ingress(
            namespace=app.namespace.name,
            body=ingress_spec
        )

    def create_app(self, app: ContainerApp) -> dict:
        try:
            resources = {}

            # Create PVCs first
            if app.pvcs.exists():
                resources['pvcs'] = [
                    self.create_pvc(pvc) for pvc in app.pvcs.all()
                ]

            # Create deployment
            resources['deployment'] = self.create_deployment(app)

            # Create service if needed
            service = self.create_service(app)
            if service:
                resources['service'] = service

            # Create HPA if enabled
            hpa = self.create_hpa(app)
            if hpa:
                resources['hpa'] = hpa

            # Create Ingress if needed
            ingress = self.create_ingress(app)
            if ingress:
                resources['ingress'] = ingress

            return resources

        except Exception as e:
            print(e)
