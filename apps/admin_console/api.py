import asyncio

import httpx
import logging

from json import JSONDecodeError
from django.http import JsonResponse
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from asgiref.sync import async_to_sync

from ..infra.constants import DEFAULT_LIMIT
from ..infra.models import Namespace, NamespaceRoles
from ..users.models import Limit, Usage
from ..oauth.models import GithubUser

from core.utils import success_message, error_message, serialize_obj, random_str
from core.settings import env

from ..oauth.tasks import set_profile_avatar

User = get_user_model()


@api_view(['PUT'])
def external_user(request):
    if not ((request.user.role == 'super_admin') or request.user.is_superuser):
        return JsonResponse(error_message('Permission denied'), status=403)

    try:
        gh_id = request.data.get('gh_id')
        gh_username = request.data.get('gh_username')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        role = request.data.get('role')

        if not all([gh_id, gh_username, first_name, last_name, email]):
            return JsonResponse(error_message('All fields are required'), status=400)

        if GithubUser.objects.filter(uid=gh_id).exists():
            return JsonResponse(error_message('User already exists'), status=400)

        if User.objects.filter(username=gh_username + '-ext').exists():
            return JsonResponse(error_message('User already exists'), status=400)

        with transaction.atomic():
            user = User.objects.create_user(
                username=gh_username + '-ext',
                first_name=first_name,
                last_name=last_name,
                email=email,
                role=role,
            )

            user.save()

            GithubUser.objects.create(
                uid=gh_id,
                username=gh_username,
                name=first_name + ' ' + last_name,
                email=email,
                user=user,
            ).save()

            ns_name = gh_username + '-' + random_str()
            ns = Namespace.objects.create(nsid=ns_name, name='Default', default=True)
            logging.info(f"Default namespace {ns_name} created for user {user.username}")
            NamespaceRoles.objects.create(namespace=ns, user=user, role='owner')

            Limit.objects.create(user=user, **DEFAULT_LIMIT)
            logging.info(f"Default limits applied for namespace {ns_name}")

            Usage.objects.create(user=user, cpu=0, memory=0, disk=0, public_ip=0, gpu=0, registry=0)

            set_profile_avatar.delay(serialize_obj(user))

            return JsonResponse(success_message('User created successfully'), status=201)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)
    except Exception as e:
        logging.error(e)
        return JsonResponse(error_message('Internal server error'), status=500)


headers = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f'token {env.github_token}'
}


async def fetch_user_details(client, url):
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        user_details = response.json()
        return {
            'id': user_details['id'],
            'username': user_details['login'],
            'name': user_details['name'],
            'email': user_details['email'],
            'avatar': user_details['avatar_url'],
        }
    except Exception as e:
        logging.error(e)
        return {}


@api_view(['POST'])
def gh_user_search(request):
    if not ((request.user.role == 'super_admin') or request.user.is_superuser):
        return JsonResponse(error_message('Permission denied'), status=403)

    query = request.data.get('query')
    if not query:
        return JsonResponse(error_message('Query is required'), status=400)

    async def gh_user_search_async():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.github.com/search/users?q={query}", headers=headers)
                response.raise_for_status()
                data = response.json()

                tasks = [fetch_user_details(client, user['url']) for user in (data['items'][:5])]
                result = await asyncio.gather(*tasks)

                return JsonResponse(success_message('Search github users', {'users': result}), status=200)

        except Exception as e:
            logging.error(e)
            return JsonResponse(error_message('Internal Server error'), status=500)

    resp = async_to_sync(gh_user_search_async)()
    return resp
