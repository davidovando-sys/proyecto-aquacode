from django.urls import path

from .views import *

urlpatterns = [
    path('graficos/', graficos_view, name='graficos'),
]