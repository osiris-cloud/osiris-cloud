from random import random, randint

from core.utils import error_message, success_message
import string
from ..k8s.utils import IMAGE_TAGS

VALID_NAME_CHARLIST = list(string.ascii_lowercase + string.digits + '_' + '-')


def validate_vm_spec(data: dict) -> tuple[bool, dict]:
    """
    Validate the data for creating a virtual machine
    Returns a tuple of (valid, message)
    """

    if data is None:
        return False, error_message('Missing specs')

    str_types = ['name', 'os', 'size', 'vm_username', 'vm_password', 'network_type']
    os_options = [x for x in IMAGE_TAGS.keys()]
    size_options = ['s1', 's2', 'm1', 'm2', 'l1', 'l2']
    network_options = ['private', 'vlab', 'public']

    for field in str_types:
        if field not in data.keys():
            return False, error_message(f'Wrong type for {field}')

    if data['os'] not in os_options:
        return False, error_message('Invalid OS')

    if data['size'] not in size_options:
        return False, error_message('Invalid size')

    if ssh_config := data.get('ssh_config'):
        if not isinstance(ssh_config, dict):
            return False, error_message('Invalid SSH config data type')
        if ['ssh_key', 'password_auth'] != list(ssh_config.keys()):
            return False, error_message('Invalid SSH config')
        if not isinstance(ssh_config.get('ssh_key'), str) or not isinstance(ssh_config.get('password_auth'), bool):
            return False, error_message('Invalid SSH config data type')

    if data['network_type'] not in network_options:
        return False, error_message('Invalid network type')

    return True, success_message()


def sanitize_vm_name(name: str) -> str:
    name = name.lower().replace(' ', '-')
    name = ''.join(x for x in name if x in VALID_NAME_CHARLIST)
    return name


def gen_mac_address():
    mac = 'BE:EF:69:'
    number = randint(0, 16777215)
    hex_num = hex(number)[2:].zfill(6)
    return "{}{}{}:{}{}:{}{}".format(mac, *hex_num).upper()
