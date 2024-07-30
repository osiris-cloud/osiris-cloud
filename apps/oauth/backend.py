from django.contrib.auth.backends import BaseBackend
from django.utils import timezone
import logging

from .models import NYUUser, GithubUser, User


class AuthBackend(BaseBackend):
    def authenticate(self, request, mode: str = '', user_info: dict | None = None, username=None, password=None):

        if (user_info is None) and (username is None or password is None):
            return None

        try:
            if mode == 'nyu':
                user_info = user_info['userinfo']
                if nyu_user := NYUUser.objects.get(netid=user_info['sub']):
                    user = nyu_user.user
                    user.first_name = nyu_user.first_name = user_info['firstname']
                    user.last_name = nyu_user.last_name = user_info['lastname']
                    nyu_user.affiliation = user_info['eduperson_primary_affiliation']
                    user.last_login = timezone.now()
                    user.save()
                    logging.info('nyu user logged in %s', user_info['sub'])
                    return user

            elif mode == 'github':
                if github_user := GithubUser.objects.get(uid=user_info['id']):
                    github_user.username = user_info['login']  # Update user info on every login
                    github_user.name = user_info['name']
                    github_user.email = user_info['email']
                    github_user.save()

                    user = github_user.user

                    if user is None:
                        logging.error('github user does not exist: %s', user_info['login'])
                        return None

                    user.last_login = timezone.now()  # Update last login time
                    user.save()
                    logging.info('Github login: %s', user_info['login'])
                    return user
            else:
                mode = 'staff'
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user

        # If user does not exist, it will caught by an exception
        except (User.DoesNotExist, NYUUser.DoesNotExist, GithubUser.DoesNotExist):
            message = (user_info['sub'] if mode == 'nyu' else user_info['login']) if mode != 'staff' else username
            logging.info(f'{mode} user does not exist: {message}')
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
