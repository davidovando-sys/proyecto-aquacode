import os
from datetime import timedelta
from unittest import SkipTest, skipIf

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.urls import reverse
from django.utils import timezone

from formularios.models import Medicion
from formularios.tests import crear_medicion

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:  
    sync_playwright = None

ESPERA = 15_000  


def retroceder(medicion, dias):
    Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=timezone.now() - timedelta(days=dias))
    return medicion


@tag('navegador')
@skipIf(sync_playwright is None, 'Playwright no está instalado')
class InicioEnNavegadorTests(StaticLiveServerTestCase):
    #Lo que dibuja el navegador en inicio.html: gráficos (Chart.js) y mapa (Leaflet)

    @classmethod
    def setUpClass(cls):
        os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'  
        cls.playwright = sync_playwright().start()
        try:
            cls.navegador = cls.playwright.chromium.launch()
        except Exception as error:
            cls.playwright.stop()
            raise SkipTest(f'No se pudo abrir Chromium: {error}')
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.pagina = self.navegador.new_page(timezone_id='America/Santiago')

    def tearDown(self):
        self.pagina.close()

    def abrir(self):
        self.pagina.goto(self.live_server_url + reverse('home'))
        self.pagina.wait_for_function("window.Chart && Chart.getChart('chartPH')")

    def puntos_graficos(self):
        return self.pagina.evaluate(
            "['chartPH','chartCond','chartTDS','chartTemp'].map(id => Chart.getChart(id).data.labels.length)")

    def marcadores(self):
        return self.pagina.locator('#mapa-calor path.leaflet-interactive')

    def crear_datos_del_mapa(self):
        crear_medicion(None, ubicacion='Maipú', alerta_general='Rojo', latitud=-33.51, longitud=-70.76)
        crear_medicion(None, ubicacion='Ñuñoa', alerta_general='Verde', latitud=-33.46, longitud=-70.60)
        retroceder(crear_medicion(None, ubicacion='Santiago', alerta_general='Amarillo',
                                  latitud=-33.44, longitud=-70.65), dias=1)
        crear_medicion(None, ubicacion='Buin', alerta_general='Verde')  

    def test_los_graficos_dibujan_las_mediciones_del_periodo(self):
        crear_medicion(None, ubicacion='Maipú')
        crear_medicion(None, ubicacion='Ñuñoa')
        retroceder(crear_medicion(None, ubicacion='Maipú'), dias=5)
        retroceder(crear_medicion(None, ubicacion='Maipú'), dias=40)  
        self.abrir()
        self.assertEqual(self.puntos_graficos(), [3, 3, 3, 3])
        self.pagina.select_option('#chart-periodo', 'hoy')
        self.assertEqual(self.puntos_graficos(), [2, 2, 2, 2])

    def test_filtrar_los_graficos_por_comuna(self):
        crear_medicion(None, ubicacion='Maipú')
        retroceder(crear_medicion(None, ubicacion='Maipú'), dias=5)
        crear_medicion(None, ubicacion='Ñuñoa')
        self.abrir()
        self.pagina.select_option('#chart-comuna', 'maipu')
        self.assertEqual(self.puntos_graficos(), [2, 2, 2, 2])
        self.pagina.select_option('#chart-comuna', 'buin')
        self.assertEqual(self.puntos_graficos(), [0, 0, 0, 0])
        expect(self.pagina.locator('#charts-empty')).to_be_visible(timeout=ESPERA)

    def test_el_mapa_dibuja_un_marcador_de_color_por_medicion_de_hoy(self):
        self.crear_datos_del_mapa()
        self.abrir()
        expect(self.marcadores()).to_have_count(2, timeout=ESPERA)
        colores = self.pagina.eval_on_selector_all(
            '#mapa-calor path.leaflet-interactive', 'els => els.map(e => e.getAttribute("stroke"))')
        self.assertCountEqual(colores, ['#dc3545', '#198754'])  # rojo y verde

    def test_filtros_del_mapa(self):
        self.crear_datos_del_mapa()
        self.abrir()
        self.pagina.select_option('#periodo', '7')
        expect(self.marcadores()).to_have_count(3, timeout=ESPERA)
        self.pagina.select_option('#comuna', 'maipu')
        expect(self.marcadores()).to_have_count(1, timeout=ESPERA)
        expect(self.pagina.locator('.leaflet-popup-content')).to_contain_text('Maipú', timeout=ESPERA)

    def test_sin_mediciones_el_mapa_y_los_graficos_muestran_el_aviso(self):
        self.abrir()
        expect(self.pagina.locator('#mapa-vacio')).to_be_visible(timeout=ESPERA)
        expect(self.pagina.locator('#charts-empty')).to_be_visible(timeout=ESPERA)
        expect(self.marcadores()).to_have_count(0, timeout=ESPERA)