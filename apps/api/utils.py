from ..k8s.constants import ACCESS_SCOPES
from datetime import datetime, timezone


def validate_create_token(data: dict) -> tuple[bool, str | None]:
    if not isinstance(data, dict):
        return False, "Invalid data"
    name = data.get('name')
    if name is None:
        return False, "Name is required"
    if not isinstance(name, str):
        return False, "Name must be a string"

    app_scopes = data.get('scopes')
    if app_scopes is None:
        return False, "Scopes are required"
    if not isinstance(app_scopes, list):
        return False, "Scopes must be an array"

    if not all([scope in ACCESS_SCOPES for scope in app_scopes]):
        return False, "Invalid scopes"

    if data.get('can_write') is None:
        return False, "Write permission must be specified"

    if not isinstance(data['can_write'], bool):
        return False, "Write permission must be a boolean"

    expiration = data.get('expiration')

    if (expiration is not None) and (not isinstance(expiration, str)):
        return False, "Expiration must be a string or null"

    if expiration is not None:
        try:
            exp = datetime.fromisoformat(expiration)
            if exp.astimezone(timezone.utc) < datetime.now(timezone.utc):
                return False, "Expiration must be in the future"
        except ValueError:
            return False, "Expiration must be a string in ISO format"

    return True, None


def extract_app_name(url_path):
    """
    Extract app name from URL path following the pattern:
    <origin>/<app>/<nsid>/<resource-id>/<option>
    """
    parts = url_path.strip('/').split('/')  # Remove leading/trailing slashes

    if len(parts) >= 2:
        return parts[1]
    return None
