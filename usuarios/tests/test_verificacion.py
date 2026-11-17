import re
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import SolicitudRegistro


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class VerificacionTests(TestCase):
    def registrar(self):
        response = self.client.post(reverse('solicitar_registro'), {
            'nombre': 'Persona Prueba', 'comuna': 'Santiago', 'email': 'prueba@example.com',
            'password': 'ClavePrueba-123!', 'password2': 'ClavePrueba-123!',
        })
        self.assertRedirects(response, reverse('verificar_correo'))
        return SolicitudRegistro.objects.get(email='prueba@example.com')

    def codigo(self):
        return re.search(r'Tu código es: ([0-9]{4})', mail.outbox[-1].body).group(1)

    def test_redireccion_confirmacion_y_aprobacion(self):
        solicitud = self.registrar()
        self.assertContains(self.client.get(reverse('verificar_correo')), 'Ingresa el número de 4 dígitos')
        admin = User.objects.create_user('admin', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('dashboard_admin')).context['total_pendientes'], 0)
        self.client.post(reverse('aprobar_solicitud', args=[solicitud.pk]))
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.aprobado)
        self.client.post(reverse('verificar_correo'), {'codigo': self.codigo()})
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.correo_verificado)
        self.assertEqual(solicitud.codigo_hash, '')
        self.assertFalse(User.objects.get(email=solicitud.email).is_active)
        self.assertEqual(self.client.get(reverse('dashboard_admin')).context['total_pendientes'], 1)
        self.client.post(reverse('aprobar_solicitud', args=[solicitud.pk]))
        self.assertTrue(User.objects.get(email=solicitud.email).is_active)

    def test_error_de_envio_permite_reintentar(self):
        with patch('usuarios.views.verificacion_views.send_mail', side_effect=SMTPException):
            solicitud = self.registrar()
        self.assertContains(self.client.get(reverse('verificar_correo')), 'Todavía no se ha enviado')
        self.client.post(reverse('verificar_correo'), {'accion': 'reenviar'})
        self.client.post(reverse('verificar_correo'), {'codigo': self.codigo()})
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.correo_verificado)

    def test_limite_vencimiento_y_reenvio(self):
        with patch('usuarios.views.verificacion_views.secrets.randbelow', return_value=7):
            solicitud = self.registrar()
        self.assertEqual(self.codigo(), '0007')
        for _ in range(5):
            self.client.post(reverse('verificar_correo'), {'codigo': '9999'})
        self.assertContains(self.client.post(reverse('verificar_correo'), {'codigo': '0007'}), 'Alcanzaste')
        self.client.post(reverse('verificar_correo'), {'accion': 'reenviar'})
        self.assertEqual(len(mail.outbox), 1)
        solicitud.codigo_enviado = timezone.now() - timedelta(minutes=11)
        solicitud.save()
        self.assertContains(self.client.post(reverse('verificar_correo'), {'codigo': '0007'}), 'venció')
        with patch('usuarios.views.verificacion_views.secrets.randbelow', return_value=1234):
            self.client.post(reverse('verificar_correo'), {'accion': 'reenviar'})
        self.client.post(reverse('verificar_correo'), {'codigo': '0007'})
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.correo_verificado)
        self.client.post(reverse('verificar_correo'), {'codigo': '1234'})
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.correo_verificado)

    def test_sin_sesion_no_verifica(self):
        solicitud = self.registrar()
        codigo = self.codigo()
        self.client.logout()
        self.assertRedirects(self.client.post(reverse('verificar_correo'), {'codigo': codigo}), reverse('solicitar_registro'))
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.correo_verificado)
