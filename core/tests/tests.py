from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from formularios.models import Medicion

from .models import RecordatorioMedicion
from .recordatorios import enviar_recordatorios_pendientes


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='AquaCivis <no-reply@aquacivis.cl>',
    AQUACIVIS_SITE_URL='https://aquacivis.test',
)
class RecordatoriosMedicionTests(TestCase):
    def setUp(self):
        self.ahora = timezone.now()
        self.usuario = User.objects.create_user(
            username='monitor@example.com',
            email='monitor@example.com',
            password='ClaveSegura123*',
            first_name='Monitor',
        )

    def _crear_medicion(self, fecha):
        medicion = Medicion.objects.create(
            ph=7,
            conductividad=10,
            tds=100,
            temperatura=20,
            ubicacion='Santiago',
            usuario=self.usuario,
        )
        Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=fecha)
        medicion.refresh_from_db()
        return medicion

    def test_envia_recordatorio_al_cumplir_un_dia(self):
        medicion = self._crear_medicion(self.ahora - timedelta(days=1, minutes=1))

        resultado = enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(resultado['enviados'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('un día', mail.outbox[0].body)
        self.assertTrue(
            RecordatorioMedicion.objects.filter(
                usuario=self.usuario,
                dias_sin_medicion=1,
                fecha_referencia=medicion.fecha_registro,
            ).exists(),
        )

    def test_no_repite_el_mismo_recordatorio(self):
        self._crear_medicion(self.ahora - timedelta(days=2))

        enviar_recordatorios_pendientes(ahora=self.ahora)
        segundo_resultado = enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(segundo_resultado['enviados'], 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_usuario_sin_mediciones_usa_la_fecha_de_creacion(self):
        User.objects.filter(pk=self.usuario.pk).update(
            date_joined=self.ahora - timedelta(days=1, minutes=1),
        )

        enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('un día', mail.outbox[0].body)

    def test_envia_recordatorio_de_una_semana_una_sola_vez(self):
        medicion = self._crear_medicion(self.ahora - timedelta(days=7, minutes=1))
        RecordatorioMedicion.objects.create(
            usuario=self.usuario,
            dias_sin_medicion=1,
            fecha_referencia=medicion.fecha_registro,
        )

        enviar_recordatorios_pendientes(ahora=self.ahora)
        enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('una semana', mail.outbox[0].body)
        self.assertEqual(
            RecordatorioMedicion.objects.filter(
                usuario=self.usuario,
                dias_sin_medicion=7,
            ).count(),
            1,
        )

    def test_a_los_siete_dias_no_envia_dos_correos_juntos(self):
        self._crear_medicion(self.ahora - timedelta(days=8))

        enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('una semana', mail.outbox[0].body)

    def test_nueva_medicion_inicia_un_nuevo_ciclo(self):
        medicion_anterior = self._crear_medicion(self.ahora - timedelta(days=10))
        RecordatorioMedicion.objects.create(
            usuario=self.usuario,
            dias_sin_medicion=7,
            fecha_referencia=medicion_anterior.fecha_registro,
        )
        medicion_nueva = self._crear_medicion(self.ahora - timedelta(days=1, minutes=1))

        enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            RecordatorioMedicion.objects.filter(
                usuario=self.usuario,
                dias_sin_medicion=1,
                fecha_referencia=medicion_nueva.fecha_registro,
            ).exists(),
        )

    def test_omite_usuario_inactivo_personal_y_sin_correo(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])
        User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='ClaveSegura123*',
            is_staff=True,
            date_joined=self.ahora - timedelta(days=2),
        )
        User.objects.create_user(
            username='sin-correo',
            email='',
            password='ClaveSegura123*',
            date_joined=self.ahora - timedelta(days=2),
        )

        resultado = enviar_recordatorios_pendientes(ahora=self.ahora)

        self.assertEqual(resultado['usuarios_revisados'], 0)
        self.assertEqual(len(mail.outbox), 0)
