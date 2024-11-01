from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from ..users.models import User


@login_required
def dashboard(request):
    if (request.user.role == 'super_admin') or request.user.is_superuser:
        return render(request, 'admin_console/dashboard.html', context={
            'segment': ['dashboard'],
        })

    return render(request, '403-admin.html')


def init_app(request):
    if not User.objects.filter(username='admin', is_superuser=True).exists():
        from os import getenv
        user = User.objects.create_superuser(username='osirisadmin',
                                             first_name='Osiris',
                                             last_name='Admin',
                                             email='infra@osiriscloud.io',
                                             password=getenv('ADMIN_PASSWORD', 'admin'))
        login(request, user)
        return HttpResponse('Admin user created successfully.')

    return HttpResponse('Already initialized.')


@login_required
def users(request):
    if (request.user.role == 'super_admin') or request.user.is_superuser:
        return render(request, 'admin_console/users.html', context={
            'segment': ['users'],
        })
    return render(request, '403-admin.html')
