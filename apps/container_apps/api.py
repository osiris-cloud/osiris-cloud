import logging
from random import randint
from json import JSONDecodeError

from django.http import JsonResponse
from django.db import transaction
from rest_framework.decorators import api_view
from django.core.exceptions import ValidationError

from ..k8s.models import Namespace, PVC, PVCContainerMode
from ..secret_store.models import Secret
from .models import ContainerApp, HPA

from core.utils import success_message, error_message
from .utils import validate_app_spec, validate_app_update_spec
from ..users.utils import get_default_ns

from .tasks import create_deployment, patch_deployment, delete_deployment


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

    if (request.method in ['PATCH, DELETE']) and appid is None:
        return JsonResponse(error_message('appid is required'), status=400)

    try:
        ns = Namespace.objects.filter(nsid=nsid).first()
        if ns is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)
        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

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
                return JsonResponse(error_message('Not implemented'), status=501)

            case 'PUT':
                if role == 'viewer':
                    return JsonResponse(error_message('Permission denied'), status=403)

                valid, err = validate_app_spec(app_data, request.user)
                if not valid:
                    return JsonResponse(err, status=400)

                conn_proto = app_data['connection_protocol']
                if conn_proto != 'http':
                    conn_port = randint(30020, 32767)
                    while ContainerApp.objects.filter(connection_port=conn_port).exists():
                        conn_port = randint(30020, 32767)
                else:
                    conn_port = 443

                try:
                    with transaction.atomic():
                        app = ContainerApp.objects.create(namespace=ns,
                                                          name=app_data['name'],
                                                          slug=app_data['slug'],
                                                          connection_protocol=conn_proto,
                                                          connection_port=conn_port,
                                                          restart_policy=app_data['restart_policy'],
                                                          exposed_public=app_data['exposed_public'])

                        for i, spec in enumerate((app_data.get('main'), app_data.get('init'), app_data.get('sidecar'))):
                            if spec:
                                app.containers.create(type=('main', 'init', 'sidecar')[i],
                                                      image=spec['image'],
                                                      port=spec['port'],
                                                      port_protocol=['port_protocol'],
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

                        if volumes := app_data.get('volumes'):
                            for volume in volumes:
                                modes = volume['modes']
                                pvc = PVC.objects.create(name=volume['name'],
                                                         size=volume['size'],
                                                         mount_path=volume['mount_path'],
                                                         container_app_mode=PVCContainerMode.objects.create(
                                                             init=modes['init'],
                                                             main=modes['main'],
                                                             sidecar=modes['sidecar'])
                                                         )
                                pvc.save()

                        if custom_domains := app_data.get('custom_domain'):
                            for domain in custom_domains:
                                app.custom_domains.create(name=domain['name'], gen_cert=domain['gen_cert'])

                        if hpa := app_data.get('autoscale'):
                            app.hpa = HPA.objects.create(enabled=hpa['enabled'],
                                                         min_replicas=hpa['min_replicas'],
                                                         max_replicas=hpa['max_replicas'],
                                                         scaleup_stb_window=hpa['scaleup_stb_window'],
                                                         scaledown_stb_window=hpa['scaledown_stb_window'],
                                                         cpu_trigger=hpa['cpu_trigger'],
                                                         memory_trigger=hpa['memory_trigger'])
                        app.save()

                except Exception as e:
                    logging.error(e)
                    return JsonResponse(error_message('Internal server error'), status=500)

                create_deployment.delay(app.appid)
                return JsonResponse(success_message('Create container app', app.info()), status=201)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except ValidationError:
        return JsonResponse(error_message('Invalid appid/input data type'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
