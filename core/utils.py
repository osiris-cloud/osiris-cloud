import random
import string
import boto3

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


def get_s3_file_contents(object_path, access_key, secret_key) -> str | None:
    try:
        s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        bucket_name, object_key = object_path.split('/', 1)
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_contents = response['Body'].read().decode('utf-8')
        return file_contents
    except:
        return None
