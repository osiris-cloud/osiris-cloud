R_STATES = (('creating', 'Resource is being created'),
            ('updating', 'Resource is being updated'),
            ('deleting', 'Resource is being deleted'),
            ('active', 'Resource is live'),
            ('stopped', 'Resource is stopped'),
            ('error', 'Resource is in error'),
            ('zombie', 'Resource exists in database but in cluster')
            )

DOCKER_HEADERS = {
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
}
