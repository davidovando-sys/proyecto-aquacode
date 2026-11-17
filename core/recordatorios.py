import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import DateTimeField, OuterRef, Subquery
from django.utils import timezone

from formularios.models import Medicion

from .correos import enviar_correo_recordatorio
from .models import RecordatorioMedicion


logger = logging.getLogger(__name__)


def _usuarios_con_ultima_medicion():
    ultima_medicion = (
        Medicion.objects.filter(usuario=OuterRef('pk'))
        .order_by('-fecha_registro', '-pk')
        .values('fecha_registro')[:1]
    )
    return (
        User.objects.filter(is_active=True, is_staff=False)
        .exclude(email='')
        .annotate(
            fecha_ultima_medicion=Subquery(
                ultima_medicion,
                output_field=DateTimeField(),
            ),
        )
    )


def _nivel_correspondiente(fecha_referencia, ahora):
    tiempo_sin_medicion = ahora - fecha_referencia
    if tiempo_sin_medicion >= timedelta(days=7):
        return RecordatorioMedicion.RECORDATORIO_7_DIAS
    if tiempo_sin_medicion >= timedelta(days=1):
        return RecordatorioMedicion.RECORDATORIO_1_DIA
    return None


def enviar_recordatorios_pendientes(ahora=None):
    """Envía como máximo un recordatorio pendiente por usuario y ciclo."""
    ahora = ahora or timezone.now()
    resultado = {
        'usuarios_revisados': 0,
        'enviados': 0,
        'omitidos': 0,
        'errores': 0,
    }

    for usuario in _usuarios_con_ultima_medicion().iterator():
        resultado['usuarios_revisados'] += 1
        fecha_referencia = usuario.fecha_ultima_medicion or usuario.date_joined
        nivel = _nivel_correspondiente(fecha_referencia, ahora)
        if nivel is None:
            resultado['omitidos'] += 1
            continue

        recordatorio, creado = RecordatorioMedicion.objects.get_or_create(
            usuario=usuario,
            dias_sin_medicion=nivel,
            fecha_referencia=fecha_referencia,
        )
        if not creado:
            resultado['omitidos'] += 1
            continue

        try:
            cantidad = enviar_correo_recordatorio(usuario, nivel)
        except Exception:
            recordatorio.delete()
            resultado['errores'] += 1
            logger.exception(
                'No se pudo enviar el recordatorio de medición al usuario %s.',
                usuario.pk,
            )
            continue

        if cantidad != 1:
            recordatorio.delete()
            resultado['errores'] += 1
            continue

        resultado['enviados'] += 1

    return resultado
