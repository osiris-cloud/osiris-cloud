from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.vm, name='vm'),
    path('create', views.vm_create, name='vm_create'),
    path('edit', views.vm_edit, name='vm_edit'),
    path('console', views.vm_vnc, name='vm_vnc_404'),
    re_path(r'^console/(?P<vmid>[^/]+)/(?P<rest>.*)$', views.vm_vnc, name='vm_vnc'),
]

# path('terminal', views.vm_terminal, name='vm_terminal')
