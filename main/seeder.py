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


def create_pvcs():
    from json import load as json_load
    from apps.users.models import User
    from apps.k8s.models import Namespace, PVC
    with open(r'./seed/pvcs.json') as f:
        pvcs = json_load(f)

    for pvc in pvcs:
        owner = User.objects.get(id=pvc['owner_id'])
        namespace = Namespace.objects.get(id=pvc['namespace_id'])

        PVC.objects.create(
            name=pvc['name'],
            size=pvc['size'],
            owner=owner,
            namespace=namespace
        )

# TODO: Add seed data for other models
def create_vms():
    from json import load as json_load
    from apps.k8s.models import Namespace, PVC
    from apps.vm.models import VM
    from apps.users.models import User
    with open(r'./seed/vms.json') as f:
        vms = json_load(f)

    for vm in vms:
        disk = PVC.objects.get(id=vm['disk_id'])
        owner = User.objects.get(id=vm['owner_id'])
        namespace = Namespace.objects.get(id=vm['namespace_id'])

        VM.objects.create(
                name=vm['name'],
                k8s_name=vm['k8s_name'],
                cpu=vm['cpu'],
                memory=vm['memory'],
                disk=disk,
                owner=owner,
                namespace=namespace
            )


def create_events():
    from json import load as json_load
    from apps.k8s.models import Namespace, Event

    with open(r'./seed/events.json') as f:
        events = json_load(f)

    for event in events:
        namespace = Namespace.objects.get(id=event['namespace_id'])
        
        Event.objects.create(
            namespace=namespace,
            message=event['message'],
            related_link=event['related_link'],
            read=event['read']
        )