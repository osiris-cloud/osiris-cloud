from django.conf import settings


def version(request):
    return {
        'VER': getattr(settings, 'VER', 'Unknown'),
        'DEBUG': getattr(settings, 'DEBUG', False),
    }
