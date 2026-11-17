from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from formularios.models import Medicion


class ResultadoMedicionTests(TestCase):
    def test_resultado_muestra_estado_guardado_y_detalles(self):
        self.client.force_login(User.objects.create_user('monitor-resultado'))
        hora = datetime(2026, 10, 28, 10, tzinfo=ZoneInfo('America/Santiago'))
        with patch('formularios.views.timezone.localtime', return_value=hora):
            response = self.client.post(reverse('medicion'), {
                'ubicacion': 'La Florida', 'ph': '7', 'conductividad': '2',
                'tds': '20', 'temperatura': '20',
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Medicion.objects.get().alerta_general, 'Rojo')
        self.assertEqual(response.context['estado_general']['nivel'], 'Alto')
        self.assertContains(response, 'Estado del agua')
        self.assertContains(response, 'Ver más información', count=4)
        self.assertContains(response, '<details class="parameter-info">', count=4)
