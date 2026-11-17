from django.urls import path

from . import admin_views

urlpatterns = [
    path('dashboard/mediciones/', admin_views.admin_mediciones_view, name='admin_mediciones'),
    path('dashboard/mediciones/<int:medicion_id>/eliminar/', admin_views.eliminar_medicion_view, name='eliminar_medicion'),
    path('dashboard/descargas/', admin_views.admin_descargas_view, name='admin_descargas'),
    path('dashboard/descargas/csv/', admin_views.exportar_mediciones_csv_view, name='exportar_mediciones_csv'),
    path('dashboard/descargas/excel/', admin_views.exportar_mediciones_excel_view, name='exportar_mediciones_excel'),
]