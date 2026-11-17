from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formularios.models import Medicion
from formularios.tests import CLAVE, crear_medicion


def retroceder(medicion, dias):
    # retrocede la fecha de registro
    Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=timezone.now() - timedelta(days=dias))
    return medicion


class PuntosDelMapaTests(TestCase):
    #Mapa y gráficos de inicio: datos que entrega el servidor según el rol

    def setUp(self):
        self.monitor = User.objects.create_user('privado@test.cl', 'privado@test.cl', CLAVE, first_name='Zacarias')
        self.admin = User.objects.create_user('admin@test.cl', 'admin@test.cl', CLAVE, is_staff=True)
        crear_medicion(self.monitor, ubicacion='Maipú', alerta_general='Rojo',
                       latitud=-33.456789, longitud=-70.123456)

    def puntos(self):
        return self.client.get(reverse('home')).context['puntos_mapa']

    def test_visitante_ve_coordenadas_redondeadas_y_sin_datos_personales(self):
        respuesta = self.client.get(reverse('home'))
        punto = respuesta.context['puntos_mapa'][0]
        self.assertEqual((punto['lat'], punto['lng']), (-33.457, -70.123))
        self.assertNotIn('registrado_por', punto)
        for texto in ('privado@test.cl', 'Zacarias', '-33.456789', '-70.123456'):
            with self.subTest(texto=texto):
                self.assertNotContains(respuesta, texto)

    def test_monitor_tampoco_ve_coordenadas_exactas(self):
        self.client.force_login(self.monitor)
        punto = self.puntos()[0]
        self.assertEqual(punto['lat'], -33.457)
        self.assertNotIn('registrado_por', punto)

    def test_admin_ve_coordenadas_exactas_y_quien_registro(self):
        self.client.force_login(self.admin)
        punto = self.puntos()[0]
        self.assertEqual((punto['lat'], punto['lng']), (-33.456789, -70.123456))
        self.assertEqual(punto['registrado_por'],
                         {'nombre': 'Zacarias', 'correo': 'privado@test.cl', 'comuna': ''})

    def test_medicion_anonima_se_muestra_al_admin_como_sin_usuario(self):
        crear_medicion(None, latitud=-33.5, longitud=-70.6)
        self.client.force_login(self.admin)
        self.assertIsNone(self.puntos()[0]['registrado_por'])

    def test_admin_en_vista_de_usuario_deja_de_ver_datos_exactos(self):
        self.client.force_login(self.admin)
        self.client.get(reverse('dashboard_admin'))
        punto = self.puntos()[0]
        self.assertEqual(punto['lat'], -33.457)
        self.assertNotIn('registrado_por', punto)
        self.client.get(reverse('desactivar_vista_usuario'))
        self.assertEqual(self.puntos()[0]['lat'], -33.456789)

    def test_solo_van_mediciones_de_los_ultimos_30_dias_y_el_mapa_exige_coordenadas(self):
        crear_medicion(None, ubicacion='Buin') 
        retroceder(crear_medicion(None, latitud=-33.4, longitud=-70.5), dias=40)  
        contexto = self.client.get(reverse('home')).context
        self.assertEqual(len(contexto['puntos_mapa']), 1)
        self.assertEqual(len(contexto['datos_graficos']), 2)

    def test_orden_del_mapa_y_de_los_graficos(self):
        retroceder(crear_medicion(None, ph=6.0, latitud=-33.4, longitud=-70.5), dias=3)
        crear_medicion(None, ph=8.0, latitud=-33.3, longitud=-70.4)
        contexto = self.client.get(reverse('home')).context
        phs_mapa = [p['ph'] for p in contexto['puntos_mapa']]
        phs_graficos = [d['ph'] for d in contexto['datos_graficos']]
        self.assertEqual(phs_mapa[0], 8.0)  
        self.assertEqual(phs_graficos[0], 6.0)  
        self.assertEqual(phs_graficos[-1], 8.0)