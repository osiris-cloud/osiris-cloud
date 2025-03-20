import logging
import re
import ipaddress

from core.settings import env

from .models import ContainerApp, IngressHosts
from ..container_registry.models import ContainerRegistry
from ..infra.models import Volume
from ..secret_store.models import Secret
from ..users.models import User

from ..infra.constants import VOLUME_TYPES, DOMAIN_REGEX, SLUG_REGEX, STATE_TRANSLATIONS

DOMAIN_RE = re.compile(DOMAIN_REGEX)
SLUG_RE = re.compile(SLUG_REGEX)
V_TYPES = [v[0] for v in VOLUME_TYPES]


def validate_container_spec(c_type: str, spec: dict, user, port_req=True) -> tuple[bool, [str | None]]:
    if not spec.get('image'):
        return False, 'image is required'

    if pull_secret := spec.get('pull_secret'):
        try:
            p_secret = Secret.objects.get(secretid=pull_secret)
            if p_secret.namespace.get_role(user) is None:
                return False, f'{c_type}[pull_secret] not found or no permission to access'
            if p_secret.type != 'dockerconfig':
                return False, f'{c_type}: only dockerconfig secrets are allowed for pull_secret'
        except Exception:
            return False, f'{c_type}[pull_secret] not found or no permission to access'

    if env_secret := spec.get('env_secret'):
        try:
            e_secret = Secret.objects.get(secretid=env_secret)
            if e_secret.namespace.get_role(user) is None:
                return False, f'{c_type}[env_secret] not found or no permission to access'
            if e_secret.type != 'opaque':
                return False, f'{c_type}: Only opaque secrets are allowed for env_secret'
        except Exception:
            return False, f'{c_type}[env_secret] not found or no permission to access'

    port = spec.get('port')
    if not port and port_req:
        return False, f'{c_type}[port] is required'
    if not isinstance(port, int) and port_req:
        return False, f'{c_type}[port] must be an integer'

    port_protocol = spec.get('port_protocol')
    if not port_protocol and port_req:
        return False, f'{c_type}[port_protocol] is required'
    if port_protocol not in ('tcp', 'udp') and port_req:
        return False, f'{c_type}: Invalid port_protocol'

    if command := spec.get('command'):
        if not isinstance(command, list):
            return False, f'{c_type}[command] must be a list'
        for each in command:
            if not isinstance(each, str):
                return False, f'{c_type}[command] must be a list of strings'

    if args := spec.get('args'):
        if not isinstance(args, list):
            return False, f'{c_type}[args] must be a list'
        for each in args:
            if not isinstance(each, str):
                return False, f'{c_type}[args] must be a list of strings'

    cpu_request = spec.get('cpu')
    if cpu_request is None:
        return False, f'{c_type}[cpu] is required'
    if not (isinstance(cpu_request, int) or isinstance(cpu_request, float)):
        return False, f'{c_type}[cpu] must be an int or float'
    if cpu_request <= 0:
        return False, f'{c_type}[cpu] must be greater than 0'

    memory_request = spec.get('memory')
    if memory_request is None:
        return False, f'{c_type}[memory] is required'
    if not (isinstance(memory_request, int) or isinstance(memory_request, float)):
        return False, f'{c_type}[memory] must be an int or float'
    if memory_request <= 0:
        return False, f'{c_type}[memory] must be greater than 0'

    return True, None


def validate_ingress_spec(ingress: dict) -> tuple[bool, [str | None]]:
    if ingress == {} or ingress is None:
        return True, None

    if not isinstance(ingress, dict):
        return False, 'ingress must be a dict'

    if hosts := ingress.get('hosts'):
        if not isinstance(hosts, list):
            return False, 'hosts must be an array'

        for i, domain in enumerate(hosts):
            if not isinstance(domain, str):
                return False, f'hosts[{i}] must be a string'

            domain = domain.strip()

            if not DOMAIN_RE.match(domain):
                return False, f'host: "{domain}" is invalid'
            if domain == env.container_apps_domain or domain.endswith(f".{env.container_apps_domain}"):
                return False, f'host: "{domain}" cannot be used'

            try:
                IngressHosts.objects.get(host=domain)
                return False, f'host: "{domain}" is already used by another app'
            except IngressHosts.DoesNotExist:
                pass

    pass_tls = ingress.get('pass_tls')
    if pass_tls is not None:
        if not isinstance(pass_tls, bool):
            return False, 'ingress[pass_tls] must be a boolean'

    return True, None


def validate_volume_spec(volumes: dict, *, user: User, sidecar: bool, init: bool) -> tuple[bool, [str | None]]:
    if volumes == [] or volumes is None:
        return True, None

    if not isinstance(volumes, list):
        return False, 'volumes must be an array'

    for i, vol in enumerate(volumes):
        if not isinstance(vol, dict):
            return False, f'volumes[{i}] must be an object'

        if vol_id := vol.get('volumeid'):
            try:
                volume = Volume.objects.get(volumeid=vol_id)
                if volume.container_app.namespace.get_role(user) is None:
                    return False, f'volumeid for volume[{i}] not found or no permission to access'
            except Exception:
                return False, f'volumeid for volume[{i}] not found or no permission to access'

        if not isinstance(vol.get('name'), str):
            return False, f'name is required for volume[{i}]'

        if not isinstance(vol.get('type'), str):
            return False, f'type is required for volume[{i}]'

        if vol['type'] not in V_TYPES:
            return False, f'Invalid type for volume[{i}]'

        if not (isinstance(vol.get('size'), float) or isinstance(vol.get('size'), int)):
            return False, f'size is required for volume[{i}]'

        if not isinstance(vol.get('mount_path'), str):
            return False, f'mount_path is required for volume[{i}]'

        if not isinstance(vol.get('mode'), dict):
            return False, f'mode(object) is required for volume[{i}]'

        v_modes = ('', 'ro', 'rw')

        if not vol['mode'].get('main') in v_modes:
            return False, f'main is required for volume[{i}][mode]'
        if sidecar and (not vol['mode'].get('sidecar') in v_modes):
            return False, f'sidecar is required for volume[{i}][mode]'
        if init and (not vol['mode'].get('init') in v_modes):
            return False, f'init is required for volume[{i}][mode]'

        if vol['type'] == 'secret':
            if not isinstance(vol['secretid'], str):
                return False, f'secretid is required for type secret volume[{i}]'

            try:
                secret = Secret.objects.get(secretid=vol['secretid'])
                if secret.namespace.get_role(user) is None:
                    return False, f'secretid for volume[{i}] not found or no permission to access'
            except Exception:
                return False, f'secretid for volume[{i}] not found or no permission to access'

            allowed_v_modes = ('', 'ro')
            if vol['mode']['main'] not in allowed_v_modes:
                return False, f'volume[{i}][mode][main] for secret type can only be ro or empty'
            if sidecar and (vol['mode']['sidecar'] not in allowed_v_modes):
                return False, f'volume[{i}][mode][sidecar] for secret type can only be ro or empty'
            if init and (vol['mode']['init'] not in allowed_v_modes):
                return False, f'volume[{i}][mode][init] for secret type can only be ro or empty'

        elif vol['type'] == 'block':
            allowed_v_modes = ('', 'rw')
            if vol['mode']['main'] not in allowed_v_modes:
                return False, f'volume[{i}][mode][main] for block type can only be rw or empty'
            if sidecar and (vol['mode']['sidecar'] not in allowed_v_modes):
                return False, f'volume[{i}][mode][sidecar] for block type can only be rw or empty'
            if init and (vol['mode']['init'] not in allowed_v_modes):
                return False, f'volume[{i}][mode][init] for block type can only be rw or empty'

    return True, None


def validate_scaling_spec(spec: dict) -> tuple[bool, [str | None]]:
    if spec == {} or spec is None:
        return True, None

    if not isinstance(spec, dict):
        return False, 'scaling must be an object'

    min_replicas = spec.get('min_replicas')
    if not min_replicas:
        return False, 'scaling[min_replicas] is required'
    if not isinstance(min_replicas, int):
        return False, 'scaling[min_replicas] must be an integer'

    autoscaling = hasattr(spec, 'scalers')

    max_replicas = spec.get('max_replicas')
    if not max_replicas and autoscaling:
        return False, 'scaling[max_replicas] is required'
    if not isinstance(max_replicas, int) and autoscaling:
        return False, 'scaling[max_replicas] must be an integer'

    if scaledown_stb_window := spec.get('scaledown_stb_window'):
        if not isinstance(scaledown_stb_window, int):
            return False, 'scaling[scaledown_stb_window] must be an integer'

    if scaledown_stb_window := spec.get('scaleup_stb_window'):
        if not isinstance(scaledown_stb_window, int):
            return False, 'scaling[scaleup_stb_window] must be an integer'

    if scalers := spec.get('scalers'):
        if not isinstance(scalers, list):
            return False, 'scaling[scalers] must be an array'
        for each in scalers:
            if not isinstance(each, dict):
                return False, 'scaling[scalers] must be an array of objects'
            if not isinstance(each.get('type'), str):
                return False, 'scaling[scalers][type] is required for scalers'
            if each['type'] not in ('cpu', 'memory'):
                return False, 'Invalid scaler type'
            if not isinstance(each.get('target'), int):
                return False, 'scaling[scalers][target] is required for scalers'
            if each['target'] < 1 or each['target'] > 100:
                return False, 'scaling[scalers][target] must be with 1% and 100%'

    return True, None


def validate_ip_rule(ip_string: str) -> tuple[bool, [str | None]]:
    ip_string = ip_string.strip()

    if '-' in ip_string:  # IP range (format: start_ip-end_ip)
        try:
            start_ip, end_ip = ip_string.split('-')
            start_ip = ipaddress.ip_address(start_ip.strip())
            end_ip = ipaddress.ip_address(end_ip.strip())

            if start_ip > end_ip:
                return False, "Start IP must be less than end IP"

            return True, None
        except ValueError:
            return False, "Invalid IP range format. Use format: start ip-end_ip"

    elif '/' in ip_string:  # CIDR subnet
        try:
            network = ipaddress.ip_network(ip_string, strict=False)
            return True, None
        except ValueError:
            return False, "Invalid CIDR subnet format"

    else:  # Single IP
        try:
            ipaddress.ip_address(ip_string)
            return True, None
        except ValueError:
            return False, "Invalid IP address format"


def validate_fw_spec(spec: dict) -> tuple[bool, [str | None]]:
    if spec == {} or spec is None:
        return True, None

    if not isinstance(spec, dict):
        return False, 'firewall must be an object'

    rules_set = False

    if allow_rules := spec.get('allow'):
        if not isinstance(allow_rules, list):
            return False, 'firewall[allow] must be an array'

        for rule in allow_rules:
            if not isinstance(rule, str):
                return False, 'firewall[allow] must be an array of strings'
            valid, err = validate_ip_rule(rule)
            if not valid:
                return False, 'Allow rule: ' + rule + ' ,' + err
        rules_set = True

    if deny_rules := spec.get('deny'):
        if not isinstance(deny_rules, list):
            return False, 'firewall[deny] must be an array'

        for rule in deny_rules:
            if not isinstance(rule, str):
                return False, 'firewall[deny] must be an array of strings'
            valid, err = validate_ip_rule(rule)
            if not valid:
                return False, 'Deny rule: ' + rule + ' ,' + err
        rules_set = True

    precedence = spec.get('precedence')
    if rules_set and not precedence:
        return False, 'firewall[precedence] is required'

    if rules_set and precedence not in ('allow', 'deny'):
        return False, 'firewall[precedence] must be either allow or deny'

    if spec.get('nyu_only') is not None:
        if not isinstance(spec['nyu_only'], bool):
            return False, 'firewall[nyu_only] must be a boolean'

    return True, None


def validate_app_spec(spec: dict, user) -> tuple[bool, [str | None]]:
    """
    Validate container app create spec
    """
    if spec is None:
        return False, 'Missing request spec'

    if not isinstance(spec, dict):
        return False, 'spec must be an object'

    if not spec.get('name'):
        return False, 'name is required'
    if not isinstance(spec['name'], str):
        return False, 'name must be a string'
    if not spec['name'].strip():
        return False, 'name cannot be empty'

    slug = spec.get('slug')
    if not slug:
        return False, 'slug is required'

    if not isinstance(slug, str):
        return False, 'slug must be a string'

    slug = slug.strip().lower()

    if len(slug) < 3 or len(slug) > 63:
        return False, 'slug should be between 3 and 63 characters'

    if not SLUG_RE.match(slug):
        return False, 'Invalid subdomain slug'

    try:
        ContainerApp.objects.get(slug=slug)
        return False, 'slug already exists'
    except ContainerApp.DoesNotExist:
        pass

    if r_policy := spec.get('restart_policy'):
        if r_policy not in ('always', 'on_failure', 'never'):
            return False, 'Invalid restart_policy'

    if not spec.get('connection_protocol'):
        return False, 'connection_protocol is required'

    if spec['connection_protocol'] not in ('http', 'tcp', 'udp'):
        return False, 'Invalid connection_protocol'

    sidecar_enabled = False
    init_enabled = False

    main = spec.get('main')
    if not main:
        return False, 'main container config is required'
    if not isinstance(main, dict):
        return False, 'main must be an object'
    valid, err = validate_container_spec('main', main, user)
    if not valid:
        return False, err

    if sidecar := spec.get('sidecar'):
        if not isinstance(sidecar, dict):
            return False, 'sidecar must be an object'
        valid, err = validate_container_spec('sidecar', sidecar, user, False)
        if not valid:
            return False, err
        sidecar_enabled = True

    if init := spec.get('init'):
        if not isinstance(sidecar, dict):
            return False, 'init must be an object'
        valid, err = validate_container_spec('init', init, user, False)
        if not valid:
            return False, err
        init_enabled = True

    if volumes := spec.get('volumes'):
        valid, err = validate_volume_spec(volumes, user=user, sidecar=sidecar_enabled, init=init_enabled)
        if not valid:
            return False, err

    if scaling := spec.get('scaling'):
        valid, err = validate_scaling_spec(scaling)

        if not valid:
            return False, err

    if ingress := spec.get('ingress'):
        valid, err = validate_ingress_spec(ingress)
        if not valid:
            return False, err

    if fw := spec.get('firewall'):
        valid, err = validate_fw_spec(fw)
        if not valid:
            return False, err

    return True, None


def validate_app_update_spec(spec: dict, user) -> tuple[bool, [str | None]]:
    """
    Validate container app update spec
    """
    if spec is None:
        return False, 'Missing request spec'

    if not isinstance(spec, dict):
        return False, 'spec must be an object'

    if name := spec.get('name'):
        if not isinstance(name, str):
            return False, 'name must be a string'

        if not name.strip():
            return False, 'name cannot be empty'

    if r_policy := spec.get('restart_policy'):
        if r_policy not in ('always', 'on_failure', 'never'):
            return False, 'Invalid restart_policy'

    if c_proto := spec.get('connection_protocol'):
        if c_proto not in ('http', 'tcp', 'udp'):
            return False, 'Invalid connection_protocol'

    sidecar_enabled = False
    init_enabled = False

    if main := spec.get('main'):
        if not isinstance(main, dict):
            return False, 'main must be an object'
        valid, err = validate_container_spec('main', main, user)
        if not valid:
            return False, err

    if sidecar := spec.get('sidecar'):
        if not isinstance(sidecar, dict):
            return False, 'sidecar must be an object'
        valid, err = validate_container_spec('sidecar', sidecar, user, False)
        if not valid:
            return False, err
        sidecar_enabled = True

    if init := spec.get('init'):
        if not isinstance(sidecar, dict):
            return False, 'init must be an object'
        valid, err = validate_container_spec('init', init, user, False)
        if not valid:
            return False, err
        init_enabled = True

    if volumes := spec.get('volumes'):
        valid, err = validate_volume_spec(volumes, user=user, sidecar=sidecar_enabled, init=init_enabled)
        if not valid:
            return False, err

    if scaling := spec.get('scaling'):
        valid, err = validate_scaling_spec(scaling)
        if not valid:
            return False, err

    if ingress := spec.get('ingress'):
        valid, err = validate_ingress_spec(ingress)
        if not valid:
            return False, err

    if fw := spec.get('firewall'):
        valid, err = validate_fw_spec(fw)
        if not valid:
            return False, err

    return True, None


def generate_meta_for_image(image: str, user) -> tuple[dict, str | None]:
    if image.startswith(env.registry_domain):
        image = image.removeprefix(env.registry_domain + '/')
        image_parts = image.split('/', 1)
        if len(image_parts) == 2:
            registry = ContainerRegistry.objects.get(repo=image_parts[0])
            if registry.namespace.get_role(user) is None:
                return {}, 'Container registry image not found or no permission to access'
            meta = {
                'crid': registry.crid,
                'repo': image_parts[0],
                'image': image_parts[1]
            }
            return meta, None
        return {}, 'Invalid registry image url'
    return {}, None


def under_limits(spec: dict, user) -> [bool, dict]:
    """
    Check if the app spec can be created under user limits.
    Returns True if the app can be created, False otherwise, along with resource usage as dict.
    """
    agg_cpu = 0
    agg_memory = 0
    agg_disk = 0
    scaling = spec.get('scaling', {})
    count = scaling.get('max_replicas', scaling.get('min_replicas', 1))

    for cont in (spec.get('main'), spec.get('sidecar')):
        if cont:
            agg_cpu += cont['cpu'] * count
            agg_memory += cont['memory'] * count

    for vol in spec.get('volumes', []):
        agg_disk += vol['size']

    main_sidecar_ok = True
    init_ok = True

    init_cpu = 0
    init_mem = 0

    if user.limit.limit_reached(cpu=agg_cpu, memory=agg_memory, disk=agg_disk):
        main_sidecar_ok = False

    if init := spec.get('init'):
        init_cpu = init['cpu'] * count
        init_mem = init['memory'] * count
        if user.limit.limit_reached(cpu=init_cpu, memory=init_mem, disk=agg_disk):
            init_ok = False

    if main_sidecar_ok and init_ok:
        user.usage.cpu += agg_cpu
        user.usage.memory += agg_memory
        user.usage.disk += agg_disk
        user.usage.save()

    return (main_sidecar_ok and init_ok, {
        'cpu': max(agg_cpu, init_cpu),
        'memory': max(agg_memory, init_mem),
        'disk': agg_disk
    })


def process_events(events):
    """
    Process kubernetes events and sort them by timestamp in descending order
    """
    event_messages = []
    for e in events.items:
        if e.reason == 'ScalingReplicaSet':
            msg = e.message.split()
            event_messages.append({
                'message': ' '.join(msg[:2] + ['app instances'] + msg[5:]),
                'time': e.last_timestamp.isoformat() if e.last_timestamp else None
            })
        else:
            event_messages.append({
                'reason': e.reason,
                'message': e.message,
                'time': e.last_timestamp.isoformat() if e.last_timestamp else None
            })

    return sorted(
        event_messages,
        key=lambda x: (x['time'] is None, x['time'] or ''),
        reverse=True
    )


def process_conditions(deployment):
    """
    Process deployment conditions
    """
    conditions = []
    k8s_conditions = sorted(deployment.status.conditions, key=lambda x: x.last_transition_time, reverse=True)
    for condition in k8s_conditions:
        last_transition_time = condition.last_transition_time
        last_update_time = condition.last_update_time

        conditions.append({
            'type': condition.type,
            'status': condition.status,
            'reason': condition.reason if hasattr(condition, 'reason') else None,
            'message': condition.message if hasattr(condition, 'message') else None,
            'last_transition_time': last_transition_time.isoformat() if last_transition_time else None,
            'last_update_time': last_update_time.isoformat() if last_update_time else None
        })
    return conditions


def process_pod_info(pod) -> dict:
    """
    Process pod information
    """

    is_terminating = pod.metadata.deletion_timestamp is not None

    pod_info = {
        'iref': pod.metadata.name,
        'state': None,
        'started_at': pod.status.start_time.isoformat() if pod.status.start_time else '',
        'main': {},
        'sidecar': {},
        'init': {},
    }

    for container in pod.spec.containers:
        if container.name == 'main':
            port = container.ports[0]
            pod_info['main']['port'] = port.container_port
            pod_info['main']['port_protocol'] = port.protocol.lower()
            break

    if pod.status.container_statuses:
        for container in pod.status.container_statuses:
            container_info = process_container_status(container)

            if is_terminating:  # If pod is terminating, override container state
                container_info['state'] = 'terminating'

            if container.name.startswith('main'):
                pod_info['main'].update(container_info)

            elif container.name.startswith('sidecar'):
                pod_info['sidecar'] = container_info

    init_container = {}

    if pod.status.init_container_statuses:
        init_container = process_container_status(pod.status.init_container_statuses[0])

        if is_terminating:  # If pod is terminating, override container state
            init_container['state'] = 'terminating'

        pod_info['init'] = init_container

    for container in (pod_info['main'], pod_info['sidecar'], pod_info['init']):
        if not container or (container.get('state') is None):
            continue

        if container['state'] == 'crash':
            pod_info['state'] = 'crash'
            break

        else:
            state = 'terminating' if is_terminating else get_state_from_conditions(pod.status.conditions)
            if state == 'pending' and init_container.get('state') == 'running':
                pod_info['state'] = 'pending'
            else:
                pod_info['state'] = 'creating' if state == 'pending' else state

    return pod_info


def process_container_status(container) -> dict:
    """
    Process container status information
    """
    container_info = {
        'state': None,
        'image': container.image,
        'ready': container.ready,
        'restarts': container.restart_count,
        'started': container.started,
        'started_at': None,
        'message': ''
    }

    if waiting := container.state.waiting:
        message = ''

        if waiting.message:
            message = waiting.message.partition('container')[0].replace(": unknown", '')

        if waiting.reason in ('ImagePullBackOff', 'ErrImagePull'):
            container_info['state'] = 'creating'
            container_info['message'] = f'Image pull error'

        elif waiting.reason in ('CrashLoopBackOff',):
            container_info['state'] = 'crash'
            message = message.partition('container')[0].strip()
            container_info['message'] = f'Container crashed: {message}'

        elif waiting.reason in ('RunContainerError', 'StartError'):
            container_info['state'] = 'crash'
            msg = message.split(':', 1)
            if len(msg) > 1:
                container_info['message'] = f'Container crashed: {" . ".join(msg[1:])}'
            else:
                container_info['message'] = f'Container crashed: {message}'

        elif waiting.reason in ('PodInitializing',):
            container_info['state'] = 'pending'

        else:
            container_info['state'] = 'creating'

    elif container.state.running:
        container_info['state'] = 'running'

        started_at = container.state.running.started_at
        container_info['started_at'] = started_at.isoformat() if started_at else None

    elif container.state.terminated:
        container_info['state'] = 'terminated'

    term_last_state = container.last_state.terminated

    if container_info['state'] == 'crash' and term_last_state:
        if term_last_state.reason == 'Error':
            container_info['message'] += f' (received exit code {term_last_state.exit_code})'

        elif term_last_state.reason == 'StartError':
            msg = term_last_state.message.replace(': unknown', '').split(':', 1)
            if len(msg) > 1:
                container_info['message'] = f'Container crashed: {"".join(msg[1:]).strip()}'
            elif msg:
                container_info['message'] += " ".join(msg)

    return container_info


async def fetch_metric(client, url, metric_name, query, params):
    try:
        response = await client.get(url, params={'query': query, **params})
        response.raise_for_status()
        result = response.json().get('data', {}).get('result', [])
        return metric_name, result[0]['values'] if result else []
    except Exception as e:
        logging.error(f"Error fetching {metric_name}: {str(e)}")
        return metric_name, []


async def fetch_usage(client, url, query: str, metric_name: str) -> float:
    try:
        response = await client.get(url, params={'query': query}, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        result = data.get('data', {}).get('result', [])
        if not result:
            return 0
        return float(result[0]['value'][1])

    except Exception as e:
        logging.error(f"Error fetching {metric_name}: {str(e)}")
        raise e


async def fetch_metric_server_stat(client, url: str) -> dict:
    try:
        response = await client.get(url, timeout=5)
        response.raise_for_status()
        metrics = response.json()

        result = {
            'main': {},
            'sidecar': {},
            'init': {},
            'total': {},
        }

        if metrics.get('containers') is None:
            return result

        total_cpu = 0
        total_memory = 0

        for container in metrics['containers']:
            usage = {
                'cpu': round(cpu_to_cores(container['usage']['cpu']), 4),
                'memory': round(memory_to_mb(container['usage']['memory'], mib=True), 4)
            }

            if container['name'] == 'main':
                result['main'] = usage

            elif container['name'] == 'sidecar':
                result['sidecar'] = usage

            elif container['name'] == 'init':
                result['init'] = usage

            total_cpu += usage['cpu']
            total_memory += usage['memory']

        result['total']['cpu'] = total_cpu
        result['total']['memory'] = total_memory

        return result

    except Exception:
        return {
            'main': {},
            'sidecar': {},
            'init': {},
            'total': {
                'cpu': 0,
                'memory': 0
            },
        }


def get_state_from_conditions(k8s_conditions: list, default='unknown') -> str:
    conditions = sorted(k8s_conditions, key=lambda x: x.last_transition_time, reverse=True)

    for condition in conditions:
        if condition.type == 'Ready':
            ready = condition.status == 'True'
            if ready:
                return 'active'

    for condition in conditions:
        if condition.status == 'True':
            return STATE_TRANSLATIONS.get(condition.type, default)


CPU_CONV_FACTORS = {
    'n': 1e-9,
    'u': 1e-6,
    'm': 1e-3,
    '': 1
}


def cpu_to_cores(value: str) -> float:
    if not value:
        return 0.0

    unit = next((u for u in CPU_CONV_FACTORS.keys() if value.endswith(u)), '')
    try:
        number = float(value.rstrip('nmu'))
        return round(number * CPU_CONV_FACTORS[unit], 3)
    except ValueError:
        return 0.0


MEM_CONV_FACTORS = {
    "K": 1e-3, "Ki": 1 / 1024,
    "M": 1, "Mi": 1,
    "G": 1e3, "Gi": 1024,
    "T": 1e6, "Ti": 1024 ** 2
}


def memory_to_mb(value: str, mib=False) -> float:
    match = re.match(r"(\d+(\.\d+)?)([KMGTP]i?|[kmgpt]i?)", value)
    if not match:
        raise ValueError(f"Invalid memory format: {value}")

    num, _, unit = match.groups()
    num = float(num)
    unit = unit.capitalize()

    if unit not in MEM_CONV_FACTORS:
        raise ValueError(f"Unknown unit: {unit}")

    factor = MEM_CONV_FACTORS[unit if mib else unit.rstrip("i")]
    return round(num * factor, 3)


def get_stat_from_deployment(deployment) -> dict:
    cpu_limit = 0
    mem_limit = 0

    for container in deployment.spec.template.spec.containers:
        print(container.to_dict())
        if limits := container.resources.limits:
            cpu_limit += cpu_to_cores(limits['cpu'])
            mem_limit += memory_to_mb(limits['memory'], mib=True)

    available_replicas = deployment.status.available_replicas or 0
    unavailable_replicas = deployment.status.unavailable_replicas or 0
    updated_replicas = deployment.status.updated_replicas or available_replicas

    stat = {
        'app_state': get_state_from_conditions(deployment.status.conditions),
        'cpu_limit': cpu_limit * available_replicas if available_replicas else -1,
        'memory_limit': mem_limit * available_replicas if available_replicas else -1,
        'running': available_replicas,
        'pending': unavailable_replicas,
        'desired': updated_replicas or available_replicas + unavailable_replicas,
    }

    return stat
