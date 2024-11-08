from django.shortcuts import render
from django.http import JsonResponse
from uuid import UUID

from django.contrib.auth.decorators import login_required
from ..users.decorator import namespaced
from .models import ContainerRegistry


@login_required
@namespaced
def container_registry(request, nsid):
    context = {
        'segment': ['container_registry', 'list'],
    }
    return render(request, "apps/container-registry.html", context)


@login_required
@namespaced
def container_registry_create(request, nsid):
    context = {
        'segment': ['container_registry', 'create'],
    }
    return render(request, "apps/container-registry.html", context)


@login_required
@namespaced
def container_registry_edit(request, nsid, crid):
    try:
        crid = UUID(crid)
    except ValueError:
        return render(request, "404-app.html", status=404)

    cr = ContainerRegistry.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "404-app.html", status=404)

    if request.ns_role == 'viewer':
        return render(request, "403-app.html", status=403)

    context = {
        'segment': ['container_registry', 'edit'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-registry.html", context)


@login_required
@namespaced
def container_registry_view(request, nsid, crid):
    try:
        crid = UUID(crid)
    except ValueError:
        return render(request, "404-app.html", status=404)

    cr = ContainerRegistry.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "404-app.html", status=404)

    context = {
        'segment': ['container_registry', 'view'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-registry.html", context)
