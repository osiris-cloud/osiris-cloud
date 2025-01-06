from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..users.utils import get_default_ns


@login_required
def profile(request):
    default_ns = get_default_ns(request.user)
    if default_ns is None:
        return render(request, 'pages/404-app.html')

    return render(request, 'apps/pages/profile.html', context={
        'github': request.user.github.username if hasattr(request.user, 'github') else None,
        'default_ns': default_ns.nsid,
        'segment': ['profile'],
    })


@login_required
def access_keys(request):
    return render(request, 'apps/pages/access-keys.html')
