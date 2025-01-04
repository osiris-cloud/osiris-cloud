from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from ..users.decorator import namespaced
from .models import Secret


@login_required
@namespaced
def secret_store(request, nsid):
    context = {
        'segment': ['secret_store', 'list'],
    }
    return render(request, "apps/secret-store.html", context)


@login_required
@namespaced
def secret_store_create(request, nsid):
    context = {
        'segment': ['secret_store', 'create'],
    }
    return render(request, "apps/secret-store.html", context)


@login_required
@namespaced
def secret_store_view(request, nsid, secret_id):
    try:
        secret = Secret.objects.get(secretid=secret_id)
        context = {
            'segment': ['secret_store', 'view'],
            'secret': secret,
        }
        return render(request, "apps/secret-store.html", context)
    except (ValueError, Secret.DoesNotExist):
        return render(request, "pages/404-app.html")


@login_required
@namespaced
def secret_store_edit(request, nsid, secret_id):
    try:
        secret = Secret.objects.get(secretid=secret_id)
        context = {
            'segment': ['secret_store', 'edit'],
            'secret': secret,
        }
        return render(request, "apps/secret-store.html", context)
    except (ValueError, Secret.DoesNotExist):
        return render(request, "pages/404-app.html")
