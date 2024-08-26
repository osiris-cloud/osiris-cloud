from django.contrib.auth.decorators import login_required
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


@login_required
def dashboard(request):
    context = {
        'segment': ['dashboard'],
        'ver': '0.1',
    }
    return render(request, "dashboard/app.html", context)


def logout_view(request):
    request.session.clear()
    logout(request)
    return redirect('index')


def not_found(request):
    return render(request, "404.html", status=404)


def seed(request):
    from .seeder import create_users
    create_users()
    return redirect('login_view')
