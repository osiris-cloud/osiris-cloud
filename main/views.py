from django.shortcuts import render, redirect
from django.contrib.auth import logout


def index(request):
    return render(request, "pages/index.html")


def faq(request):
    return render(request, "pages/faq.html")


def about(request):
    return render(request, "pages/about.html")


def architecture(request):
    return render(request, "pages/architecture.html")


def observability(request):
    return render(request, "pages/observability.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def logout_view(request):
    request.session.clear()
    logout(request)
    return redirect('index')


def not_found(request):
    return render(request, "404.html", status=404)


def seed(request):
    from .seeder import create_users, create_vms, create_pvcs, create_events
    create_users()
    create_pvcs()
    create_vms()
    create_events()
    return redirect('login_view')
