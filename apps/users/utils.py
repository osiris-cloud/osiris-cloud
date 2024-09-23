import string
import re
import requests
import logging
from core.utils import error_message, success_message
from core.settings import env

VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')
MAILGUN_API_KEY = env.mailgun_api_key
MAILGUN_DOMAIN = env.mailgun_sender_domain
MAILGUN_SENDER_EMAIL = env.mailgun_sender_email


def validate_dict(d):
    if not isinstance(d, dict):
        return False
    for key, value in d.items():
        if isinstance(value, dict):
            return False
    return True


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
    if not ns_name:
        return False, error_message('Missing namespace name')
    if not isinstance(ns_name, str):
        return False, error_message('Invalid namespace name type')
    if ns_name.strip() == '':
        return False, error_message('Namespace name cannot be empty')

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
            if not validate_dict(user):
                return False, error_message('Invalid user data type')
            if 'username' not in user:
                return False, error_message('Missing user username')
            if not isinstance(user['username'], str):
                return False, error_message('Invalid user username type')
            if 'role' not in user:
                return False, error_message('Missing user role')
            if user['role'] not in user_role_options:
                return False, error_message('Invalid user role')

    return True, success_message({})


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
        if not validate_dict(ns_owner):
            return False, error_message('Invalid owner type')
        if 'username' not in ns_owner or not isinstance(ns_owner['username'], str):
            return False, error_message('Invalid owner username type')

    ns_users = ns_data.get('users')
    if ns_users is not None:
        if not isinstance(ns_users, list):
            return False, error_message('Invalid users type')
        for user in ns_users:
            if not validate_dict(user):
                return False, error_message('Invalid user data type')
            if 'username' not in user:
                return False, error_message('Missing user username')
            if not isinstance(user['username'], str):
                return False, error_message('Invalid user username type')
            if 'role' not in user:
                return False, error_message('Missing user role')
            if user['role'] not in user_role_options:
                return False, error_message('Invalid user role')

    return True, success_message({})


def sanitize_nsid(nsid: str) -> str:
    # Replace one or more spaces with a single dash
    nsid = re.sub(r'\s+', '-', nsid.lower())
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


def validate_user_update(user_data: dict) -> tuple[bool, dict]:
    """
    Validate the data for updating a user
    Returns a tuple of (valid, message)
    """
    valid_cluster_roles = ['super_admin', 'admin', 'user', 'guest', 'blocked']
    valid_resource_limits = ['cpu', 'memory', 'disk', 'public_ip', 'gpu']

    if 'first_name' in user_data and not isinstance(user_data['first_name'], str):
        return False, error_message('Invalid first name type')

    if 'last_name' in user_data and not isinstance(user_data['last_name'], str):
        return False, error_message('Invalid last name type')

    if 'email' in user_data and not isinstance(user_data['email'], str):
        return False, error_message('Invalid email type')

    if 'avatar' in user_data:
        if not isinstance(user_data['avatar'], str):
            return False, error_message('Invalid avatar type')
        # TODO: Additional validation for avatar URL

    if 'cluster_role' in user_data:
        if not isinstance(user_data['cluster_role'], str) or user_data['cluster_role'] not in valid_cluster_roles:
            return False, error_message('Invalid cluster role')

    if 'resource_limit' in user_data:
        if not validate_dict(user_data['resource_limit']):
            return False, error_message('Invalid resource limit type')
        for key, value in user_data['resource_limit'].items():
            if key not in valid_resource_limits:
                return False, error_message(f'Invalid resource limit key: {key}')
            if value is not None and not isinstance(value, int):
                return False, error_message(f'Invalid resource limit value for {key}')

    return True, success_message('User data is valid')


def delete_owner_resources(user_obj):
    # TODO: Handle actual resource deletion
    return True


def schedule_ns_deletion(namespace_obj):
    # TODO: Handle actual resource deletion
    return True


def send_email_notification(to_email, subject, text):
    response = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={"from": MAILGUN_SENDER_EMAIL,
              "to": to_email,
              "subject": subject,
              "text": text
              }
    )

    return response


def notify_new_owner(owner_email, namespace_id, namespace_name, requester_username):
    subject = "Namespace Ownership Transfer"

    text = (
        f"You have been assigned as the new owner of the namespace: {namespace_name} ({namespace_id}) by {requester_username}.\n"
    )
    response = send_email_notification(owner_email, subject, text)

    if response.status_code != 200:
        logging.error(f"Failed to send email notification to {owner_email}")
        return False

    return True
