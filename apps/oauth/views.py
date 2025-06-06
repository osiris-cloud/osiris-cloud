import logging

from authlib.integrations.django_client import OAuth
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.settings import env
from core.utils import random_str, serialize_obj

from ..infra.models import Namespace, NamespaceRoles
from ..users.models import Limit, Usage

from ..oauth.models import GithubUser, NYUUser
from ..users.models import User

from .tasks import set_profile_avatar

from ..infra.constants import DEFAULT_LIMIT, DEFAULT_ROLE

nyu_oauth = OAuth()
github_oauth = OAuth()

nyu_oauth.register(
    name='nyu',
    client_id=env.nyu_client_id,
    client_secret=env.nyu_client_secret,
    server_metadata_url=env.nyu_openid_meta,
    client_kwargs={'scope': 'openid'},
)

github_oauth.register(
    name='github',
    client_id=env.github_client_id,
    client_secret=env.github_client_secret,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    api_base_url='https://api.github.com',
    refresh_token_url=None,
    redirect_uri=None,
    client_kwargs={'scope': 'read:user'},
)


def login_view(request):
    if request.user.is_authenticated:
        next_url = request.GET.get('next', reverse("dashboard"))
        return redirect(next_url)

    next_url = request.GET.get('next', '')
    return render(request, 'pages/login.html', {'next': next_url})


def nyu_login(request):
    if next_url := request.GET.get('next', ''):  # Save the next URL to redirect after login
        request.session['original_next'] = next_url

    base_uri = request.scheme + '://' if env.debug else 'https://'
    redirect_uri = base_uri + request.get_host() + '/login/nyu/callback'
    return nyu_oauth.nyu.authorize_redirect(request, redirect_uri)


def nyu_callback(request):
    try:
        user_info = nyu_oauth.nyu.authorize_access_token(request)

        # if user exists, we log them in
        if user := authenticate(request, mode='nyu', user_info=user_info):
            if user.role == 'blocked':
                return HttpResponse('Your account is blocked. Please contact support.')

        # if user does not exist, we create a new account, and give them user role for now
        else:
            user_info = user_info['userinfo']

            with transaction.atomic():
                user = User.objects.create_user(
                    username=user_info['sub'],
                    first_name=user_info['firstname'],
                    last_name=user_info['lastname'],
                    email=user_info['sub'] + '@nyu.edu',
                    last_login=timezone.now(),
                    role=DEFAULT_ROLE,
                )

                NYUUser.objects.create(first_name=user_info['firstname'],
                                       last_name=user_info['lastname'],
                                       netid=user_info['sub'],
                                       affiliation=user_info['eduperson_primary_affiliation'],
                                       user=user
                                       )

                # We create a default NS for the user
                ns_name = user_info['sub'] + '-' + random_str()
                ns = Namespace.objects.create(nsid=ns_name, name='Default', default=True)
                logging.info(f"Default namespace {ns_name} created for user {user.username}")

                # We add the user to the NS role Table wih owner role
                NamespaceRoles.objects.create(namespace=ns, user=user, role='owner')

                Limit.objects.create(user=user, **DEFAULT_LIMIT)
                logging.info(f"Default limits applied for namespace {ns_name}")

                Usage.objects.create(user=user)

                # We set the user's profile avatar
                set_profile_avatar.delay(serialize_obj(user))

        login(request, user)

        next_url = request.session.get('original_next', reverse("dashboard"))

        if 'original_next' in request.session:
            del request.session['original_next']

        return redirect(next_url)

    except Exception as e:
        logging.exception(e)
        return redirect(request.build_absolute_uri(reverse("login_view")))


def github_login(request):
    base_uri = request.scheme + '://' if env.debug else 'https://'
    redirect_uri = base_uri + request.get_host() + '/login/github/callback'
    return github_oauth.github.authorize_redirect(request, redirect_uri)


def github_callback(request):
    try:
        token = github_oauth.github.authorize_access_token(request)
        user_info = github_oauth.github.get('user', token=token).json()

        # if user is already logged in and 'github_link_call' is set, we link the accounts together
        if request.user.is_authenticated and request.session.get('github_link_call'):
            GithubUser.objects.create(
                uid=user_info['id'],
                username=user_info['login'],
                name=user_info['name'] if user_info['name'] else user_info['login'],
                email=user_info['email'] if user_info['email'] else None,
                user=request.user
            )
            request.session.pop('github_link_call')
            return HttpResponse('Github account successfully linked! You can now close this window.')

        # if user is not logged in, we authenticate them
        else:
            # if user exists, we log them in. DOES NOT CREATE A NEW USER
            if user := authenticate(request, mode='github', user_info=user_info):
                if user.role == 'blocked':
                    return HttpResponse('Your account is blocked. Please contact support.')
                login(request, user)
                return redirect(request.build_absolute_uri(reverse("dashboard")))
            else:
                return redirect(request.build_absolute_uri(reverse("login_view")))

    except Exception as e:
        logging.exception(e)
        return redirect(request.build_absolute_uri(reverse("login_view")))


@login_required
def link_github(request):
    if GithubUser.objects.filter(user=request.user).exists():
        return HttpResponse('The authenticated Github is already linked to an account.')

    request.session['github_link_call'] = True
    redirect_uri = request.build_absolute_uri('/login/github/callback')
    return github_oauth.github.authorize_redirect(request, redirect_uri)


@login_required
def unlink_github(request):
    if github_user := GithubUser.objects.filter(user=request.user).first():
        github_user.delete()
        return HttpResponse('Github account unlinked! This window will close automatically.')
    return redirect(request.build_absolute_uri(reverse("profile")))


def seed_login(request):
    user = User.objects.filter().first()
    login(request, user)
    return redirect(request.build_absolute_uri(reverse("dashboard")))
