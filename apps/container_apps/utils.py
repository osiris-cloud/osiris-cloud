import re
import ipaddress

from core.settings import env
from .models import ContainerApp, CustomDomain
from ..container_registry.models import ContainerRegistry
from ..infra.models import Volume

from ..infra.constants import VOLUME_TYPES, DOMAIN_REGEX, SLUG_REGEX
from ..secret_store.models import Secret
from ..users.models import User

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


def validate_custom_domain_spec(custom_domains: list) -> tuple[bool, [str | None]]:
    if custom_domains == [] or custom_domains is None:
        return True, None

    if not isinstance(custom_domains, list):
        return False, 'custom_domains must be an array'

    for i, domain in enumerate(custom_domains):
        if not isinstance(domain, str):
            return False, f'custom_domains[{i}] must be a string'

        domain = domain.strip()

        if not DOMAIN_RE.match(domain):
            return False, f'custom_domains[{i}] is invalid'
        if domain == env.container_apps_domain or domain.endswith(f".{env.container_apps_domain}"):
            return False, f'custom_domains[{i}] is invalid'

        try:
            CustomDomain.objects.get(name=domain)
            return False, f'custom_domains[{i}] is already used'
        except ContainerApp.DoesNotExist:
            pass

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
            if each['threshold'] < 1 or each['threshold'] > 100:
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

    pass_tls = spec.get('pass_tls')
    if pass_tls is not None:
        if not isinstance(pass_tls, bool):
            return False, 'pass_tls must be a boolean'

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

    if custom_domains := spec.get('custom_domains'):
        valid, err = validate_custom_domain_spec(custom_domains)
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

    if custom_domains := spec.get('custom_domains'):
        valid, err = validate_custom_domain_spec(custom_domains)
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


def under_limits(spec: dict, user) -> bool:
    agg_cpu = 0
    agg_memory = 0
    agg_disk = 0
    scaling = spec.get('scaling', {})

    for cont in (spec.get('main'), spec.get('sidecar'), spec.get('init')):
        if cont:
            agg_cpu += cont['cpu'] * scaling.get('max_replicas', 1)
            agg_memory += cont['memory'] * scaling.get('max_replicas', 1)

    for vol in spec.get('volumes', []):
        agg_disk += vol['size']

    if user.limit.limit_reached(cpu=agg_cpu, memory=agg_memory, disk=agg_disk):
        return False

    return True

