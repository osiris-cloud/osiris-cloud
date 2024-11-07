from django.shortcuts import render
from uuid_utils import UUID
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
def container_apps_edit(request, nsid, appid):
    try:
        crid = UUID(appid)
    except ValueError:
        return render(request, "404-app.html", status=404)

    cr = ContainerApp.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "404-app.html", status=404)

    if request.ns_role == 'viewer':
        return render(request, "403-app.html", status=403)

    context = {
        'segment': ['container_apps', 'edit'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-apps.html", context)


@login_required
@namespaced
def container_apps_view(request, nsid, appid):
    try:
        crid = UUID(appid)
    except ValueError:
        return render(request, "404-app.html", status=404)

    cr = ContainerApp.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "404-app.html", status=404)

    context = {
        'segment': ['container_apps', 'view'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-apps.html", context)
