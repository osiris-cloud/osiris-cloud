from django.http import HttpResponsePermanentRedirect


class RemoveSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.split('/')
        if len(path) > 1:
            if 'admin' in path[1]:
                pass
            elif request.path.endswith('/') and len(request.path) > 1:
                return HttpResponsePermanentRedirect(request.path[:-1])
        try:
            response = self.get_response(request)
            return response
        except Exception:
            print("Middleware exception")
