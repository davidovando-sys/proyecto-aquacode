from django.contrib import admin
from .models import (
    ConfiguracionAlerta,
    ContenidoWeb,
    RecordatorioMedicion,
    SolicitudRegistro,
)

@admin.register(SolicitudRegistro)
class SolicitudRegistroAdmin(admin.ModelAdmin):
    # Columnas que se verán en la tabla
    list_display = ('nombre', 'comuna', 'email', 'aprobado', 'fecha_creacion')
    
    # Filtros laterales rápidos
    list_filter = ('aprobado', 'comuna', 'fecha_creacion')
    
    # Barra de búsqueda
    search_fields = ('nombre', 'email', 'comuna')
    
    # Permite cambiar el estado de "aprobado" directamente desde la lista general
    readonly_fields = ('aprobado', 'correo_verificado', 'codigo_enviado', 'codigo_intentos')
    exclude = ('codigo_hash',)


admin.site.register(ConfiguracionAlerta)
admin.site.register(ContenidoWeb)


@admin.register(RecordatorioMedicion)
class RecordatorioMedicionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'dias_sin_medicion', 'fecha_referencia', 'fecha_envio')
    list_filter = ('dias_sin_medicion', 'fecha_envio')
    search_fields = ('usuario__email', 'usuario__username')
