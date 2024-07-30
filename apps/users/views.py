from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView, PasswordResetConfirmView
# from django.views.generic import CreateView
# from apps.users.models import User
# from django.contrib.auth import logout
# from django.urls import reverse
# from django.http import HttpResponse
# from django.contrib import messages
# from django.contrib.auth.models import User
# from django.core.paginator import Paginator
# from apps.users.utils import user_filter


@login_required
def profile(request):
    ns = request.user.namespaces.filter(role='owner').filter(namespace__default=True).first().namespace
    return render(request, 'dashboard/profile.html', context={
        'github': request.user.github.first().username if request.user.github.first() else None,
        'nsid': ns.nsid if ns else None,
        'limit': ns.limit.all().first() if ns else None,
        'segment': ['profile'],
    })
