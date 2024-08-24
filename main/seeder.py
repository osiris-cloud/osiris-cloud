def create_users():
    from django.utils import timezone
    from json import load as json_load

    from apps.k8s.models import Namespace, NamespaceRoles
    from apps.users.models import User, Limit
    from apps.oauth.models import NYUUser
    from core.utils import random_str

    with open(r'./seed/users.json') as f:
        users = json_load(f)

    for user in users:
        sample_user = User.objects.create_user(
            username=user['username'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            email=user['email'],
            last_login=timezone.now(),
            role=user['role'],
            avatar=user['avatar']
        )

        NYUUser.objects.create(first_name=user['first_name'],
                               last_name=user['last_name'],
                               netid=user['sub'],
                               affiliation=user['eduperson_primary_affiliation'],
                               user=sample_user
                               )

        ns_name = user['sub'] + random_str()

        ns = Namespace.objects.create(nsid=ns_name, name='Default', default=True)
        NamespaceRoles.objects.create(namespace=ns, user=sample_user, role='owner')
        Limit.objects.create(user=sample_user, **user['limits'])

# TODO: Add seed data for other models
