R_STATES = (('creating', 'Resource is being created'),
            ('active', 'Resource is live'),
            ('stopped', 'Resource is stopped'),
            ('deleting', 'Resource is being deleted'),
            ('error', 'Resource is in error'))

DOCKER_HEADERS = {
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
}
