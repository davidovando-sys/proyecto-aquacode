from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('formularios/', include('formularios.urls')),
    path('', include('core.urls')),
    path('', include('usuarios.urls')),
    path('', include('graficos.urls')),
    path('', include('formularios.admin_urls')),
]