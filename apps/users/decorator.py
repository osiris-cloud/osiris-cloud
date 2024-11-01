import re
from functools import wraps

from django.http import HttpResponse
from django.shortcuts import redirect, render
from core.settings import OC_APPS

from .utils import get_default_ns
from ..k8s.models import Namespace

CLIENT_APPS = [app.replace('apps.', '').replace('_', '-') for app in OC_APPS]


def namespaced(view_func):
    """
    Decorator to extract `nsid` from any request URL and attach it to the request object.
    The `nsid` is expected to be part of the URL in the format <app>/<nsid>/<option>/<resource id>.
    It checks for default nsid, and redirects when needed. This also validates the user's access to the given namespace.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        pattern = r'^/(?P<app>[^/]+)(?:/(?P<nsid>[0-9a-zA-Z_-]+))?(?:/(?P<option>.*))?/?'
        path = request.path
        match = re.search(pattern, path)

        app = match.group('app') if match else None
        nsid = match.group('nsid') if match else kwargs.get('nsid')
        option = match.group('option') if match else None

        if not nsid or nsid == 'default':
            if not (nsid := request.session.get('default_nsid')):  # Check session, otherwise get default nsid from DB
                ns = get_default_ns(request.user)
                if not ns:  # When it is the first admin account
                    return HttpResponse("Cannot continue. Please logout and re-login with a different account.")
                nsid = ns.nsid
                request.session['default_nsid'] = nsid

            valid_app = app in CLIENT_APPS
            if valid_app and option:
                return redirect(f'/{app}/{nsid}/{option}')  # Redirect to the URL with the correct nsid
            elif valid_app:
                return redirect(f'/{app}/{nsid}')
            else:
                return render(request, "404-app.html", status=404)

        ns = Namespace.objects.filter(nsid=nsid).first()
        if not ns:
            return render(request, "404-app.html", status=404)  # Render 404 if namespace is not found

        role = ns.get_role(request.user)

        if role is None:
            return render(request, "404-app.html", status=404)  # If the user has no role, render 404

        request.nsid = nsid  # Attach the namespace info to the request
        request.namespace = ns
        request.ns_role = role

        return view_func(request, *args, **kwargs)

    return _wrapped_view
