from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urljoin
from .models import RecordatorioMedicion
from .bloques import texto_bloques_disponibles

def enviar_correo_estado_solicitud(solicitud):
    # avisa al usuario si su solicitud fue aprobada o rechazada
    url_sitio = f"{getattr(settings, 'AQUACIVIS_SITE_URL', 'https://aquacivis.cl').rstrip('/')}/"

    if solicitud.rechazado:
        motivo = solicitud.get_motivo_rechazo_display() or "No se indicó un motivo."
        detalle = f"\nDetalle: {solicitud.detalle_rechazo}" if solicitud.detalle_rechazo else ""
        asunto = "Tu solicitud de cuenta en AquaCivis fue rechazada"
        mensaje = (
            f"Hola {solicitud.nombre},\n\n"
            "Tu solicitud de cuenta no fue aprobada.\n"
            f"Motivo: {motivo}{detalle}\n\n"
            "Podrás enviar una nueva solicitud pasados 7 días desde hoy.\n\n"
            "Equipo AquaCivis"
        )
        contexto = {
            'nombre': solicitud.nombre,
            'aprobada': False,
            'motivo': motivo,
            'detalle': solicitud.detalle_rechazo,
            'url_sitio': url_sitio,
        }
    elif solicitud.aprobado:
        asunto = "Tu cuenta en AquaCivis fue aprobada"
        mensaje = (
            f"Hola {solicitud.nombre},\n\n"
            "Tu solicitud de cuenta fue aprobada. Ya puedes iniciar sesión "
            "con tu correo y contraseña, y comenzar a ingresar mediciones.\n\n"
            "Equipo AquaCivis"
        )
        contexto = {
            'nombre': solicitud.nombre,
            'aprobada': True,
            'url_sitio': url_sitio,
        }
    else:
        return 
    
    html_mensaje = render_to_string('email/estado_solicitud.html', contexto)

    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [solicitud.email], html_message=html_mensaje),


def enviar_correo_recordatorio(usuario, dias_sin_medicion):
    # recuerda al usuario que lleva 1 día o 1 semana sin registrar mediciones
    nombre = usuario.first_name.strip() or usuario.username
    url_medicion = urljoin(
        f"{settings.AQUACIVIS_SITE_URL.rstrip('/')}/",
        reverse('medicion').lstrip('/'),
    )

    if dias_sin_medicion == RecordatorioMedicion.RECORDATORIO_7_DIAS:
        apertura = (
            'Hace más de una semana que no registras una medición en AquaCivis. '
            'Tu aporte es clave para que el monitoreo de la calidad del agua '
            'siga siendo útil para tu comunidad.'
        )
    else:
        apertura = (
            'Llevas más de un día sin registrar una medición en AquaCivis. '
            'Te invitamos a ingresar una nueva para mantener actualizado '
            'el monitoreo de la calidad del agua.'
        )

    bloques_texto = texto_bloques_disponibles()
    asunto = 'Recordatorio de medición - AquaCivis'
    mensaje = (
        f'Hola {nombre},\n\n'
        f'{apertura}\n\n'
        f'{texto_bloques_disponibles()}\n\n'
        f'Registrar medición: {url_medicion}\n\n'
        'Este recordatorio se envía automáticamente.\n'
        'Equipo AquaCivis'
    )

    html_mensaje = render_to_string('email/recordatorio_medicion.html', {
        'nombre': nombre,
        'apertura': apertura,
        'bloques': bloques_texto,
        'url_medicion': url_medicion,
    })

    return send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [usuario.email], html_message=html_mensaje)