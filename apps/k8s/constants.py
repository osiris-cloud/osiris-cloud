R_STATES = (('creating', 'Resource is being created'),
            ('updating', 'Resource is being updated'),
            ('deleting', 'Resource is being deleted'),
            ('active', 'Resource is live'),
            ('stopped', 'Resource is stopped'),
            ('error', 'Resource is in error'),
            ('zombie', 'Resource exists in database but in cluster'),
            )

PVC_CONTAINER_MODES = (('', 'No Access'), ('ro', 'Read Only'), ('rw', 'Read Write'))

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

SECRET_TYPES = (('opaque', 'Key value pair secret'),
                ('auth', 'Auth secret'),
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

ACCESS_SCOPES = ('global',
                 'container-registry',
                 'container-apps',
                 'namespace',
                 'secret-store',
                 )
