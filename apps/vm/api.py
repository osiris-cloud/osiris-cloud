import logging

from django.forms import model_to_dict
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.utils import success_message, error_message
from json import loads as json_loads

from .utils import validate_vm_spec, sanitize_vm_name, gen_mac_address
from .values import VM_TYPES
from ..k8s.utils import create_vm

from .models import VM


@api_view(['GET'])
def vnc(request, vmid=None):
    return Response(error_message('VNC not supported over http', {
        'detail': 'Protocol not supported' + (', <vmid> is required' if vmid is None else '')
    }))


@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def virtual_machines(request, vmid=None):
    """
    API endpoint for virtual machines
    """
    if vmid is None and request.method == 'GET':  # Get all virtual machines
        vm = request.user.vms.all()
        vm_dict = [model_to_dict(v) for v in vm]
        return Response(success_message('Get virtual machines', {'vm': vm_dict}))

    match request.method:
        case 'GET':
            try:
                vm = request.user.vms.filter(vmid=vmid).first()

                #vm_dict['created_at'] = timezone.localtime(vm_dict['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                #vm_dict['updated_at'] = timezone.localtime(vm_dict['updated_at']).strftime('%Y-%m-%d %H:%M:%S')

                return Response({
                    'status': 'success',
                    'vm': vm.to_dict() if vm else None,
                })
            except Exception as e:
                logging.exception(e)
                return Response({
                    'status': 'error',
                    'message': 'Invalid VMID',
                })

        case 'POST':
            vm_spec = json_loads(request.data.get('vm_spec')) if request.data.get('vm_spec') else None
            valid, resp = validate_vm_spec(vm_spec)

            if not valid:
                return Response(resp)

            vm_spec['k8sName'] = sanitize_vm_name(vm_spec['name'])
            vm_spec['ram'] = VM_TYPES[vm_spec['size']]['ram']
            vm_spec['cpu'] = VM_TYPES[vm_spec['size']]['cpu']
            vm_spec['mac'] = gen_mac_address()
            vm_spec['pvc_name'] = f"{vm_spec['k8sName']}-pvc"
            vm_spec['cloudinit_secret'] = f"{vm_spec['k8sName']}-cloud-init"

            create_vm(vm_spec, request.user)

            return Response({
                'status': 'success',
                'message': 'VM created',
            })
