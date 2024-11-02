from django.shortcuts import render
from django.http import JsonResponse
from uuid import UUID


def vm(request):
    context = {
        'segment': ['vm', 'list'],
    }
    return render(request, "apps/vm.html", context)


def vm_create(request):
    context = {
        'segment': ['vm', 'create'],
    }
    return render(request, "apps/vm.html", context)


def vm_edit(request):
    context = {
        'segment': ['vm', 'edit'],
    }
    return render(request, "apps/vm.html", context)


def vm_vnc(request, vmid=None, rest=None):
    if vmid is None:
        return render(request, "404.html")
    if rest:
        return JsonResponse({'error': 'Invalid URL'})
    vmid = vmid.strip()
    try:
        UUID(vmid)
    except ValueError:
        return JsonResponse({'error': 'Invalid VMID'})
    return render(request, "components/vm/console/vnc.html")

# def vm_terminal(request):
#     return render(request, "console/terminal.html")
