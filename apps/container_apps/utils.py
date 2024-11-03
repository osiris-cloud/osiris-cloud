import re

from ..secret_store.models import Secret


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

    if replica := spec.get('replicas'):
        if not isinstance(replica, int):
            return False, 'replicas must be an integer'
        if replica < 1:
            return False, 'replicas must be greater than or equal to 0'

    if not isinstance(spec['exposed_public'], bool):
        return False, 'exposed_public must be a boolean'

    return True, None


def validate_app_update_spec(spec: dict) -> tuple[bool, [str | None]]:
    pass
