def validate_secret_creation(secret_data: dict) -> tuple[bool, [str | None]]:
    """
    Validate the data for creating a secret
    """
    if not secret_data:
        return False, 'Missing secret data'

    secret_name = secret_data.get('name')

    if not isinstance(secret_name, str):
        return False, 'Secret name must be a string'

    if not secret_name.strip():
        return False, 'Secret name cannot be empty'

    secret_type = secret_data.get('type')
    if secret_type not in ('opaque', 'dockerconfig'):
        return False, 'Invalid secret type'

    is_dockerconfig = (secret_type == 'dockerconfig')

    secret_values = secret_data.get('values', {})

    if not isinstance(secret_values, dict):
        return False, 'values must be an object'

    if is_dockerconfig:
        if len(secret_values) != 1:
            return False, 'Dockerconfig secret must have a single key .dockerconfigjson'
        if secret_values.get('.dockerconfigjson') is None:
            return False, 'Dockerconfig secret must have .dockerconfigjson key'

    for k, v in secret_values.items():
        if (not isinstance(k, str)) or (not isinstance(v, str)):
            return False, 'Key value pairs must be strings'

    return True, None


def validate_secret_update(secret_data: dict) -> tuple[bool, str | None]:
    """
    Validate the data for updating a secret
    """
    if secret_name := secret_data.get('name'):
        if not isinstance(secret_name, str):
            return False, 'Secret name must be a string'

    if secret_values := secret_data.get('values'):
        if not isinstance(secret_values, dict):
            return False, 'Values must be an object'

        for k, v in secret_values.items():
            if (not isinstance(k, str)) or (not isinstance(v, str)):
                return False, 'Key value pairs must be strings'

    return True, None
