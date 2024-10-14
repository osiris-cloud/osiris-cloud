from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from ..users.utils import get_default_ns
from ..k8s.models import Namespace


@login_required
def dashboard(request, nsid=None):
    if (nsid == 'default') or (not nsid):
        if not (nsid := request.session.get('default_nsid')):
            nsid = get_default_ns(request.user).nsid
            request.session['default_nsid'] = nsid
        return redirect(f'/dashboard/{nsid}')
    else:
        if not (ns := Namespace.objects.filter(nsid=nsid).first()):
            return render(request, "404_app.html", status=404)
        if ns.get_role(request.user) is None:
            return render(request, "404_app.html", status=404)
        context = {
            'segment': ['dashboard'],
        }
        return render(request, "apps/dashboard/app.html", context)
