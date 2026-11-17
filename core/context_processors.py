from django.utils import timezone

from formularios.models import Medicion

from .bloques import bloque_actual


def recordatorio_bloque(request):
    """Avisa en todas las páginas si el usuario aún no registra su medición del bloque vigente.

    No aparece para administradores, fuera del horario de mediciones (08:00-20:00)
    ni si el usuario ya registró su medición de este bloque hoy.
    """
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated or usuario.is_staff:
        return {}

    ahora = timezone.localtime()
    bloque = bloque_actual(ahora)
    if bloque is None:
        return {}

    nombre, fin = bloque
    ya_registro = Medicion.objects.filter(
        usuario=usuario,
        bloque_horario=nombre,
        fecha_registro__date=ahora.date(),
    ).exists()
    if ya_registro:
        return {}

    return {'recordatorio_bloque': {'nombre': nombre, 'fin': fin.strftime('%H:%M')}}