from datetime import time

from django.utils import timezone

# Mismos bloques que Medicion.BLOQUES_HORARIOS (formularios/models.py).
BLOQUES = [
    ('Mañana', time(8, 0), time(12, 0)),
    ('Día', time(12, 0), time(16, 0)),
    ('Noche', time(16, 0), time(20, 0)),
]


def bloque_actual(ahora=None):
    """Devuelve (nombre, hora_de_termino) del bloque vigente, o None fuera de 08:00-20:00."""
    hora = (ahora or timezone.localtime()).time()
    for nombre, inicio, fin in BLOQUES:
        if inicio <= hora < fin:
            return nombre, fin
    return None


def _linea(bloque):
    nombre, inicio, fin = bloque
    return f'  - {nombre} ({inicio:%H:%M}-{fin:%H:%M})'


def texto_bloques_disponibles(ahora=None):
    """Texto para el correo: qué bloques se pueden usar hoy, según la hora de envío."""
    ahora = ahora or timezone.localtime()
    hora = ahora.time()
    restantes = [b for b in BLOQUES if hora < b[2]]

    if not restantes:
        intro = 'Las mediciones de hoy ya cerraron. Mañana puedes registrarla en cualquiera de estos bloques:'
        lista = BLOQUES
    elif hora < BLOQUES[0][1]:
        intro = 'Hoy puedes registrarla desde las 08:00, en cualquiera de estos bloques:'
        lista = BLOQUES
    else:
        intro = 'Hoy aún puedes registrarla en:' if len(restantes) > 1 else 'Hoy aún puedes registrarla en el último bloque:'
        lista = restantes

    return intro + '\n' + '\n'.join(_linea(b) for b in lista)