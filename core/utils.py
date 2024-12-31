import hashlib
import random
import string
import boto3

from datetime import datetime
from django.utils import timezone
from django.core import serializers as django_serializers
from pytz import timezone as pytz_timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from base64 import b32encode


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


def load_file_from_s3(object_path, access_key, secret_key) -> str | None:
    try:
        s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        bucket_name, object_key = object_path.split('/', 1)
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_contents = response['Body'].read().decode('utf-8')
        return file_contents
    except:
        return None


def load_file(file_path, mode='r') -> str | None:
    try:
        with open(file_path, mode) as file:
            return file.read()
    except:
        return None


def generate_kid(private_key_data: bytes | str, key_type) -> str:
    """
    Generates a unique identifier (KID) from a private key file.
    """

    if isinstance(private_key_data, str):
        private_key_data = bytes(private_key_data, encoding='utf-8')
    public_key = None

    try:
        if key_type == 'EC':
            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=None,
                backend=default_backend()
            )
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

        elif key_type == 'RSA':
            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=None,
                backend=default_backend()
            )
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

        algorithm = hashlib.sha256()
        algorithm.update(public_key)

        encoded = b32encode(algorithm.digest()[:30]).decode('ascii').rstrip("=")

        return ':'.join(encoded[i:i + 4] for i in range(0, len(encoded), 4))

    except Exception as e:
        raise ValueError(f"Failed to generate KID: {str(e)}")
