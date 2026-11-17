import importlib
import json
from types import SimpleNamespace
from pathlib import Path
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from core.models import Comuna, SolicitudRegistro
from core.comunas import exigir_comuna
from formularios.models import Medicion


class ComunasTests(TestCase):
    def setUp(self):
        self.florida = Comuna.objects.get(pk='13110')
        self.temuco = Comuna.objects.get(nombre='Temuco')
        self.admin = User.objects.create_user('admin', is_staff=True)

    def medicion(self, **kwargs):
        return Medicion.objects.create(ph=7, conductividad=.5, tds=300, temperatura=20, **kwargs)

    def test_catalogo_y_geometrias(self):
        self.assertEqual(Comuna.objects.count(), 346)
        self.assertEqual(Comuna.objects.values('codigo_region').distinct().order_by().count(), 16)
        root = Path(__file__).resolve().parent.parent
        self.assertEqual(
            json.loads((root / 'static/data/catalogo-comunas.json').read_text(encoding='utf-8')),
            json.loads((root / 'core/data/comunas.json').read_text(encoding='utf-8')),
        )
        datos = json.loads((root / 'static/data/comunas.geojson').read_text(encoding='utf-8'))
        codigos = {f['properties']['codigo'] for f in datos['features']}
        self.assertEqual(set(Comuna.objects.values_list('codigo', flat=True)) - codigos, {'12202'})
        for region in Comuna.objects.values_list('codigo_region', flat=True).distinct().order_by():
            regional = json.loads((root / f'static/data/comunas-{region}.geojson').read_text(encoding='utf-8'))
            self.assertTrue(all(Comuna.objects.get(pk=f['properties']['codigo']).codigo_region == region for f in regional['features']))

    def test_busqueda_minimo_dos_letras_tildes_y_region(self):
        url = reverse('buscar_comunas')
        self.assertEqual(self.client.get(url, {'q': 'n'}).json()['results'], [])
        resultado = self.client.get(url, {'q': 'NUNOA'}).json()['results']
        self.assertEqual(resultado[0]['codigo'], '13120')
        self.assertIn('Metropolitana', resultado[0]['region'])
        self.assertEqual(self.client.get(url, {'q': 'inexistente'}).json()['results'], [])
        self.assertEqual(exigir_comuna('maipu').nombre, 'Maipú')
        with self.assertRaises(ValueError):
            exigir_comuna('Comuna inventada')

    def test_panel_filtra_usuarios_sin_mediciones_y_no_reubica_historial(self):
        usuario = User.objects.create_user('monitor', email='monitor@example.com')
        solicitud = SolicitudRegistro.objects.create(nombre='Monitor sin registros', email=usuario.email,
            comuna=self.florida.nombre, comuna_catalogo=self.florida, aprobado=True)
        self.medicion(ubicacion=self.florida.nombre, comuna=self.florida)
        self.medicion(ubicacion=self.temuco.nombre, comuna=self.temuco)
        url = reverse('admin_mediciones')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        response = self.client.get(url, {'comuna': self.florida.pk})
        self.assertEqual(len(response.context['mediciones']), 1)
        self.assertEqual(len(response.context['usuarios_comuna']), 1)
        self.assertContains(response, 'monitor@example.com')
        solicitud.comuna_catalogo = self.temuco
        solicitud.comuna = self.temuco.nombre
        solicitud.save()
        response = self.client.get(url, {'comuna': self.florida.pk})
        self.assertEqual(len(response.context['mediciones']), 1)
        self.assertEqual(len(response.context['usuarios_comuna']), 0)
        response = self.client.get(url, {'comuna': '12202'})
        self.assertEqual(len(response.context['mediciones']), 0)
        self.assertContains(response, 'Antártica')

    def test_migracion_conserva_textos_y_ubicaciones_desconocidas(self):
        conocida = self.medicion(ubicacion=' Nunoa ')
        desconocida = self.medicion(ubicacion='Zona antigua')
        migracion = importlib.import_module('core.migrations.0012_cargar_comunas')
        migracion.cargar(apps, SimpleNamespace(connection=connection))
        conocida.refresh_from_db(); desconocida.refresh_from_db()
        self.assertEqual(conocida.comuna_id, '13120')
        self.assertEqual(conocida.ubicacion, ' Nunoa ')
        self.assertIsNone(desconocida.comuna_id)

    def test_registro_rechaza_comuna_inventada(self):
        response = self.client.post(reverse('solicitar_registro'), {
            'nombre': 'Prueba', 'email': 'nuevo@example.com', 'comuna': 'Inventada',
            'password': 'Ejemplo123!', 'password2': 'Ejemplo123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(email='nuevo@example.com').exists())

    def test_diez_mediciones_y_historial_conservan_filtro(self):
        for _ in range(12):
            self.medicion(ubicacion=self.florida.nombre, comuna=self.florida)
        self.medicion(ubicacion=self.temuco.nombre, comuna=self.temuco)
        self.client.force_login(self.admin)
        url = reverse('admin_mediciones')
        response = self.client.get(url, {'comuna': self.florida.pk})
        self.assertEqual(len(response.context['mediciones']), 12)
        self.assertEqual(response.context['total_mediciones'], 12)
        self.assertContains(response, 'Ver más mediciones')
        self.assertContains(response, 'data-fila-extra hidden', count=2)
        self.assertContains(response, 'aria-controls="filas-mediciones"')
        self.assertNotContains(response, 'historial=completo')
        response = self.client.get(url, {'comuna': self.temuco.pk})
        self.assertNotContains(response, 'Ver más mediciones')

    def test_usuarios_muestra_diez_y_oculta_el_resto(self):
        for i in range(12):
            SolicitudRegistro.objects.create(nombre=f'Monitor {i}', email=f'm{i}@example.com',
                comuna=self.florida.nombre, comuna_catalogo=self.florida, aprobado=True)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_mediciones'), {'comuna': self.florida.pk})
        self.assertEqual(len(response.context['usuarios_comuna']), 12)
        self.assertContains(response, 'data-fila-extra hidden', count=2)
        self.assertContains(response, 'Ver más usuarios')
        self.assertContains(response, 'aria-controls="filas-usuarios"')

    def test_creacion_administrador_con_comuna(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('crear_admin'))
        self.assertContains(response, 'data-comuna-busqueda')
        datos = {'nombre': 'Nueva cuenta', 'email': 'adminnuevo@example.com',
                 'password': 'UnaClaveSegura482!', 'password2': 'UnaClaveSegura482!',
                 'comuna': 'Inventada'}
        self.client.post(reverse('crear_admin'), datos)
        self.assertFalse(User.objects.filter(email=datos['email']).exists())
        datos['comuna'] = self.temuco.nombre
        response = self.client.post(reverse('crear_admin'), datos)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SolicitudRegistro.objects.get(email=datos['email']).comuna_catalogo_id, self.temuco.pk)
        self.assertContains(self.client.get(reverse('solicitar_registro')), 'data-comuna-busqueda')
