from django.shortcuts import render
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

from ..users.decorator import namespaced

from .models import ContainerApp


@login_required
@namespaced
def container_apps(request, nsid):
    context = {
        'segment': ['container_apps', 'list'],
    }
    return render(request, "apps/container-apps.html", context)


@login_required
@namespaced
def container_apps_create(request, nsid):
    context = {
        'segment': ['container_apps', 'create'],
    }
    return render(request, "apps/container-apps.html", context)


@login_required
@namespaced
def container_apps_view(request, nsid, appid):
    try:
        app = ContainerApp.objects.get(appid=appid)
    except ContainerApp.DoesNotExist:
        return render(request, "pages/404-app.html", status=404)

    cache_key = f'container_app_{appid}_info'
    cache.set(cache_key, app.info(), timeout=2)

    containers = {}
    for container in app.containers.all():
        containers[container.type] = container.info()

    context = {
        'segment': ['container_apps', 'view'],
        'app': app,
        'nsid': nsid,
        'containers': containers,
    }

    return render(request, "apps/container-apps.html", context)


@login_required
@namespaced
def container_apps_edit(request, nsid, appid):
    try:
        app = ContainerApp.objects.get(appid=appid)
    except ContainerApp.DoesNotExist:
        return render(request, "pages/404-app.html", status=404)

    if request.ns_role == 'viewer':
        return render(request, "pages/403-app.html", status=403)

    cache_key = f'container_app_{appid}_info'
    cache.set(cache_key, app.info(), timeout=2)

    context = {
        'app': app,
        'segment': ['container_apps', 'edit'],
    }

    return render(request, "apps/container-apps.html", context)
