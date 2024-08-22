import string
from core.utils import error_message, success_message

VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')

def validate_ns_creation(ns_data: dict) -> tuple[bool, dict]:
    """
    Validate the data for creating a namespace
    Returns a tuple of (valid, message)
    """

    if ns_data is None:
        return False, error_message('Missing data')

    str_types = ['name']
    user_role_options = ['manager', 'viewer']

    for field in str_types:
        if field not in ns_data.keys():
            return False, error_message(f'Missing field: {field}')
    
    # Validate name
    ns_name = ns_data.get('name')
    if not ns_name or not isinstance(ns_name, str) or ns_name.strip() == '':
        return False, error_message('Invalid or missing namespace name')

    # Validate default
    ns_default = ns_data.get('default')
    if ns_default is not None and not isinstance(ns_default, bool):
        return False, error_message('Invalid default type')
    
    # Validate users
    ns_users = ns_data.get('users')
    if ns_users is not None:
        if not isinstance(ns_users, list):
            return False, error_message('Invalid users type')
        for user in ns_users:
            if not isinstance(user, dict):
                return False, error_message('Invalid user data type')
            if 'username' not in user or not isinstance(user['username'], str):
                return False, error_message('Invalid user username type')
            if 'role' not in user or user['role'] not in user_role_options:
                return False, error_message('Invalid user role')

    return True, success_message()

def validate_ns_update(ns_data: dict, nsid: str) -> tuple[bool, dict]:
    """
    Validate the data for updating a namespace
    Returns a tuple of (valid, message)
    """

    if not nsid or not isinstance(nsid, str):
        return False, error_message('Invalid or missing nsid')
    
    user_role_options = ['manager', 'viewer']
    
    ns_name = ns_data.get('name')
    if ns_name is not None and not isinstance(ns_name, str):
        return False, error_message('Invalid name type')
    
    ns_default = ns_data.get('default')
    if ns_default is not None and not isinstance(ns_default, bool):
        return False, error_message('Invalid default type')

    ns_owner = ns_data.get('owner')
    if ns_owner is not None:
        if not isinstance(ns_owner, dict):
            return False, error_message('Invalid owner type')
        if 'username' not in ns_owner or not isinstance(ns_owner['username'], str):
            return False, error_message('Invalid owner username type')

    ns_users = ns_data.get('users')
    if ns_users is not None:
        if not isinstance(ns_users, list):
            return False, error_message('Invalid users type')
        for user in ns_users:
            if not isinstance(user, dict):
                return False, error_message('Invalid user data type')
            if 'username' not in user or not isinstance(user['username'], str):
                return False, error_message('Invalid user username type')
            if 'role' not in user or user['role'] not in user_role_options:
                return False, error_message('Invalid user role')
            
    return True, success_message()

def sanitize_nsid(nsid: str) -> str:
    nsid = nsid.lower().replace(' ', '-')
    nsid = ''.join(ch for ch in nsid if ch in VALID_NAME_CHARLIST)

    # Ensure nsid does not start or end with a hyphen
    nsid = nsid.strip('-')

    # Split nsid into words
    words = nsid.split('-')

    # Reconstruct nsid ensuring it does not exceed 15 characters
    trimmed_nsid = ''
    for word in words:
        if len(trimmed_nsid) + len(word) + 1 > 15:
            break
        if trimmed_nsid:
            trimmed_nsid += '-'
        trimmed_nsid += word

    # Handle case where trimmed_nsid is empty
    if not trimmed_nsid:
        trimmed_nsid = nsid[:15]

    return trimmed_nsid