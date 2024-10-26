from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..users.decorator import namespaced


@login_required
@namespaced
def dashboard(request, nsid):
    context = {
        'segment': ['dashboard'],
    }
    return render(request, "apps/dashboard/app.html", context)
