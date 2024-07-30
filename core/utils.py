import random
import string

from datetime import datetime
from django.utils import timezone
from django.core import serializers as django_serializers
from pytz import timezone as pytz_timezone


def success_message(message: str = '', data: dict | None = None) -> dict:
    if data is None:
        data = {}
    response = {
        'status': 'success',
        **data,
    }
    if message:
        response['message'] = message
    return response


def error_message(message: str = '', data: dict | None = None) -> dict:
    if data is None:
        data = {}
    response = {
        'status': 'error',
        **data,
    }
    if message:
        response['message'] = message
    return response


def random_str(length: int = 4) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def eastern_time(dt: datetime) -> str:
    dt_eastern = timezone.localtime(dt, pytz_timezone('US/Eastern'))
    return dt_eastern.strftime('%H:%M:%S, %a %d %b %Y')


def serialize_obj(obj):
    return django_serializers.serialize('json', [obj])


def deserialize_obj(obj):
    return list(django_serializers.deserialize('json', obj))[0].object
