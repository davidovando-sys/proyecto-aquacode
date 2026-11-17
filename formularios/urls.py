from django.urls import path
from . import views

urlpatterns = [
    path('medicion/', views.nueva_medicion_view, name='medicion'),
    path('historial/', views.historial_mediciones, name='historial_mediciones'),


]