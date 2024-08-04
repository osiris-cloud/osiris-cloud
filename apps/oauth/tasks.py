from celery import shared_task
from core.utils import deserialize_obj, random_str

from .utils import get_avatar, upload_to_r2

import logging


@shared_task(name='set_profile_avatar')
def set_profile_avatar(user):
    user = deserialize_obj(user)
    filename = f'{user.username}-{random_str(10)}.png'
    avatar_data = get_avatar(user.first_name, user.last_name)
    upload_to_r2(avatar_data, filename)
    user.avatar = 'https://blob.osiriscloud.io/avatar/' + filename
    user.save()
    logging.info(f"Avatar set for user {user.username}")
    return True
