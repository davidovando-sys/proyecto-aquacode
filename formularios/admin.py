from django.contrib import admin
from .models import ConfiguracionParametro

admin.site.register(ConfiguracionParametro)
from .models import Medicion

@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    # Columnas visibles para el Admin, incluyendo QUIÉN lo registró
    list_display = ('ubicacion', 'alerta_general', 'ph', 'tds', 'usuario', 'fecha_registro')
    
    # Filtros laterales rápidos
    list_filter = ('alerta_general', 'ubicacion', 'fecha_registro')
    
    # Barra de búsqueda
    search_fields = ('ubicacion', 'usuario__username')
