import string
from core.utils import error_message, success_message

VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')

def validate_ns_creation(ns_data: dict) -> tuple[bool, dict]:
    """
    Validate the data for creating a namespace
    Returns a tuple of (valid, message)
    """

    if ns_data is None:
        return False, error_message('Missing specs')

    str_types = ['name', 'default', 'users']
    user_role_options = ['manager', 'viewer']

    for field in str_types:
        if field not in ns_data.keys():
            return False, error_message(f'Wrong type for {field}')
    
    # Validate name
    ns_name = ns_data.get('name')
    if not ns_name or not isinstance(ns_name, str) or ns_name.strip() == '':
        return False, error_message('Invalid or missing namespace name')

    # Validate default
    ns_default = ns_data.get('default', False)
    if not isinstance(ns_default, bool):
        return False, error_message('Default value must be a boolean')
    
    # Validate users
    ns_users = ns_data.get('users', [])
    if not isinstance(ns_users, list):
        return False, error_message('Users must be a list')
    else:
        for user in ns_users:
            if not isinstance(user, dict):
                return False, error_message('Invalid users data type')
            
            username = user.get('username', '')
            role = user.get('role', '')

            if not isinstance(username, str):
                return False, error_message('Invalid username type')
            if role not in user_role_options:
                return False, error_message('Invalid role for user')

    return True, success_message()

def sanitize_nsid(nsid: str) -> str:
    nsid = nsid.lower().replace(' ', '-')
    return ''.join(ch for ch in nsid if ch in VALID_NAME_CHARLIST)