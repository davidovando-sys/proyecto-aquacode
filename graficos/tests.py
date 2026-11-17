from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from formularios.models import Medicion
from formularios.tests import CLAVE, crear_medicion


def con_fecha(medicion, dias):

    Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=timezone.now() - timedelta(days=dias))
    return medicion


class GraficosTests(TestCase):
    #Gráficos e historial público: datos que reciben los gráficos y la tabla

    def graficos(self, **filtros):
        return self.client.get(reverse('graficos'), filtros)

    def test_es_publico_y_usa_la_plantilla_del_historial(self):
        respuesta = self.graficos()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'historial.html')
        self.assertEqual(respuesta.context['datos_graficos'], [])

    def test_periodo_por_defecto_es_30_dias(self):
        con_fecha(crear_medicion(None), dias=5)
        con_fecha(crear_medicion(None), dias=40)
        respuesta = self.graficos()
        self.assertEqual(respuesta.context['periodo_seleccionado'], '30')
        self.assertEqual(len(respuesta.context['datos_graficos']), 1)

    def test_periodos_hoy_7_y_30_dias(self):
        for dias in (0, 1, 5, 10):
            con_fecha(crear_medicion(None), dias=dias)
        for periodo, esperado in {'hoy': 1, '7': 3, '30': 4}.items():
            with self.subTest(periodo=periodo):
                respuesta = self.graficos(periodo=periodo)
                self.assertEqual(len(respuesta.context['datos_graficos']), esperado)

    def test_periodo_invalido_vuelve_a_30_dias(self):
        self.assertEqual(self.graficos(periodo='999').context['periodo_seleccionado'], '30')

    def test_filtra_por_comuna_e_ignora_las_invalidas(self):
        crear_medicion(None, ubicacion='Maipú')
        crear_medicion(None, ubicacion='Ñuñoa')
        self.assertEqual(self.graficos(comuna='Maipú').context['total_mediciones'], 1)
        respuesta = self.graficos(comuna='Atlantida')
        self.assertEqual(respuesta.context['comuna_seleccionada'], '')
        self.assertEqual(respuesta.context['total_mediciones'], 2)

    def test_el_filtro_de_alerta_afecta_la_tabla_pero_no_los_graficos(self):
        crear_medicion(None, alerta_general='Verde')
        crear_medicion(None, alerta_general='Rojo')
        contexto = self.graficos(alerta='Rojo').context
        self.assertEqual(contexto['total_mediciones'], 1)
        self.assertEqual(len(contexto['datos_graficos']), 2)

    def test_fechas_de_la_tabla_y_fechas_invalidas(self):
        con_fecha(crear_medicion(None), dias=10)
        crear_medicion(None)
        limite = (timezone.localdate() - timedelta(days=5)).isoformat()
        self.assertEqual(self.graficos(fecha_desde=limite).context['total_mediciones'], 1)
        self.assertEqual(self.graficos(fecha_hasta=limite).context['total_mediciones'], 1)
        invalida = self.graficos(fecha_desde='no-es-fecha').context
        self.assertEqual(invalida['fecha_desde'], '')
        self.assertEqual(invalida['total_mediciones'], 2)

    def test_los_datos_de_los_graficos_van_en_orden_cronologico(self):
        con_fecha(crear_medicion(None, ph=6.0), dias=3)
        crear_medicion(None, ph=7.0)
        datos = self.graficos().context['datos_graficos']
        self.assertEqual([d['ph'] for d in datos], [6.0, 7.0])
        self.assertEqual(set(datos[0]), {'etiqueta', 'ph', 'conductividad', 'tds', 'temperatura'})

    def test_la_tabla_pagina_de_a_10_pero_los_graficos_traen_todo(self):
        for _ in range(12):
            crear_medicion(None)
        contexto = self.graficos().context
        self.assertEqual(len(contexto['mediciones']), 10)
        self.assertEqual(contexto['pagina_obj'].paginator.num_pages, 2)
        self.assertEqual(len(contexto['datos_graficos']), 12)
        self.assertEqual(len(self.graficos(page=2).context['mediciones']), 2)

    def test_la_pagina_publica_no_expone_datos_personales(self):
        usuario = User.objects.create_user('privado@test.cl', 'privado@test.cl', CLAVE, first_name='Zacarias')
        crear_medicion(usuario, latitud=-33.456789, longitud=-70.123456)
        respuesta = self.graficos()
        # con LANGUAGE_CODE es-cl los decimales pueden salir con coma, por eso se prueban ambas formas
        for texto in ('privado@test.cl', 'Zacarias', '-33.4567', '-33,4567', '-70.1234', '-70,1234'):
            with self.subTest(texto=texto):
                self.assertNotContains(respuesta, texto)