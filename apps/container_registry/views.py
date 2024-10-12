from django.shortcuts import render
from django.http import JsonResponse
from uuid import UUID

from .models import ContainerRegistry


def container_registry(request):
    context = {
        'segment': ['container_registry', 'list'],
    }
    return render(request, "apps/container-registry.html", context)


def container_registry_create(request):
    context = {
        'segment': ['container_registry', 'create'],
    }
    return render(request, "apps/container-registry.html", context)


def container_registry_edit(request):
    context = {
        'segment': ['container_registry', 'edit'],
    }
    return render(request, "apps/container-registry.html", context)


def container_registry_view(request, crid):
    try:
        crid = UUID(crid)
    except ValueError:
        return JsonResponse({'error': 'Invalid crid'}, status=400)

    cr = ContainerRegistry.objects.filter(crid=crid).first()

    context = {
        'segment': ['container_registry', 'view'],
        'crid': crid,
    }
    return render(request, "apps/container-registry.html", context)
