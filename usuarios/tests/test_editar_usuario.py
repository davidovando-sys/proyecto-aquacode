from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import SolicitudRegistro


class EditarUsuarioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin-edicion', is_staff=True)
        self.usuario = User.objects.create_user('monitor@example.com', email='monitor@example.com', first_name='Monitor')
        self.solicitud = SolicitudRegistro.objects.create(
            nombre='Monitor', email=self.usuario.email, comuna='Santiago', aprobado=True,
        )
        self.client.force_login(self.admin)
        self.url = reverse('editar_usuario', args=[self.solicitud.pk])

    def test_abrir_formulario_con_datos_actuales(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['formulario'].initial['email'], self.usuario.email)
        self.assertTrue(response.context['formulario'].initial['activo'])

    def test_guardar_edicion(self):
        response = self.client.post(self.url, {
            'nombre': 'Monitor actualizado', 'email': self.usuario.email,
            'comuna': 'Maipú', 'rol': 'monitor', 'activo': 'on',
        })
        self.assertRedirects(response, reverse('dashboard_admin'), fetch_redirect_response=False)
        self.usuario.refresh_from_db()
        self.solicitud.refresh_from_db()
        self.assertEqual(self.usuario.first_name, 'Monitor actualizado')
        self.assertEqual(self.solicitud.comuna, 'Maipú')

    def test_datos_invalidos_no_guardan(self):
        response = self.client.post(self.url, {'email': 'incorrecto'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['formulario'].errors)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, 'monitor@example.com')
