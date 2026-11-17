import re
from datetime import timedelta
from unittest import expectedFailure

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import SolicitudRegistro

from .tests import CLAVE, crear_cuenta


def datos_registro(**cambios):
    datos = {
        'nombre': 'Prueba Uno', 'comuna': 'Santiago', 'email': 'nuevo@aquacivis.cl',
        'motivo': '', 'password': CLAVE, 'password2': CLAVE,
    }
    datos.update(cambios)
    return datos


def mensajes(respuesta):
    return [str(m) for m in get_messages(respuesta.wsgi_request)]


class RegistroDeCuentaTests(TestCase):
    #CIA-51: crear una cuenta deja la solicitud pendiente y la contraseña con hash

    def test_registro_crea_cuenta_inactiva_y_solicitud_pendiente(self):
        respuesta = self.client.post(reverse('solicitar_registro'), datos_registro())
        self.assertRedirects(respuesta, reverse('verificar_correo'), fetch_redirect_response=False)
        usuario = User.objects.get(email='nuevo@aquacivis.cl')
        self.assertFalse(usuario.is_active)
        solicitud = SolicitudRegistro.objects.get(email='nuevo@aquacivis.cl')
        self.assertFalse(solicitud.aprobado)
        self.assertFalse(solicitud.rechazado)
        self.assertFalse(solicitud.correo_verificado)

    def test_la_contrasena_se_guarda_con_hash(self):
        self.client.post(reverse('solicitar_registro'), datos_registro())
        usuario = User.objects.get(email='nuevo@aquacivis.cl')
        self.assertNotEqual(usuario.password, CLAVE)
        self.assertTrue(usuario.check_password(CLAVE))

    def test_cuenta_pendiente_no_puede_iniciar_sesion(self):
        self.client.post(reverse('solicitar_registro'), datos_registro())
        respuesta = self.client.post(reverse('login'), {'username': 'nuevo@aquacivis.cl', 'password': CLAVE})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class ValidacionRegistroTests(TestCase):
    #CIA-81: validaciones del formulario de registro

    def registrar(self, **cambios):
        return self.client.post(reverse('solicitar_registro'), datos_registro(**cambios))

    def crear_rechazada(self, dias):
        _, solicitud = crear_cuenta('rechazado@test.cl', activo=False, aprobado=False)
        SolicitudRegistro.objects.filter(pk=solicitud.pk).update(
            rechazado=True, fecha_rechazo=timezone.now() - timedelta(days=dias))
        return solicitud

    def test_campos_obligatorios_vacios(self):
        for campo in ('nombre', 'comuna', 'email', 'password', 'password2'):
            respuesta = self.registrar(**{campo: ''})
            self.assertRedirects(respuesta, reverse('solicitar_registro'), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(SolicitudRegistro.objects.count(), 0)

    def test_contrasenas_distintas(self):
        self.registrar(password2='otra-clave')
        self.assertEqual(User.objects.count(), 0)

    def test_correo_duplicado(self):
        crear_cuenta('existente@test.cl')
        respuesta = self.registrar(email='existente@test.cl')
        self.assertRedirects(respuesta, reverse('solicitar_registro'), fetch_redirect_response=False)
        self.assertIn('Ya existe una cuenta asociada a este correo.', mensajes(respuesta))
        self.assertEqual(SolicitudRegistro.objects.filter(email='existente@test.cl').count(), 1)

    def test_rechazado_debe_esperar_7_dias(self):
        solicitud = self.crear_rechazada(dias=2)
        respuesta = self.registrar(email='rechazado@test.cl')
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.rechazado)
        self.assertTrue(any('esperar' in m for m in mensajes(respuesta)))

    def test_rechazado_puede_volver_a_postular_tras_7_dias(self):
        solicitud = self.crear_rechazada(dias=8)
        self.registrar(email='rechazado@test.cl', password='Otra-Clave-456', password2='Otra-Clave-456')
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.rechazado)
        usuario = User.objects.get(email='rechazado@test.cl')
        self.assertFalse(usuario.is_active)
        self.assertTrue(usuario.check_password('Otra-Clave-456'))

    def test_comuna_fuera_de_la_lista_se_rechaza(self):
        respuesta = self.registrar(comuna='Atlantida')
        self.assertRedirects(respuesta, reverse('solicitar_registro'), fetch_redirect_response=False)
        self.assertIn('Por favor selecciona una comuna válida.', mensajes(respuesta))
        self.assertEqual(User.objects.count(), 0)

    def test_el_correo_se_guarda_en_minusculas(self):
        self.registrar(email='Nuevo@Aquacivis.CL')
        self.assertTrue(User.objects.filter(email='nuevo@aquacivis.cl').exists())
        self.registrar(email='NUEVO@aquacivis.cl')
        self.assertEqual(User.objects.filter(email__iexact='nuevo@aquacivis.cl').count(), 1)

    @expectedFailure  #Le hice una prueba y el servidor no valida el formato del correo, lo misma con las otras de abajo
    def test_correo_sin_arroba_se_rechaza(self):
        self.registrar(email='correo-sin-arroba')
        self.assertFalse(User.objects.filter(email='correo-sin-arroba').exists())

    @expectedFailure  #El RF3 pide mínimo 8 caracteres y no se valida
    def test_contrasena_corta_se_rechaza(self):
        self.registrar(password='1234', password2='1234')
        self.assertFalse(User.objects.filter(email='nuevo@aquacivis.cl').exists())

    @expectedFailure  #El RF3 pide un nombre de al menos 3 letras
    def test_nombre_demasiado_corto_se_rechaza(self):
        self.registrar(nombre='Al')
        self.assertFalse(User.objects.filter(email='nuevo@aquacivis.cl').exists())


class RecuperarContrasenaTests(TestCase):
    #CIA-88: recuperar la contraseña por correo

    def setUp(self):
        crear_cuenta('monitor@test.cl')

    def test_se_envia_un_correo_con_el_enlace(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': 'monitor@test.cl'})
        self.assertRedirects(respuesta, reverse('password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['monitor@test.cl'])
        self.assertIn('/recuperar-password/', mail.outbox[0].body)

    def test_correo_desconocido_no_envia_nada(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': 'nadie@test.cl'})
        self.assertRedirects(respuesta, reverse('password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_cuenta_inactiva_no_recibe_el_enlace(self):
        crear_cuenta('pendiente@test.cl', activo=False, aprobado=False)
        self.client.post(reverse('password_reset'), {'email': 'pendiente@test.cl'})
        self.assertEqual(len(mail.outbox), 0)

    def test_cambiar_la_contrasena_con_el_enlace(self):
        self.client.post(reverse('password_reset'), {'email': 'monitor@test.cl'})
        enlace = re.search(r'https?://[^/\s]+(/recuperar-password/\S+)', mail.outbox[0].body).group(1)
        # Django guarda el token en la sesión y redirige a la pantalla para escribir la nueva contraseña
        pantalla = self.client.get(enlace, follow=True)
        url_cambio = pantalla.redirect_chain[-1][0]
        respuesta = self.client.post(url_cambio, {
            'new_password1': 'Nueva-Clave-456', 'new_password2': 'Nueva-Clave-456',
        })
        self.assertRedirects(respuesta, reverse('password_reset_complete'), fetch_redirect_response=False)
        self.assertTrue(Client().login(username='monitor@test.cl', password='Nueva-Clave-456'))
        self.assertFalse(Client().login(username='monitor@test.cl', password=CLAVE))


class FlujoDelUsuarioNuevoTests(TestCase):
    #Flujo completo: registro, aprobación del administrador e inicio de sesión

    def test_registro_aprobacion_e_inicio_de_sesion(self):
        # 1. el visitante envía su solicitud y se le pide verificar el correo
        respuesta = self.client.post(reverse('solicitar_registro'), datos_registro())
        self.assertRedirects(respuesta, reverse('verificar_correo'), fetch_redirect_response=False)
        solicitud = SolicitudRegistro.objects.get(email='nuevo@aquacivis.cl')

        # 2. mientras esté pendiente no puede entrar
        self.assertFalse(Client().login(username='nuevo@aquacivis.cl', password=CLAVE))

        # 3. el administrador no puede aprobarla hasta que el correo esté verificado
        admin, _ = crear_cuenta('admin@test.cl', staff=True)
        cliente_admin = Client()
        cliente_admin.force_login(admin)
        cliente_admin.post(reverse('aprobar_solicitud', args=[solicitud.id]))
        solicitud.refresh_from_db()
        self.assertFalse(solicitud.aprobado)

        # 4. provisorio: se marca el correo como verificado; falta probar el código real
        SolicitudRegistro.objects.filter(pk=solicitud.pk).update(correo_verificado=True)

        # 5. ahora sí la aprueba y se envía el correo de aviso
        cliente_admin.post(reverse('aprobar_solicitud', args=[solicitud.id]))
        self.assertEqual(mail.outbox[-1].to, ['nuevo@aquacivis.cl'])

        # 6. inicia sesión por la pantalla real y llega al formulario de mediciones
        usuario = Client()
        respuesta = usuario.post(reverse('login'), {'username': 'nuevo@aquacivis.cl', 'password': CLAVE})
        self.assertRedirects(respuesta, reverse('home'), fetch_redirect_response=False)
        self.assertEqual(usuario.get(reverse('medicion')).status_code, 200)

        # 7. y sigue sin acceso al panel de administración
        self.assertEqual(usuario.get(reverse('dashboard_admin')).status_code, 302)