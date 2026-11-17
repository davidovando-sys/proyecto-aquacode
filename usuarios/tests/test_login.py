from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import ControlAcceso, IntentoInicioSesion
from .tests import CLAVE, crear_cuenta


def mensajes(respuesta):
    return [str(m) for m in get_messages(respuesta.wsgi_request)]


class BloqueoPorIntentosFallidosTests(TestCase):
    #Protección contra fuerza bruta en el inicio de sesión (RNF3)

    def setUp(self):
        self.usuario, _ = crear_cuenta('monitor@test.cl')

    def intentar(self, contrasena='clave-equivocada', usuario='monitor@test.cl'):
        return self.client.post(reverse('login'), {'username': usuario, 'password': contrasena})

    def test_avisa_cuantos_intentos_quedan(self):
        respuesta = self.intentar()
        self.assertTrue(any('Te quedan 4 intento(s)' in m for m in mensajes(respuesta)))

    def test_el_quinto_intento_fallido_bloquea_incluso_con_la_clave_correcta(self):
        for _ in range(5):
            self.intentar()
        respuesta = self.intentar(contrasena=CLAVE)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(any('bloquead' in m.lower() for m in mensajes(respuesta)))
        self.assertGreater(ControlAcceso.objects.get(username='monitor@test.cl').bloqueado_hasta, timezone.now())

    def test_un_inicio_de_sesion_correcto_reinicia_el_contador(self):
        for _ in range(2):
            self.intentar()
        self.intentar(contrasena=CLAVE)
        self.assertEqual(ControlAcceso.objects.get(username='monitor@test.cl').intentos_fallidos, 0)
        self.assertIn('_auth_user_id', self.client.session)

    def test_el_bloqueo_expira(self):
        for _ in range(5):
            self.intentar()
        ControlAcceso.objects.filter(username='monitor@test.cl').update(
            bloqueado_hasta=timezone.now() - timedelta(minutes=1))
        self.intentar(contrasena=CLAVE)
        self.assertIn('_auth_user_id', self.client.session)

    def test_no_se_evade_el_bloqueo_cambiando_mayusculas(self):
        for variante in ('MONITOR@test.cl', 'Monitor@test.cl', 'monitor@TEST.cl', 'MONITOR@TEST.CL', 'monitor@test.cl'):
            self.intentar(usuario=variante)
        self.intentar(contrasena=CLAVE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_los_intentos_se_registran_sin_guardar_la_contrasena(self):
        self.intentar(contrasena='clave-secreta-equivocada')
        intento = IntentoInicioSesion.objects.get()
        self.assertEqual(intento.usuario, self.usuario)
        self.assertEqual(intento.identificador, 'monitor@test.cl')
        self.assertEqual(intento.direccion_ip, '127.0.0.1')
        self.assertNotIn('clave-secreta-equivocada', str(intento.__dict__))

    def test_un_usuario_inexistente_tambien_cuenta_y_se_registra(self):
        self.intentar(usuario='nadie@test.cl')
        self.assertIsNone(IntentoInicioSesion.objects.get().usuario)
        self.assertEqual(ControlAcceso.objects.get(username='nadie@test.cl').intentos_fallidos, 1)