from django.conf import settings


def version(request):
    return {'ver': getattr(settings, 'VER', 'Unknown')}
