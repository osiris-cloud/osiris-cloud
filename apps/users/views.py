from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..users.utils import get_default_ns


@login_required
def profile(request):
    if get_default_ns(request.user) is None:
        return render(request, '404-app.html')

    return render(request, 'apps/dashboard/profile.html', context={
        'github': request.user.github.first().username if request.user.github.first() else None,
        'segment': ['profile'],
    })
