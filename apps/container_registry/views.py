from django.shortcuts import render

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
    cr = ContainerRegistry.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "pages/404-app.html", status=404)

    if request.ns_role == 'viewer':
        return render(request, "pages/403-app.html", status=403)

    context = {
        'segment': ['container_registry', 'edit'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-registry.html", context)


@login_required
@namespaced
def container_registry_view(request, nsid, crid):
    cr = ContainerRegistry.objects.filter(crid=crid).first()
    if not cr:
        return render(request, "pages/404-app.html", status=404)

    context = {
        'segment': ['container_registry', 'view'],
        'crid': crid,
        'cr': cr,
    }
    return render(request, "apps/container-registry.html", context)
