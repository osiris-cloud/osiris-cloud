from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator

from ..users.models import User


def init_app(request):
    if not User.objects.filter(username='osirisadmin').exists():
        from os import getenv
        User.objects.create_superuser(username='osirisadmin',
                                      first_name='Osiris',
                                      last_name='Admin',
                                      email='infra@osiriscloud.io',
                                      password=getenv('ADMIN_PASSWORD', 'admin'))
        return HttpResponse('Admin user created successfully.')

    return HttpResponse('Already initialized.')


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
