R_STATES = (('creating', 'Resource is being created'),
            ('updating', 'Resource is being updated'),
            ('deleting', 'Resource is being deleted'),
            ('created', 'Resource is created'),
            ('active', 'Resource is live'),
            ('stopped', 'Resource is stopped'),
            ('error', 'Resource is in error'),
            ('zombie', 'Resource exists in database but in cluster'),
            ('orphan', 'Resource exists in cluster but not in database'),
            )

VOLUME_MODES = (('', 'No Access'), ('ro', 'Read Only'), ('rw', 'Read Write'))

VOLUME_TYPES = (('temp', 'Temporary Storage'), ('fs', 'File System'), ('block', 'Block Device'), ('secret', 'Secret'))

DOCKER_HEADERS = {
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
}

NS_ROLES = (
    ('owner', 'Owner: Full control'),
    ('manager', 'Manager: Read and write'),
    ('viewer', 'Viewer: Read only'),
)

LB_PROTOCOLS = (
    ('tcp', 'TCP'),
    ('udp', 'UDP'),
)

DEFAULT_LIMIT = {
    'cpu': 0,
    'memory': 0,
    'disk': 0,
    'public_ip': 0,
    'gpu': 0,
    'registry': 0,
}

DEFAULT_ROLE = 'guest'

SECRET_TYPES = (('opaque', 'Key value pair secrets'),
                ('dockerconfig', 'Docker config'),
                )

DEFAULT_HPA_SPEC = {
    'enable': False,
    'min_replicas': 1,
    'max_replicas': 1,
    'scaleup_stb_window': 300,
    'scaledown_stb_window': 300,
    'cpu_trigger': 90,
    'memory_trigger': 90,
}

RESTART_POLICIES = {
    'always': 'Always',
    'on_failure': 'OnFailure',
    'never': 'Never'
}

ACCESS_SUB_SCOPES = {
    'global': [],
    'container-registry': [
        'all',
        'registry-login',
    ],
    'container-apps': [],
    'namespace': [],
    'secret-store': [],
}

ACCESS_SCOPES = tuple(ACCESS_SUB_SCOPES.keys())

DOMAIN_REGEX = r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.[A-Za-z0-9-]{1,63}(?<!-)){1,}(?:\.[A-Za-z]{2,6})$'

SLUG_REGEX = r'^[a-z0-9]+(-[a-z0-9]+)*$'

NYU_SUBNETS = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "59.79.127.0/24",
    "91.230.41.0/24",
    "94.56.130.144/28",
    "94.200.220.160/27",
    "101.231.120.128/27",
    "103.242.128.0/22",
    "128.122.0.0/16",
    "128.238.0.0/16",
    "176.74.48.32/27",
    "192.76.177.0/24",
    "192.86.139.0/24",
    "195.113.94.0/24",
    "192.114.110.0/24",
    "193.146.139.0/25",
    "193.175.54.0/24",
    "193.205.158.0/25",
    "193.206.104.0/24",
    "194.214.81.0/24",
    "195.229.110.0/25",
    "195.229.110.128/26",
    "202.66.60.160/27",
    "203.174.165.128/25",
    "212.219.93.0/24",
    "213.42.147.0/26",
    "216.165.0.0/17",
)

STATE_TRANSLATIONS = {
    'Available': 'active',
    'Running': 'active',
    'Ready': 'active',
    'Succeeded': 'success',
    'ContainersReady': 'active',

    'Pending': 'creating',
    'Initialized': 'creating',
    'PodScheduled': 'creating',

    'PodReadyToStartContainers': 'pending',

    'Progressing': 'updating',

    'Failed': 'error',
    'CrashLoopBackOff': 'crash',
}

K8S_WATCH_EVENT_EQS = {
    'ADDED': 'add',
    'MODIFIED': 'modify',
    'DELETED': 'delete',
    'ERROR': 'error',
}
