from django.shortcuts import render

from ..users.models import User
from core.utils import success_message, error_message

# @api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def user_list(request):
    users = User.objects.all()
    return render(request, 'users/user_list.html', {'users': users})
