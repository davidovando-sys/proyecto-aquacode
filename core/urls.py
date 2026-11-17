from django.urls import path
from .views import *
from .comunas_views import buscar_comunas

urlpatterns = [
    path('comunas/buscar/', buscar_comunas, name='buscar_comunas'),
    path('', home_view, name='home'),
    path('sobre-nosotros/', sobre_nosotros_view, name='sobre_nosotros'),
    path('dashboard/umbrales/', admin_umbrales_view, name='admin_umbrales'),
    path('dashboard/contenido/', admin_contenido_view, name='admin_contenido'),
    path('dashboard/vista-usuario/activar/', activar_vista_usuario, name='activar_vista_usuario'),
    path('dashboard/vista-usuario/desactivar/', desactivar_vista_usuario, name='desactivar_vista_usuario'),
]
