import string
import re
import requests
import logging
from core.utils import error_message, success_message
from core.settings import env

from apps.users.models import User
from apps.infra.models import NamespaceRoles, Namespace


def get_default_ns(user: User) -> Namespace | None:
    try:
        return NamespaceRoles.objects.get(user=user, role='owner', namespace__default=True).namespace
    except:
        return None


def validate_users_dict_type(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    for key, value in d.items():
        if isinstance(value, dict):
            return False
    return True


def validate_ns_users(ns_users: list) -> tuple[bool, str | None]:
    if ns_users is not None:
        if not isinstance(ns_users, list):
            return False, 'users must be an array'

        user_role_options = ('manager', 'viewer')

        for i, user in enumerate(ns_users):
            if not isinstance(user, dict):
                return False, f'users[{i}] must be an object'
            if user.get('username') is None:
                return False, f'users[{i}] is missing username'
            if not isinstance(user['username'], str):
                return False, f'users[{i}][username] must be a string'
            if user.get('role') is None:
                return False, f'users[{i}] is missing role'
            if user['role'] not in user_role_options:
                return False, f'users[{i}][role] is invalid'

    return True, None


def validate_ns_create(ns_data: dict) -> tuple[bool, str | None]:
    """
    Validate the data for creating a namespace
    """
    if ns_data is None:
        return False, 'Missing data'

    # Validate name
    ns_name = ns_data.get('name')
    if ns_name is None:
        return False, 'Namespace name is required'
    if not isinstance(ns_name, str):
        return False, 'Namespace name must be a string'
    if ns_name.strip() == '':
        return False, 'Namespace name cannot be empty'

    # Validate default
    ns_default = ns_data.get('default')
    if (ns_default is not None) and (not isinstance(ns_default, bool)):
        return False, 'Invalid default type'

    # Validate users
    ns_users = ns_data.get('users')
    valid, err = validate_ns_users(ns_users)
    if not valid:
        return False, err

    return True, None


def validate_ns_update(ns_data: dict) -> tuple[bool, str | None]:
    """
    Validate the data for updating a namespace
    """
    # Validate name
    ns_name = ns_data.get('name')
    if ns_name is not None:
        if not isinstance(ns_name, str):
            return False, 'Namespace name must be a string'
        if ns_name.strip() == '':
            return False, 'Namespace name cannot be empty'

    # Validate default
    ns_default = ns_data.get('default')
    if (ns_default is not None) and (not isinstance(ns_default, bool)):
        return False, 'Invalid default type'

    # Validate owner
    owner = ns_data.get('owner')
    if owner is not None:
        if not isinstance(owner, dict):
            return False, 'Owner must be an object'
        if owner.get('username') is None:
            return False, 'Owner is missing username'

    # Validate users
    ns_users = ns_data.get('users')
    valid, err = validate_ns_users(ns_users)
    if not valid:
        return False, err

    return True, None


VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')


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
        if not validate_users_dict_type(user_data['resource_limit']):
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


def greater_than(r1: dict, r2: dict) -> bool:
    """
    Compare two resource dictionaries
    Returns True if r1 is less than r2, False otherwise
    """
    return all(r1[key] > r2[key] for key in r1)
