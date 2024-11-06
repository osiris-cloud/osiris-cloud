import logging
from random import randint
from json import JSONDecodeError

from django.http import JsonResponse
from django.db import transaction
from rest_framework.decorators import api_view
from django.core.exceptions import ValidationError

from ..k8s.models import Namespace, PVC, PVCContainerMode
from ..k8s.constants import DEFAULT_HPA_SPEC
from ..secret_store.models import Secret
from .models import ContainerApp, HPA, CustomDomain

from core.utils import success_message, error_message
from .utils import validate_app_spec, validate_app_update_spec
from ..users.utils import get_default_ns

from .tasks import create_deployment, patch_deployment, delete_deployment, redeploy


@api_view(['POST'])
def name_check(request):
    """
    Check if container-app slug name is available
    """
    try:
        slug = request.data.get('slug', '')
        if not isinstance(slug, str):
            return JsonResponse(error_message('slug must be a string'), status=400)
        slug = slug.strip()
        if not slug:
            return JsonResponse(error_message('Slug is required'), status=400)

        return JsonResponse(
            success_message("Check availability", {
                'available': not bool(ContainerApp.objects.filter(slug=slug).exists())
            })
        )

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def container_apps(request, nsid=None, appid=None, action=None):
    """
    API endpoint for Container App
    """
    if nsid is None:
        return JsonResponse(error_message('Namespace id is required'), status=400)

    if nsid == 'default':
        if not (nsid := request.session.get('default_ns')):
            nsid = request.session['default_ns'] = get_default_ns(request.user).nsid

    if (request.method in ('POST', 'PATCH', 'DELETE')) and appid is None:
        return JsonResponse(error_message('appid is required'), status=400)

    try:
        ns = Namespace.objects.filter(nsid=nsid).first()
        if ns is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)
        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        if role == 'viewer' and (request.method in ('PUT', 'PATCH', 'DELETE')):
            return JsonResponse(error_message('Permission denied'), status=403)

        app_data = request.data
        match request.method:
            case 'GET':
                # Get all apps in the namespace
                app_filter = {'appid': appid} if appid else {}
                apps = ContainerApp.objects.filter(namespace=ns, **app_filter)
                result = [ca.info() for ca in apps]
                if appid:
                    if not result:
                        return JsonResponse(error_message('Container app not found'), status=404)
                    return JsonResponse(success_message('Get container app', {'app': result}), status=200)

                return JsonResponse(success_message('Get container apps', {'apps': result}), status=200)

            case 'POST':
                if action == 'redeploy':
                    app = ContainerApp.objects.filter(appid=appid, namespace=ns).first()
                    if app is None:
                        return JsonResponse(error_message('Container app not found'), status=404)

                    redeploy.delay(app.appid)
                    return JsonResponse(success_message('Redeploy container app'), status=202)

                elif action == 'logs':
                    return JsonResponse(error_message('Not implemented'), status=501)

                else:
                    return JsonResponse(error_message('Not implemented'), status=501)

            case 'PUT':
                valid, err = validate_app_spec(app_data, request.user)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                conn_proto = app_data['connection_protocol']
                if conn_proto == 'http':
                    conn_port = 443
                else:
                    conn_port = randint(30020, 32767)
                    while ContainerApp.objects.filter(connection_port=conn_port).exists():
                        conn_port = randint(30020, 32767)

                try:
                    with transaction.atomic():
                        app = ContainerApp.objects.create(namespace=ns,
                                                          name=app_data['name'],
                                                          slug=app_data['slug'],
                                                          replicas=app_data.get('replicas', 1),
                                                          connection_protocol=conn_proto,
                                                          connection_port=conn_port,
                                                          restart_policy=app_data['restart_policy'],
                                                          exposed_public=app_data['exposed_public'])

                        for i, spec in enumerate((app_data.get('main'), app_data.get('init'), app_data.get('sidecar'))):
                            if spec:
                                app.containers.create(type=('main', 'init', 'sidecar')[i],
                                                      image=spec['image'],
                                                      port=spec.get('port'),
                                                      port_protocol=spec.get('port_protocol'),
                                                      command=spec.get('command', []),
                                                      args=spec.get('args', []),
                                                      cpu_request=spec['cpu_request'],
                                                      memory_request=spec['memory_request'],
                                                      cpu_limit=spec['cpu_limit'],
                                                      memory_limit=spec['memory_limit'])
                                if spec.get('pull_secret'):
                                    app.pull_secrets.add(Secret.objects.get(secretid=spec['pull_secret']))
                                if spec.get('env_secret'):
                                    app.env_secrets.add(Secret.objects.get(secretid=spec['env_secret']))

                        if pvcs := app_data.get('volumes'):
                            for volume in pvcs:
                                print(volume)
                                modes = volume['mode']
                                pvc = PVC.objects.create(name=volume['name'],
                                                         namespace=ns,
                                                         size=volume['size'],
                                                         mount_path=volume['mount_path'],
                                                         container_app_mode=PVCContainerMode.objects.create(
                                                             init=modes['init'],
                                                             main=modes['main'],
                                                             sidecar=modes['sidecar'])
                                                         )
                                pvc.save()
                                app.pvcs.add(pvc)

                        if custom_domains := app_data.get('custom_domain'):
                            for domain in custom_domains:
                                app.custom_domains.create(name=domain['name'], gen_cert=domain['gen_cert'])

                        if hpa := app_data.get('autoscale'):
                            app.hpa = HPA.objects.create(enable=hpa['enable'],
                                                         min_replicas=hpa['min_replicas'],
                                                         max_replicas=hpa['max_replicas'],
                                                         scaleup_stb_window=hpa.get('scaleup_stb_window', 300),
                                                         scaledown_stb_window=hpa.get('scaledown_stb_window', 300),
                                                         cpu_trigger=hpa['cpu_trigger'],
                                                         memory_trigger=hpa['memory_trigger'])
                        app.save()

                except Exception as e:
                    logging.error(e)
                    return JsonResponse(error_message("Couldn't create app"), status=500)

                create_deployment.delay(app.appid)

                return JsonResponse(success_message('Create container app', {'app': app.info()}), status=201)

            case 'PATCH':
                app = ContainerApp.objects.filter(appid=appid, namespace=ns).first()
                if app is None:
                    return JsonResponse(error_message('Container app not found'), status=404)

                valid, err = validate_app_update_spec(app_data, request.user)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                with transaction.atomic():
                    if name := app_data.get('name'):
                        app.name = name
                    if replicas := app_data.get('replicas'):
                        app.replicas = replicas
                    if restart_policy := app_data.get('restart_policy'):
                        app.restart_policy = restart_policy
                    if exposed_public := app_data.get('exposed_public'):
                        app.exposed_public = exposed_public

                    containers = app.containers.all()

                    c_types = ('main', 'init', 'sidecar')
                    c_type_specs = (app_data.get('main'), app_data.get('init'), app_data.get('sidecar'))

                    for c_type, spec in zip(c_types, c_type_specs):
                        container = containers.filter(type=c_type).first()

                        # Delete container if it exists and an empty spec is provided
                        if container and (spec == {}):
                            container.delete()

                        # Update container if it exists and spec is provided
                        elif container and spec:
                            container.image = spec['image']
                            container.port = spec.get('port')
                            container.port_protocol = spec.get('port_protocol')
                            container.command = spec.get('command', [])
                            container.args = spec.get('args', [])
                            container.cpu_request = spec['cpu_request']
                            container.memory_request = spec['memory_request']
                            container.cpu_limit = spec['cpu_limit']
                            container.memory_limit = spec['memory_limit']

                            if pull_secret := spec.get('pull_secret'):
                                container.pull_secrets.clear()
                                container.pull_secrets.add(Secret.objects.get(secretid=pull_secret))
                            if env_secret := spec.get('env_secret'):
                                container.env_secrets.clear()
                                container.env_secrets.add(Secret.objects.get(secretid=env_secret))

                            container.save()

                        # Create container if it doesn't exist and spec is provided
                        elif spec and container is None:
                            container = app.containers.create(type=c_type,
                                                              image=spec['image'],
                                                              port=spec.get('port'),
                                                              port_protocol=spec.get('port_protocol'),
                                                              command=spec.get('command', []),
                                                              args=spec.get('args', []),
                                                              cpu_request=spec['cpu_request'],
                                                              memory_request=spec['memory_request'],
                                                              cpu_limit=spec['cpu_limit'],
                                                              memory_limit=spec['memory_limit'])
                            if pull_secret := spec.get('pull_secret'):
                                container.pull_secrets.add(Secret.objects.get(secretid=pull_secret))
                            if env_secret := spec.get('env_secret'):
                                container.env_secrets.add(Secret.objects.get(secretid=env_secret))

                            container.save()

                    volumes = app_data.get('volumes')

                    if volumes is not None:
                        existing_volumes = app.pvcs.all()
                        existing_vol_ids = [pvc.pvcid for pvc in existing_volumes]
                        new_volumes = []

                        if volumes == []:  # Delete volumes if empty spec is provided
                            existing_volumes.delete()
                        else:
                            for volume in volumes:
                                if volid := volume.get('volid'):
                                    if volid not in existing_vol_ids:
                                        return JsonResponse(error_message(f'Invalid volume id: {volid}'), status=400)
                                # Update volume if it exists
                                if pvc := existing_volumes.filter(pvcid=volid).first():
                                    existing_vol_ids.remove(pvc.pvcid)
                                    pvc.mount_path = volume['mount_path']
                                    pvc.container_app_mode.init = volume['mode']['init']
                                    pvc.container_app_mode.main = volume['mode']['main']
                                    pvc.container_app_mode.sidecar = volume['mode']['sidecar']
                                    pvc.save()
                                else:  # Create volume if it doesn't exist
                                    pvc = PVC.objects.create(name=volume['name'],
                                                             size=volume['size'],
                                                             namespace=ns,
                                                             mount_path=volume['mount_path'],
                                                             container_app_mode=PVCContainerMode.objects.create(
                                                                 init=volume['mode']['init'],
                                                                 main=volume['mode']['main'],
                                                                 sidecar=volume['mode']['sidecar'])
                                                             )
                                    pvc.save()
                                    new_volumes.append(pvc)

                        for pvcid in existing_vol_ids:  # Delete volumes that were not in the update spec
                            existing_volumes.filter(pvcid=pvcid).delete()

                        app.pvcs.add(*new_volumes)  # Add new volumes to the app

                    custom_domains = app_data.get('custom_domain')

                    if custom_domains is not None:
                        existing_domains = app.custom_domains.all()
                        existing_domain_names = [domain.name for domain in existing_domains]
                        new_domains = []

                        if custom_domains == []:
                            existing_domains.delete()
                        else:
                            for domain in custom_domains:
                                custom_domain = existing_domains.filter(name=domain['name']).first()
                                if custom_domain:
                                    custom_domain.gen_cert = domain['gen_cert']
                                    custom_domain.save()
                                    existing_domain_names.remove(custom_domain.name)
                                else:
                                    custom_domain = CustomDomain.objects.create(name=domain['name'],
                                                                                gen_cert=domain['gen_cert'])
                                    custom_domain.save()
                                    new_domains.append(custom_domain)

                        for domain_name in existing_domain_names:
                            existing_domains.filter(name=domain_name).delete()

                        app.custom_domains.add(*new_domains)

                    hpa = app_data.get('autoscale')
                    if hpa is not None:
                        if hpa == {}:
                            app.hpa.update(**DEFAULT_HPA_SPEC)
                        else:
                            app.hpa.enable = hpa.get('enable', app.hpa.enable)
                            app.hpa.min_replicas = hpa.get('min_replicas', app.hpa.min_replicas)
                            app.hpa.max_replicas = hpa.get('max_replicas', app.hpa.max_replicas)
                            app.hpa.scaleup_stb_window = hpa.get('scaleup_stb_window', app.hpa.scaleup_stb_window)
                            app.hpa.scaledown_stb_window = hpa.get('scaledown_stb_window', app.hpa.scaledown_stb_window)
                            app.hpa.cpu_trigger = hpa.get('cpu_trigger', app.hpa.cpu_trigger)
                            app.hpa.memory_trigger = hpa.get('memory_trigger', app.hpa.memory_trigger)
                            app.hpa.save()

                    if app_data.get('connection_protocol'):
                        app.connection_protocol = app_data['connection_protocol']

                    if r_policy := app_data.get('restart_policy'):
                        app.restart_policy = r_policy

                    if exposed_public := app_data.get('exposed_public'):
                        app.exposed_public = exposed_public

                    app.save()

                patch_deployment.delay(app.appid)

                return JsonResponse(success_message('Update container app', {'app': app.info()}), status=200)

            case 'DELETE':
                app = ContainerApp.objects.filter(appid=appid, namespace=ns).first()
                if app is None:
                    return JsonResponse(error_message('Container app not found'), status=404)

                delete_deployment.delay(app.appid)
                return JsonResponse(success_message('Delete container app'), status=202)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except ValidationError:
        return JsonResponse(error_message('Invalid appid/input data type'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
