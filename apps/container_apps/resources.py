import kubernetes
from core.settings import env
from ..k8s.models import PVC
from ..k8s.constants import RESTART_POLICIES

from .models import Container, ContainerApp


class AppResource:
    def __init__(self):
        self.apps_v1 = kubernetes.client.AppsV1Api(env.k8s_api_client)
        self.core_v1 = kubernetes.client.CoreV1Api(env.k8s_api_client)
        self.autoscaling_v2 = kubernetes.client.AutoscalingV2Api(env.k8s_api_client)
        self.networking_v1 = kubernetes.client.NetworkingV1Api(env.k8s_api_client)

    def create_pvc(self, pvc: PVC) -> kubernetes.client.V1PersistentVolumeClaim:
        pvc_spec = kubernetes.client.V1PersistentVolumeClaim(
            metadata=kubernetes.client.V1ObjectMeta(
                name=pvc.pvcid,
                namespace=pvc.namespace.nsid
            ),
            spec=kubernetes.client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteMany"],
                resources=kubernetes.client.V1ResourceRequirements(
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

    def create_empty_dir_volume(self, pvc: PVC) -> dict:
        volume = kubernetes.client.V1Volume(
            name=pvc.pvcid,
            empty_dir=kubernetes.client.V1EmptyDirVolumeSource()
        )

        volume_mount = kubernetes.client.V1VolumeMount(
            name=pvc.pvcid,
            mount_path=pvc.mount_path
        )

        return {
            "volume": volume,
            "volume_mount": volume_mount
        }

    def create_container_resources(self, container: Container) -> kubernetes.client.V1ResourceRequirements:
        return kubernetes.client.V1ResourceRequirements(
            requests={
                'cpu': str(container.cpu_request),
                'memory': f'{container.memory_request}Gi'
            },
            limits={
                'cpu': str(container.cpu_limit),
                'memory': f'{container.memory_limit}Gi'
            }
        )

    def create_container_ports(self, container: Container) -> list[kubernetes.client.V1ContainerPort]:
        ports = []
        if container.port and container.port_protocol:
            ports.append(
                kubernetes.client.V1ContainerPort(
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
                    kubernetes.client.V1VolumeMount(
                        name=f"pvc-{pvc.pvcid}",
                        mount_path=pvc.mount_path,
                        read_only=(container_mode == 'ro')
                    )
                )

        return volume_mounts

    def create_container_spec(self, container: Container, app: ContainerApp) -> kubernetes.client.V1Container:
        container_spec = kubernetes.client.V1Container(
            name=f"{container.type}-{container.containerid}",
            image=container.image,
            image_pull_policy='IfNotPresent',
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
                kubernetes.client.V1EnvFromSource(
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
                kubernetes.client.V1Volume(
                    name=f"pvc-{pvc.pvcid}",
                    empty_dir=kubernetes.client.V1EmptyDirVolumeSource()
                )
            )

        return volumes

    def create_image_pull_secrets(self, containers: list[Container]) -> list[kubernetes.client.V1LocalObjectReference]:
        secrets = set()
        for container in containers:
            if container.pull_secret:
                secrets.add(container.pull_secret.secretid)

        return [kubernetes.client.V1LocalObjectReference(name=secret) for secret in secrets]

    def create_deployment(self, app: ContainerApp) -> kubernetes.client.V1Deployment:
        """Create a Kubernetes deployment."""
        containers = app.containers.all()
        init_containers = [c for c in containers if c.type == 'init']
        main_containers = [c for c in containers if c.type == 'main']
        sidecar_containers = [c for c in containers if c.type == 'sidecar']

        security_context = kubernetes.client.V1SecurityContext(
            privileged=False,
            allow_privilege_escalation=False,
            read_only_root_filesystem=False,
        )

        # Create pod template spec
        pod_template = kubernetes.client.V1PodTemplateSpec(
            metadata=kubernetes.client.V1ObjectMeta(
                labels={
                    'appid': app.appid
                }
            ),
            spec=kubernetes.client.V1PodSpec(
                restart_policy=RESTART_POLICIES[app.restart_policy],
                init_containers=[self.create_container_spec(c, app) for c in init_containers],
                containers=[self.create_container_spec(c, app) for c in main_containers + sidecar_containers],
                volumes=self.create_volumes(app),
                image_pull_secrets=[
                    kubernetes.client.V1LocalObjectReference(name='ecr-pull-secret')
                ],
                security_context=security_context,
                enable_service_links=False,
                automount_service_account_token=False
            )
        )

        deployment = kubernetes.client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=kubernetes.client.V1ObjectMeta(
                name=app.appid,
                namespace=app.namespace.nsid,
                labels={
                    'appid': app.appid
                }
            ),
            spec=kubernetes.client.V1DeploymentSpec(
                replicas=app.replicas,
                selector=kubernetes.client.V1LabelSelector(
                    match_labels={
                        'appid': app.appid
                    }
                ),
                template=pod_template
            )
        )

        return self.apps_v1.create_namespaced_deployment(
            namespace=app.namespace.nsid,
            body=deployment
        )

    def create_service(self, app: ContainerApp) -> list[kubernetes.client.V1Service] | None:
        main_container = app.containers.filter(type='main').first()

        port_config = {
            'port': main_container.port,
            'protocol': main_container.port_protocol.upper(),
            'target_port': main_container.port
        }
        if app.connection_protocol != 'http':
            port_config['node_port'] = app.connection_port

        service_spec = kubernetes.client.V1Service(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f'svc-{app.appid}',
                namespace=app.namespace.nsid,
                labels={
                    'appid': app.appid
                }
            ),
            spec=kubernetes.client.V1ServiceSpec(
                type='ClusterIP' if app.connection_protocol == 'http' else 'NodePort',
                selector={
                    'appid': app.appid
                },
                ports=[kubernetes.client.V1ServicePort(**port_config)],
                session_affinity='ClientIP'
            )
        )

        return self.core_v1.create_namespaced_service(
            namespace=app.namespace.nsid,
            body=service_spec
        )

    def create_hpa(self, app: ContainerApp) -> list[kubernetes.client.V2HorizontalPodAutoscaler] | None:
        if not app.hpa or not app.hpa.enable:
            return None

        metrics = []

        metrics.append(
            kubernetes.client.V2MetricSpec(
                type="Resource",
                resource=kubernetes.client.V2ResourceMetricSource(
                    name="cpu",
                    target=kubernetes.client.V2MetricTarget(
                        type="Utilization",
                        average_utilization=app.hpa.cpu_trigger
                    )
                )
            )
        )

        metrics.append(
            kubernetes.client.V2MetricSpec(
                type="Resource",
                resource=kubernetes.client.V2ResourceMetricSource(
                    name="memory",
                    target=kubernetes.client.V2MetricTarget(
                        type="Utilization",
                        average_utilization=app.hpa.memory_trigger
                    )
                )
            )
        )

        hpa_spec = kubernetes.client.V2HorizontalPodAutoscaler(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f'hpa-{app.appid}',
                namespace=app.namespace.nsid
            ),
            spec=kubernetes.client.V2HorizontalPodAutoscalerSpec(
                scale_target_ref=kubernetes.client.V2CrossVersionObjectReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name=app.appid
                ),
                min_replicas=app.hpa.min_replicas,
                max_replicas=app.hpa.max_replicas,
                metrics=metrics,
                behavior=kubernetes.client.V2HorizontalPodAutoscalerBehavior(
                    scale_up=kubernetes.client.V2HPAScalingRules(
                        stabilization_window_seconds=app.hpa.scaleup_stb_window
                    ),
                    scale_down=kubernetes.client.V2HPAScalingRules(
                        stabilization_window_seconds=app.hpa.scaledown_stb_window
                    )
                )
            )
        )

        return self.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
            namespace=app.namespace.nsid,
            body=hpa_spec
        )

    def create_ingress(self, app: ContainerApp) -> list[kubernetes.client.V1Ingress] | None:
        if not app.exposed_public or not app.custom_domains.exists():
            return None

        rules = []
        tls = []
        for domain in app.custom_domains.all():
            rules.append(
                kubernetes.client.V1IngressRule(
                    host=domain.name,
                    http=kubernetes.client.V1HTTPIngressRuleValue(
                        paths=[
                            kubernetes.client.V1HTTPIngressPath(
                                path="/",
                                path_type="Prefix",
                                backend=kubernetes.client.V1IngressBackend(
                                    service=kubernetes.client.V1IngressServiceBackend(
                                        name=f'svc-{app.appid}',
                                        port=kubernetes.client.V1ServiceBackendPort(
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
                    kubernetes.client.V1IngressTLS(
                        hosts=[domain.name],
                        secret_name=f"{app.appid}-{domain.name.replace('.', '-')}"
                    )
                )

        ingress_spec = kubernetes.client.V1Ingress(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f'{app.appid}-ingress',
                namespace=app.namespace.nsid,
                annotations={
                    'kubernetes.io/ingress.class': 'nginx',
                    'cert-manager.io/cluster-issuer': 'letsencrypt-prod'
                }
            ),
            spec=kubernetes.client.V1IngressSpec(
                rules=rules,
                tls=tls if tls else None
            )
        )

        return self.networking_v1.create_namespaced_ingress(
            namespace=app.namespace.nsid,
            body=ingress_spec
        )

    def patch_deployment_containers(self, app: ContainerApp) -> None:
        containers = app.containers.all()
        init_containers = [c for c in containers if c.type == 'init']
        main_containers = [c for c in containers if c.type == 'main']
        sidecar_containers = [c for c in containers if c.type == 'sidecar']

        patch = {
            'spec': {
                'template': {
                    'spec': {
                        'initContainers': [self.create_container_spec(c, app) for c in init_containers],
                        'containers': [self.create_container_spec(c, app) for c in
                                       main_containers + sidecar_containers],
                        'volumes': self.create_volumes(app),
                        'imagePullSecrets': self.create_image_pull_secrets(containers)
                    }
                }
            }
        }

        self.apps_v1.patch_namespaced_deployment(
            name=app.appid,
            namespace=app.namespace.nsid,
            body=patch
        )

    def patch_service(self, app: ContainerApp) -> None:
        main_container = app.containers.filter(type='main').first()
        port_config = {
            'port': main_container.port,
            'protocol': main_container.port_protocol.upper(),
            'targetPort': main_container.port
        }
        if app.connection_protocol != 'http':
            port_config['nodePort'] = app.connection_port

        patch = {
            'spec': {
                'ports': [port_config]
            }
        }

        self.core_v1.patch_namespaced_service(
            name=f'svc-{app.appid}',
            namespace=app.namespace.nsid,
            body=patch
        )

    def patch_hpa(self, app: ContainerApp) -> None:
        if not app.hpa:
            try:
                self.autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(
                    name=f'hpa-{app.appid}',
                    namespace=app.namespace.nsid
                )
            except:
                pass

            return

        metrics = [
            {
                'type': 'Resource',
                'resource': {
                    'name': 'cpu',
                    'target': {
                        'type': 'Utilization',
                        'averageUtilization': app.hpa.cpu_trigger
                    }
                }
            },
            {
                'type': 'Resource',
                'resource': {
                    'name': 'memory',
                    'target': {
                        'type': 'Utilization',
                        'averageUtilization': app.hpa.memory_trigger
                    }
                }
            }
        ]

        patch = {
            'spec': {
                'minReplicas': app.hpa.min_replicas,
                'maxReplicas': app.hpa.max_replicas,
                'metrics': metrics,
                'behavior': {
                    'scaleUp': {
                        'stabilizationWindowSeconds': app.hpa.scaleup_stb_window
                    },
                    'scaleDown': {
                        'stabilizationWindowSeconds': app.hpa.scaledown_stb_window
                    }
                }
            }
        }

        try:
            self.autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(
                name=f'hpa-{app.appid}',
                namespace=app.namespace.nsid,
                body=patch
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                self.create_hpa(app)

    def patch_ingress(self, app: ContainerApp) -> None:
        """Update ingress configuration"""
        if not app.exposed_public or not app.custom_domains.exists():
            try:
                self.networking_v1.delete_namespaced_ingress(
                    name=f'{app.appid}-ingress',
                    namespace=app.namespace.nsid
                )
            except:
                pass

            return

        rules = []
        tls = []
        for domain in app.custom_domains.all():
            rules.append({
                'host': domain.name,
                'http': {
                    'paths': [{
                        'path': '/',
                        'pathType': 'Prefix',
                        'backend': {
                            'service': {
                                'name': f'svc-{app.appid}',
                                'port': {
                                    'number': app.connection_port
                                }
                            }
                        }
                    }]
                }
            })

            if domain.gen_tls_cert:
                tls.append({
                    'hosts': [domain.name],
                    'secretName': f"{app.appid}-{domain.name.replace('.', '-')}"
                })

        patch = {
            'spec': {
                'rules': rules,
                'tls': tls if tls else None
            }
        }

        try:
            self.networking_v1.patch_namespaced_ingress(
                name=f'{app.appid}-ingress',
                namespace=app.namespace.nsid,
                body=patch
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                self.create_ingress(app)

    def update_app(self, app: ContainerApp) -> dict:
        try:
            resources = {}

            # Update PVCs (create new ones, existing ones can't be modified)
            resources['pvcs'] = []
            for pvc in app.pvcs.all():
                try:
                    # Try to get existing PVC
                    self.core_v1.read_namespaced_persistent_volume_claim(
                        name=pvc.pvcid,
                        namespace=app.namespace.nsid
                    )
                except kubernetes.client.exceptions.ApiException as e:
                    if e.status == 404:
                        resources['pvcs'].append(self.create_empty_dir_volume(pvc))

            resources['deployment'] = self.patch_deployment_containers(app)

            resources['service'] = self.patch_service(app)

            self.patch_hpa(app)

            self.patch_ingress(app)

            return resources

        except Exception as e:
            print(e)

    def scale_deployment(self, app: ContainerApp, replicas: int) -> None:
        patch = {
            'spec': {
                'replicas': replicas
            }
        }

        self.apps_v1.patch_namespaced_deployment(
            name=app.appid,
            namespace=app.namespace.nsid,
            body=patch
        )

    def create_app(self, app: ContainerApp) -> dict:
        try:
            resources = {}

            if app.pvcs.exists():
                resources['pvcs'] = [self.create_empty_dir_volume(pvc) for pvc in app.pvcs.all()]
            resources['deployment'] = self.create_deployment(app)

            resources['service'] = self.create_service(app)

            hpa = self.create_hpa(app)
            if hpa:
                resources['hpa'] = hpa

            ingress = self.create_ingress(app)
            if ingress:
                resources['ingress'] = ingress

            app.state = 'active'
            app.save()

            return resources

        except Exception as e:
            print(e)

    def delete_pvc(self, pvc: PVC) -> None:
        try:
            self.core_v1.delete_namespaced_persistent_volume_claim(
                name=pvc.pvcid,
                namespace=pvc.namespace.nsid
            )
        except:
            pass

    def delete_deployment(self, app: ContainerApp) -> None:
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=app.appid,
                namespace=app.namespace.nsid
            )
        except:
            pass

    def delete_service(self, app: ContainerApp) -> None:
        try:
            self.core_v1.delete_namespaced_service(
                name=f'svc-{app.appid}',
                namespace=app.namespace.nsid
            )
        except:
            pass

    def delete_hpa(self, app: ContainerApp) -> None:
        """Delete HPA"""
        try:
            self.autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(
                name=f'hpa-{app.appid}',
                namespace=app.namespace.nsid
            )
        except:
            pass

    def delete_ingress(self, app: ContainerApp) -> None:
        """Delete ingress"""
        try:
            self.networking_v1.delete_namespaced_ingress(
                name=f'{app.appid}-ingress',
                namespace=app.namespace.nsid
            )
        except:
            pass

    def delete_app(self, app: ContainerApp, delete_pvcs: bool = True) -> None:
        try:
            app.state = 'deleting'
            self.delete_ingress(app)
            self.delete_hpa(app)
            self.delete_service(app)
            self.delete_deployment(app)
            if delete_pvcs:
                for pvc in app.pvcs.all():
                    self.delete_pvc(pvc)

        except Exception as e:
            print(e)

    def restart_deployment(self, app: ContainerApp) -> None:
        patch = {
            'spec': {
                'replicas': 0
            }
        }

        self.apps_v1.patch_namespaced_deployment(
            name=app.appid,
            namespace=app.namespace.nsid,
            body=patch
        )

        patch['spec']['replicas'] = app.replicas

        self.apps_v1.patch_namespaced_deployment(
            name=app.appid,
            namespace=app.namespace.nsid,
            body=patch
        )
