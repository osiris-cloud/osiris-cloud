from algoliasearch_django import AlgoliaIndex
from algoliasearch_django.decorators import register

from .models import User


@register(User)
class UserIndex(AlgoliaIndex):
    fields = ('first_name', 'last_name', 'username', 'email', 'avatar')
    settings = {'searchableAttributes': ['first_name', 'last_name', 'username', 'email']}
    index_name = 'users'
    should_index = 'not_manager'
