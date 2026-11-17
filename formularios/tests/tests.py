from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from formularios.models import ConfiguracionParametro, Medicion
from formularios.validaciones import (validar_conductividad, validar_ph, validar_tds,
                                      validar_temperatura, validar_ubicacion)
from formularios.views import calcular_alerta

CLAVE = 'Clave-Segura-123'


def crear_monitor(email='monitor@test.cl'):
    return User.objects.create_user(username=email, email=email, password=CLAVE, first_name='Monitor')


def datos_medicion(**cambios):
    datos = {'ph': '7.2', 'conductividad': '0.5', 'tds': '450', 'temperatura': '15',
             'ubicacion': 'Santiago', 'latitud': '', 'longitud': ''}
    datos.update(cambios)
    return datos


def crear_medicion(usuario, **cambios):
    datos = dict(ph=7.0, conductividad=0.5, tds=450.0, temperatura=15.0, ubicacion='Santiago',
                 alerta_general='Verde', usuario=usuario, bloque_horario='Mañana')
    datos.update(cambios)
    return Medicion.objects.create(**datos)


def mensajes(respuesta):
    return [str(m) for m in get_messages(respuesta.wsgi_request)]


@contextmanager
def a_las(hora, minuto=0):
    # fija la hora que ve la vista, la fecha sigue siendo la de hoy para que "ya registró hoy" funcione
    ahora = timezone.localtime().replace(hour=hora, minute=minuto, second=0, microsecond=0)
    with patch('formularios.views.timezone') as falso:
        falso.localtime.return_value = ahora
        falso.now.return_value = ahora
        yield


class ValidacionDeParametrosTests(TestCase):
    #CIA-37 y también para el CIA-45, pero server side: rangos físicos de los parámetros

    LIMITES = (
        (validar_ph, 0.01, 14.0), (validar_conductividad, 0.0, 200.0),
        (validar_tds, 0.0, 9990.0), (validar_temperatura, 0.0, 80.0),
    )

    def test_los_limites_exactos_se_aceptan(self):
        for funcion, minimo, maximo in self.LIMITES:
            with self.subTest(funcion=funcion.__name__):
                self.assertEqual(funcion(minimo), minimo)
                self.assertEqual(funcion(maximo), maximo)

    def test_valores_fuera_de_rango_se_rechazan(self):
        for funcion, minimo, maximo in self.LIMITES:
            for valor in (minimo - 0.01, maximo + 0.01):
                with self.subTest(funcion=funcion.__name__, valor=valor):
                    with self.assertRaises(ValueError):
                        funcion(valor)

    def test_valores_no_numericos_se_rechazan(self):
        for funcion, _, _ in self.LIMITES:
            for valor in ('abc', '', None, 'nan', 'inf'):
                with self.subTest(funcion=funcion.__name__, valor=valor):
                    with self.assertRaises(ValueError):
                        funcion(valor)

    def test_ubicacion_vacia_se_rechaza(self):
        for valor in ('', '   ', None):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    validar_ubicacion(valor)

    def test_los_rangos_editados_por_el_admin_se_respetan(self):
        ConfiguracionParametro.objects.create(
            nombre_parametro='ph', valor_min=0.01, valor_max=12.5, texto_informativo='x')
        self.assertEqual(validar_ph(12.5), 12.5)
        with self.assertRaises(ValueError):
            validar_ph(13.0)

    def test_sin_configuracion_se_usan_los_rangos_por_defecto(self):
        self.assertEqual(validar_ph(14.0), 14.0)


class RegistroDeMedicionTests(TestCase):
    #CIA-76 y CIA-80: bloques horarios, una medición por bloque y coordenadas

    def setUp(self):
        self.usuario = crear_monitor()
        self.client.force_login(self.usuario)

    def registrar(self, hora, minuto=0, **cambios):
        with a_las(hora, minuto):
            return self.client.post(reverse('medicion'), datos_medicion(**cambios))

    def test_bloque_segun_la_hora(self):
        casos = [(8, 0, 'Mañana'), (11, 59, 'Mañana'), (12, 0, 'Día'),
                 (15, 59, 'Día'), (16, 0, 'Noche'), (20, 0, 'Noche')]
        for hora, minuto, bloque in casos:
            with self.subTest(hora=f'{hora}:{minuto:02d}'):
                Medicion.objects.all().delete()
                self.registrar(hora, minuto)
                self.assertEqual(Medicion.objects.get().bloque_horario, bloque)

    def test_fuera_de_horario_no_guarda(self):
        for hora, minuto in ((7, 59), (20, 1), (23, 0)):
            with self.subTest(hora=f'{hora}:{minuto:02d}'):
                respuesta = self.registrar(hora, minuto)
                self.assertEqual(Medicion.objects.count(), 0)
                self.assertTrue(any('bloques habilitados' in m for m in mensajes(respuesta)))

    def test_segunda_medicion_del_mismo_bloque_actualiza_la_anterior(self):
        self.registrar(9, ph='7.0')
        self.registrar(10, ph='7.8')
        self.assertEqual(Medicion.objects.get().ph, 7.8)

    def test_bloques_distintos_guardan_mediciones_distintas(self):
        self.registrar(9)
        self.registrar(13)
        self.assertEqual(Medicion.objects.count(), 2)

    def test_cada_usuario_tiene_su_propia_medicion_por_bloque(self):
        otro = Client()
        otro.force_login(crear_monitor('otro@test.cl'))
        with a_las(9):
            self.client.post(reverse('medicion'), datos_medicion())
            otro.post(reverse('medicion'), datos_medicion())
        self.assertEqual(Medicion.objects.count(), 2)

    def test_guarda_las_coordenadas_y_acepta_su_ausencia(self):
        self.registrar(10, latitud='-33.45', longitud='-70.66')
        medicion = Medicion.objects.get()
        self.assertEqual((medicion.latitud, medicion.longitud), (-33.45, -70.66))
        Medicion.objects.all().delete()
        self.registrar(10)
        self.assertIsNone(Medicion.objects.get().latitud)

    def test_valor_fuera_de_rango_no_guarda_nada(self):
        respuesta = self.registrar(10, ph='15')
        self.assertEqual(Medicion.objects.count(), 0)
        self.assertEqual(respuesta.context['alertas'][0]['nivel'], 'Error')


class HistorialDeMedicionesTests(TestCase):
    #CIA-64 y CIA-48: consulta y filtros del historial del usuario

    def setUp(self):
        self.usuario = crear_monitor()
        self.client.force_login(self.usuario)

    def historial(self, **filtros):
        return self.client.get(reverse('historial_mediciones'), filtros)

    def test_visitante_es_enviado_al_login(self):
        respuesta = Client().get(reverse('historial_mediciones'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith(reverse('login')))

    def test_solo_muestra_las_mediciones_del_usuario(self):
        crear_medicion(self.usuario)
        crear_medicion(crear_monitor('otro@test.cl'))
        self.assertEqual(self.historial().context['total_registros'], 1)

    def test_filtra_por_alerta(self):
        crear_medicion(self.usuario, alerta_general='Verde')
        crear_medicion(self.usuario, alerta_general='Rojo')
        self.assertEqual(self.historial(alerta='Rojo').context['total_registros'], 1)

    def test_filtra_por_rango_de_un_parametro(self):
        for ph in (6.0, 7.0, 8.0):
            crear_medicion(self.usuario, ph=ph)
        respuesta = self.historial(parametro='ph', minimo='6.5', maximo='7.5')
        self.assertEqual(respuesta.context['total_registros'], 1)

    def test_filtra_por_fechas(self):
        for dias in (10, 5, 0):
            medicion = crear_medicion(self.usuario)
            Medicion.objects.filter(pk=medicion.pk).update(
                fecha_registro=timezone.now() - timedelta(days=dias))
        limite = (timezone.localdate() - timedelta(days=7)).isoformat()
        self.assertEqual(self.historial(desde=limite).context['total_registros'], 2)
        self.assertEqual(self.historial(hasta=limite).context['total_registros'], 1)

    def test_filtros_invalidos_muestran_un_error(self):
        casos = [
            ({'minimo': '1'}, 'Selecciona un parámetro para filtrar por valor.'),
            ({'parametro': 'ph', 'minimo': '9', 'maximo': '3'}, 'El valor mínimo no puede ser mayor que el máximo.'),
            ({'parametro': 'password'}, 'El parámetro seleccionado no es válido.'),
            ({'desde': '2026-12-31', 'hasta': '2026-01-01'}, 'La fecha inicial no puede ser posterior a la final.'),
            ({'desde': 'no-es-fecha'}, "La fecha 'desde' no es válida."),
        ]
        for filtros, mensaje in casos:
            with self.subTest(filtros=filtros):
                self.assertIn(mensaje, self.historial(**filtros).context['errores'])

    def test_paginacion_de_diez_en_diez(self):
        for _ in range(12):
            crear_medicion(self.usuario)
        self.assertEqual(self.historial().context['pagina'].paginator.num_pages, 2)
        self.assertEqual(len(self.historial(page=2).context['pagina']), 2)

    def test_filtra_por_bloque_horario(self):
        def a_la_hora(hora):
            medicion = crear_medicion(self.usuario)
            fecha = timezone.localtime().replace(hour=hora, minute=0, second=0, microsecond=0)
            Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=fecha)
            return medicion.pk

        manana, limite, dia, noche, _fuera = a_la_hora(9), a_la_hora(12), a_la_hora(13), a_la_hora(18), a_la_hora(7)
        esperado = {'Mañana': [manana], 'Día': [limite, dia], 'Noche': [noche]}  # las 12:00 ya son "Día"
        for bloque, pks in esperado.items():
            with self.subTest(bloque=bloque):
                pagina = self.historial(bloque_horario=bloque).context['pagina']
                self.assertCountEqual([m.pk for m in pagina], pks)
        self.assertEqual(self.historial().context['total_registros'], 5)

    def test_bloque_horario_invalido_muestra_un_error(self):
        errores = self.historial(bloque_horario='Madrugada').context['errores']
        self.assertIn('El bloque horario seleccionado no es válido.', errores)    


class CalculoDeAlertaTests(TestCase):
    #RF10: clasificación del estado del agua con los umbrales por defecto y un promedio de TDS de 500 ppm

    def test_verde_amarillo_y_rojo(self):
        casos = [
            ((7.2, 0.5, 450, 15), 'Verde'),
            ((6.3, 0.5, 450, 15), 'Amarillo'),  
            ((5.5, 0.5, 450, 15), 'Rojo'),
            ((7.2, 0.5, 600, 15), 'Amarillo'), 
            ((7.2, 0.5, 1100, 15), 'Rojo'),  
            ((7.2, 0.5, 40, 15), 'Rojo'),  
            ((7.2, 0.5, 450, 30), 'Amarillo'),  
            ((7.2, 0.5, 450, 40), 'Rojo'),
            ((7.2, 120, 450, 15), 'Amarillo'),  
            ((7.2, 160, 450, 15), 'Rojo'),
        ]
        for valores, esperado in casos:
            with self.subTest(valores=valores):
                self.assertEqual(calcular_alerta(*valores, promedio_tds=500), esperado)


class PromedioDeTdsTests(TestCase):
    #TDS comparado con el promedio de la comuna, o con el valor base si hay pocas muestras

    def setUp(self):
        self.client.force_login(crear_monitor())

    def registrar_tds(self, tds, comuna='Maipú'):
        with a_las(10):
            return self.client.post(reverse('medicion'),
                                    datos_medicion(tds=str(tds), ubicacion=comuna))

    def nivel_tds(self, respuesta):
        return next(a['nivel'] for a in respuesta.context['alertas'] if a['parametro'] == 'TDS')

    def test_con_pocas_muestras_se_compara_con_el_valor_base(self):
        # por defecto el valor base es 300 ppm y se piden 5 muestras
        self.assertEqual(self.nivel_tds(self.registrar_tds(200)), 'Bajo')
        self.assertEqual(self.nivel_tds(self.registrar_tds(400)), 'Medio')

    def test_con_suficientes_muestras_se_compara_con_el_promedio_de_la_comuna(self):
        for _ in range(5):
            crear_medicion(None, ubicacion='Maipú', tds=100.0)
        self.assertEqual(self.nivel_tds(self.registrar_tds(150)), 'Medio')  
        self.assertEqual(self.nivel_tds(self.registrar_tds(150, comuna='Ñuñoa')), 'Bajo')  

    def test_fuera_de_los_limites_absolutos_es_alto(self):
        for tds in (40, 1100):
            with self.subTest(tds=tds):
                self.assertEqual(self.nivel_tds(self.registrar_tds(tds)), 'Alto')

# 21 + 34 = 55