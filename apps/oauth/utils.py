import httpx
import boto3
import random

from botocore.client import Config

from core.settings import env


def generate_color() -> str:
    r = random.randint(0, 150)
    g = random.randint(0, 150)
    b = random.randint(0, 150)
    return "{:02x}{:02x}{:02x}".format(r, g, b)


def get_avatar(first_name, last_name):
    with httpx.Client() as client:
        response = client.get(f"https://ui-avatars.com/api/?name={first_name}+{last_name}&background={generate_color()}&color=fff")
        response.raise_for_status()
        return response.content


def upload_to_r2(image_data, filename):
    s3 = boto3.client('s3',
                      endpoint_url=env.cf_storage_url,
                      aws_access_key_id=env.cf_access_key,
                      aws_secret_access_key=env.cf_secret_key,
                      config=Config(signature_version='s3v4'),
                      region_name='auto'
                      )

    s3.put_object(Bucket='avatar', Key=filename, Body=image_data, ContentType='image/png')
