from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator

from ..users.models import User
from ..api.models import AccessToken


def init_app(_):
    actions = []
    if not User.objects.filter(username='osirisadmin').exists():
        from os import getenv
        User.objects.create_superuser(username='osirisadmin',
                                      first_name='Osiris',
                                      last_name='Admin',
                                      email='infra@osiriscloud.io',
                                      password=getenv('ADMIN_PASSWORD', 'osirisadmin'))
        actions.append('Admin user created')

    if not AccessToken.objects.filter(user__username='osirisadmin').exists():
        AccessToken.objects.create(user=User.objects.get(username='osirisadmin'),
                                   name='SYS_KEY',
                                   scopes=['global'],
                                   )
        actions.append('System key created')

    return HttpResponse({", ".join(actions) if actions else "No actions taken"})


@login_required
def dashboard(request):
    if (request.user.role == 'super_admin') or request.user.is_superuser:
        return render(request, 'admin_console/dashboard.html', context={
            'segment': ['dashboard'],
        })

    return render(request, '403-admin.html')


@login_required
def users(request):
    if (request.user.role == 'super_admin') or request.user.is_superuser:
        user_list = User.objects.exclude(username="osirisadmin")
        paginator = Paginator(user_list, 15)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, 'admin_console/users.html', context={
            'segment': ['users'],
            'page_obj': page_obj,
        })
    return render(request, '403-admin.html')
