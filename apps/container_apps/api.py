import logging
from random import randint
from json import JSONDecodeError

from celery import chain
from django.http import JsonResponse
from django.db import transaction
from django.core.cache import cache
from rest_framework.decorators import api_view

from ..infra.models import Namespace, Volume
from ..secret_store.models import Secret
from .models import ContainerApp, Scaler, AppFW, Container, Ingress, IngressHosts
from ..container_registry.models import ContainerRegistry

from core.utils import success_message, error_message
from ..infra.tasks import init_namespace, error_handler
from .utils import validate_app_spec, validate_app_update_spec, generate_meta_for_image, under_limits
from ..users.utils import get_default_ns

from .tasks import apply_deployment, delete_deployment, restart


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def container_apps(request, nsid=None, appid=None, action=None):
    """
    API endpoint for Container Apps
    """
    if nsid is None:
        return JsonResponse(error_message('Namespace id is required'), status=400)

    ns = None
    if nsid == 'default':
        if not (nsid := request.session.get('default_nsid')):
            ns = get_default_ns(request.user)
            nsid = request.session['default_nsid'] = ns.nsid

    if (request.method in ('POST', 'PATCH', 'DELETE')) and appid is None:
        return JsonResponse(error_message('appid is required'), status=400)

    if (request.user.role in ('guest', 'blocked')) and (request.method in ('PUT', 'PATCH', 'DELETE')):
        return JsonResponse(error_message('Permission denied'), status=403)

    try:
        if ns is None:
            ns = Namespace.objects.get(nsid=nsid)

        role = ns.get_role(request.user)

        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        if role == 'viewer' and (request.method in ('PUT', 'PATCH', 'DELETE')):
            return JsonResponse(error_message('Permission denied'), status=403)

        app_data = request.data

        if request.method == 'GET':  # Get all apps in the namespace
            app_filter = {'appid': appid} if appid else {}
            apps = ContainerApp.objects.filter(namespace=ns, **app_filter)
            cache_key = f'container_app_{nsid}_{appid}_info'
            cached_data = cache.get(cache_key)
            brief_only = request.GET.get('brief') == 'true'

            if appid and cached_data and not brief_only:
                result = [cached_data]
            else:
                result = [ca.brief() for ca in apps] if brief_only else [ca.info() for ca in apps]

            if appid:
                if not result:
                    return JsonResponse(error_message('Container app not found'), status=404)
                return JsonResponse(success_message('Get container app', {'app': result[0]}), status=200)

            return JsonResponse(success_message('Get container apps', {'apps': result}), status=200)

        elif request.method == 'POST':
            app = ContainerApp.objects.get(appid=appid, namespace=ns)
            if action == 'restart':
                restart.delay(app.appid)
                return JsonResponse(success_message('Restart container app'), status=202)
            else:
                return JsonResponse(error_message('Invalid action'), status=400)

        elif request.method == 'PUT':
            valid, err = validate_app_spec(app_data, request.user)
            if not valid:
                return JsonResponse(error_message(err), status=400)

            conn_proto = app_data['connection_protocol']
            if conn_proto == 'http':
                conn_port = 443
            else:
                conn_port = randint(30030, 32767)
                while ContainerApp.objects.filter(connection_port=conn_port).exists():
                    conn_port = randint(30030, 32767)

            limit_ok, usage = under_limits(app_data, request.user)

            if not limit_ok:
                return JsonResponse(error_message('Resource request exceeds allocated limits'), status=400)

            with transaction.atomic():
                app_containers = []

                for i, spec in enumerate((app_data.get('main'), app_data.get('sidecar'), app_data.get('init'))):
                    if spec:
                        meta, err = generate_meta_for_image(spec['image'], request.user)
                        if err:
                            raise ValueError(err)

                        container = Container.objects.create(type=('main', 'sidecar', 'init')[i],
                                                             image=spec['image'],
                                                             port=spec.get('port'),
                                                             port_protocol=spec.get('port_protocol'),
                                                             command=spec.get('command', []),
                                                             args=spec.get('args', []),
                                                             cpu=spec['cpu'],
                                                             memory=spec['memory'],
                                                             metadata=meta)
                        if spec.get('pull_secret'):
                            container.pull_secret = Secret.objects.get(secretid=spec['pull_secret'])
                        if spec.get('env_secret'):
                            container.env_secret = Secret.objects.get(secretid=spec['env_secret'])

                        app_containers.append(container)

                app_volumes = []

                if volumes := app_data.get('volumes'):
                    for volume in volumes:
                        v_mode = volume['mode']
                        vol = Volume.objects.create(name=volume['name'],
                                                    type=volume['type'],
                                                    namespace=ns,
                                                    size=volume['size'],
                                                    mount_path=volume['mount_path'],
                                                    metadata={'ca_mode': v_mode, 'secretid': volume.get('secretid')})

                        app_volumes.append(vol)

                ingress_hosts = []
                app_ingress = None

                if conn_proto == 'http':
                    if ingress := app_data.get('ingress', {}):
                        hosts_set = ingress.get('hosts', [])

                        for host in hosts_set:
                            ing_host = IngressHosts.objects.create(host=host.strip())
                            ingress_hosts.append(ing_host)

                    app_ingress = Ingress.objects.create(pass_tls=ingress.get('pass_tls', False))
                    app_ingress.hosts.add(*ingress_hosts)

                scaling = app_data.get('scaling', {})

                app_scaler = Scaler.objects.create(min_replicas=scaling.get('min_replicas', 1),
                                                   max_replicas=scaling.get('max_replicas', 1),
                                                   scaleup_stb_window=scaling.get('scaleup_stb_window', 0),
                                                   scaledown_stb_window=scaling.get('scaledown_stb_window', 150),
                                                   scalers=scaling.get('scalers', []))

                firewall = app_data.get('firewall')

                app_ip_rule = AppFW.objects.create(allow=firewall.get('allow', []),
                                                   deny=firewall.get('deny', []),
                                                   precedence=firewall.get('precedence', 'deny'),
                                                   nyu_only=firewall.get('nyu_only', False))

                app = ContainerApp.objects.create(namespace=ns,
                                                  name=app_data['name'],
                                                  slug=app_data['slug'],
                                                  scaler=app_scaler,
                                                  ingress=app_ingress,
                                                  connection_port=conn_port,
                                                  connection_protocol=conn_proto,
                                                  update_strategy=app_data.get('update_strategy', 'rolling'),
                                                  ip_rule=app_ip_rule)

                app.containers.add(*app_containers)
                app.volumes.add(*app_volumes)

                app.save()

                request.user.usage.cpu += usage['cpu']
                request.user.usage.memory += usage['memory']
                request.user.usage.disk += usage['disk']

            chain(init_namespace.s(ns.nsid), apply_deployment.si(app.appid)).apply_async(link_error=error_handler.s())

            return JsonResponse(success_message('Create container app', {'app': app.info()}), status=201)

        elif request.method == 'PATCH':
            app = ContainerApp.objects.get(appid=appid, namespace=ns)

            valid, err = validate_app_update_spec(app_data, request.user)
            if not valid:
                return JsonResponse(error_message(err), status=400)

            limit_ok, usage = under_limits(app_data, request.user)

            if not limit_ok:
                return JsonResponse(error_message('Resource request exceeds allocated limits'), status=400)

            with transaction.atomic():
                if name := app_data.get('name'):
                    app.name = name.strip()
                if update_strategy := app_data.get('update_strategy'):
                    app.update_strategy = update_strategy

                request.user.usage.cpu -= app.cpu_limit
                request.user.usage.memory -= app.memory_limit
                request.user.usage.disk -= app.disk_limit

                containers = app.containers.all()

                c_types = ('main', 'sidecar', 'init')
                c_type_specs = (app_data.get('main'), app_data.get('sidecar'), app_data.get('init'))

                for c_type, spec in zip(c_types, c_type_specs):
                    container = containers.filter(type=c_type).first()

                    # Delete container if it exists and an empty spec is provided
                    if container and (spec == {}) and (c_type != 'main'):
                        container.delete()

                    # Update container if it exists and spec is provided
                    elif container and spec:
                        meta, err = generate_meta_for_image(spec['image'], request.user)
                        if err:
                            raise ValueError(err)

                        container.image = spec['image']
                        container.port = spec.get('port')
                        container.port_protocol = spec.get('port_protocol')
                        container.command = spec.get('command', [])
                        container.args = spec.get('args', [])
                        container.cpu = spec['cpu']
                        container.memory = spec['memory']
                        container.metadata = meta

                        if pull_secret := spec.get('pull_secret'):
                            container.pull_secret = Secret.objects.get(secretid=pull_secret)
                        if env_secret := spec.get('env_secret'):
                            container.env_secret = Secret.objects.get(secretid=env_secret)

                        container.save()

                    # Create container if it doesn't exist and spec is provided
                    elif spec and container is None:
                        meta, err = generate_meta_for_image(spec['image'], request.user)
                        if err:
                            raise ValueError(err)

                        container = app.containers.create(type=c_type,
                                                          image=spec['image'],
                                                          port=spec.get('port'),
                                                          port_protocol=spec.get('port_protocol'),
                                                          command=spec.get('command', []),
                                                          args=spec.get('args', []),
                                                          cpu=spec['cpu'],
                                                          memory=spec['memory'],
                                                          metadata=meta)

                        if pull_secret := spec.get('pull_secret'):
                            container.pull_secrets.add(Secret.objects.get(secretid=pull_secret))
                        if env_secret := spec.get('env_secret'):
                            container.env_secrets.add(Secret.objects.get(secretid=env_secret))

                        container.save()

                volumes = app_data.get('volumes')

                if volumes is not None:
                    existing_volumes = app.volumes.all()
                    existing_vol_ids = [vol.volid for vol in existing_volumes]
                    new_volumes = []

                    for i, volume in enumerate(volumes):
                        if volid := volume.get('volid'):
                            if volid not in existing_vol_ids:
                                return JsonResponse(error_message(f'volumes[{i}][volid] not found'), status=400)

                        v_mode = volume['mode']

                        # Update volume if it exists
                        if vol := existing_volumes.filter(volid=volid).first():
                            existing_vol_ids.remove(vol.volid)
                            vol.mount_path = volume['mount_path']
                            vol.type = volume['type']
                            vol.metadata = {'ca_mode': v_mode, 'secretid': volume.get('secretid')}
                            vol.save()
                        else:  # Create volume if it doesn't exist
                            vol = Volume.objects.create(name=volume['name'],
                                                        size=volume['size'],
                                                        type=volume['type'],
                                                        namespace=ns,
                                                        mount_path=volume['mount_path'],
                                                        metadata={'ca_mode': v_mode,
                                                                  'secretid': volume.get('secretid')}
                                                        )
                            vol.save()
                            new_volumes.append(vol)

                    app.metadata['volumes_to_del'] = existing_vol_ids

                    app.volumes.add(*new_volumes)  # Add new volumes to the app

                if app.connection_protocol == 'http':
                    ingress = app_data.get('ingress')
                    if ingress:
                        existing_hosts = app.ingress.hosts.all()
                        hosts_set = set([ing.host for ing in existing_hosts])
                        new_ingress_hosts = []

                        if ingress.get('hosts') == []:  # Delete all existing hosts
                            existing_hosts.delete()

                        else:
                            for domain in ingress.get('hosts', []):
                                ing_host = existing_hosts.filter(host=domain.strip).first()
                                if ing_host:
                                    hosts_set.discard(ing_host.host)
                                else:
                                    ing_host = IngressHosts.objects.create(host=domain.strip())
                                    ing_host.save()
                                    new_ingress_hosts.append(ing_host)

                        for domain_name in hosts_set:
                            existing_hosts.filter(host=domain_name).delete()

                        pass_tls = ingress.get('pass_tls')
                        if pass_tls is not None:
                            app.ingress.pass_tls = pass_tls

                        app.ingress.hosts.add(*new_ingress_hosts)
                        app.ingress.save()

                scaling = spec.get('scaling', {})

                if scaling is not None:
                    if scaling == {}:
                        app.scaler.default()
                    else:
                        app.scaler.min_replicas = scaling.get('min_replicas', 1)
                        app.scaler.max_replicas = scaling.get('max_replicas', 1)
                        app.scaler.scaleup_stb_window = scaling.get('scaleup_stb_window', 0)
                        app.scaler.scaledown_stb_window = scaling.get('scaledown_stb_window', 300)
                        app.scaler.scalers = scaling.get('scalers', [])

                        app.scaler.save()

                if firewall := app_data.get('firewall'):
                    app.ip_rule.allow = firewall.get('allow', [])
                    app.ip_rule.deny = firewall.get('deny', [])
                    app.ip_rule.precedence = firewall.get('precedence', 'deny')
                    app.ip_rule.nyu_only = firewall.get('nyu_only', False)

                    app.ip_rule.save()

                app.save()

                request.user.usage.cpu += usage['cpu']
                request.user.usage.memory += usage['memory']
                request.user.usage.disk += usage['disk']

            apply_deployment.delay(app.appid)

            return JsonResponse(success_message('Update container app', {'app': app.info()}), status=200)

        elif request.method == 'DELETE':
            app = ContainerApp.objects.get(appid=appid, namespace=ns)

            request.user.usage.cpu -= app.cpu_limit
            request.user.usage.memory -= app.memory_limit
            request.user.usage.disk -= app.disk_limit

            delete_deployment.delay(app.appid)
            return JsonResponse(success_message('Delete container app'), status=202)

    except Namespace.DoesNotExist:
        return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

    except ContainerApp.DoesNotExist:
        return JsonResponse(error_message('Container app not found'), status=404)

    except ContainerRegistry.DoesNotExist:
        return JsonResponse(error_message('Container registry image not found or no permission to access'), status=404)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except ValueError as e:
        return JsonResponse(error_message(str(e)), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)


@api_view(['POST'])
def name_check(request):
    """
    Check if container-app slug name is available
    """
    try:
        slug = request.data.get('slug')
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
