import hashlib
import os
import random
import string
import boto3

from datetime import datetime, timedelta
from django.utils import timezone
from django.core import serializers as django_serializers
from pytz import timezone as pytz_timezone
from hashlib import sha256

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from base64 import b32encode

from kubernetes_asyncio import config as k8s_aio_config
from kubernetes_asyncio.client.api_client import ApiClient as k8s_aio_ApiClient, Configuration as k8s_aio_Configuration
from kubernetes_asyncio.stream import WsApiClient as k8s_aio_WsApiClient


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


def similar_time(t1: datetime, t2: datetime) -> bool:
    return abs(t1 - t2) < timedelta(seconds=0.5)


def serialize_obj(obj):
    return django_serializers.serialize('json', [obj])


def deserialize_obj(obj):
    return list(django_serializers.deserialize('json', obj))[0].object


def load_file_from_s3(object_path, access_key, secret_key, default=None) -> str | None:
    try:
        s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        bucket_name, object_key = object_path.split('/', 1)
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_contents = response['Body'].read().decode('utf-8')
        return file_contents
    except Exception:
        return default


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


def sponge_string(long_string: str, n=32) -> str:
    hash_obj = sha256(long_string.encode())
    hash_hex = hash_obj.hexdigest()
    return hash_hex[:n]


def cleanup():
    """
    Clean up temporary files
    """
    from .settings import env
    for temp_file in (env.k8s_auth['ca_cert'], env.k8s_auth['client_cert'], env.k8s_auth['client_key']):
        try:
            temp_file.close()
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")


def make_hashable(obj: dict | list | tuple) -> frozenset | tuple:
    if isinstance(obj, dict):
        return frozenset((k, make_hashable(v)) for k, v in obj.items())
    elif isinstance(obj, (list, tuple)):
        return tuple(make_hashable(i) for i in obj)
    return obj


async def get_k8s_api_client(ws=False) -> k8s_aio_ApiClient:
    """
    :param ws: Whether to return a websocket client
    Returns a Kubernetes async API client. Should call client.close() when done
    """
    from .settings import env
    k8s_config = k8s_aio_Configuration()
    await k8s_aio_config.load_kube_config_from_dict(
        config_dict=env.k8s_config_dict,
        client_configuration=k8s_config
    )

    if ws:
        api_client = k8s_aio_WsApiClient(configuration=k8s_config)
    else:
        api_client = k8s_aio_ApiClient(configuration=k8s_config)

    return api_client
