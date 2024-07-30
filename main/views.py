from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout


def index(request):
    return render(request, "pages/index.html")


def faq(request):
    return render(request, "pages/faq.html")


def about(request):
    return render(request, "pages/about.html")


@login_required
def dashboard(request):
    context = {
        'segment': ['dashboard'],
        'ver': '1.0',
    }
    return render(request, "dashboard/app.html", context)


def logout_view(request):
    request.session.clear()
    logout(request)
    return redirect('index')


def not_found(request):
    return render(request, "404.html", status=404)
