import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.template.loader import render_to_string

from core.models import SolicitudRegistro


def enviar_codigo(solicitud):
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        raise SMTPException('El envío real de correo no está configurado')
    codigo = f'{secrets.randbelow(10000):04d}'
    asunto = 'Tu código de verificación - AquaCivis'
    mensaje_texto = (
        f'Tu código es: {codigo}\n\nIngresa estos 4 números en AquaCivis para '
        'verificar tu correo y enviar tu solicitud al administrador. '
        'El código vence en 10 minutos. Si no solicitaste una cuenta, ignora este correo.'
    )

    html_mensaje = render_to_string('email/codigo_verificacion.html',{
        'nombre': getattr(solicitud, 'nombre', ''),
        'codigo': codigo,
    })

    if send_mail(
        asunto,
        mensaje_texto,
        settings.DEFAULT_FROM_EMAIL,
        [solicitud.email],
        fail_silently=False,
        html_message=html_mensaje,
    ) != 1:
        raise SMTPException('No se aceptó el mensaje')

    solicitud.codigo_hash = make_password(codigo)
    solicitud.codigo_enviado = timezone.now()
    solicitud.codigo_intentos = 0
    solicitud.save(update_fields=['codigo_hash', 'codigo_enviado', 'codigo_intentos'])


def iniciar_verificacion(request, solicitud):
    request.session['registro_pendiente'] = solicitud.pk
    with transaction.atomic():
        solicitud = SolicitudRegistro.objects.select_for_update().get(pk=solicitud.pk)
        if not solicitud.codigo_enviado or timezone.now() >= solicitud.codigo_enviado + timedelta(seconds=60):
            try:
                enviar_codigo(solicitud)
            except (SMTPException, OSError):
                messages.error(request, 'No pudimos enviar el código. Puedes reintentar desde esta pantalla.')
    return redirect('verificar_correo')


@transaction.atomic
def verificar_correo_view(request):
    solicitud_id = request.session.get('registro_pendiente')
    if not solicitud_id:
        return redirect('solicitar_registro')
    solicitud = get_object_or_404(SolicitudRegistro.objects.select_for_update(), pk=solicitud_id)
    if solicitud.correo_verificado:
        return render(request, 'verificar_correo.html', {'confirmado': True})
    if solicitud.rechazado or solicitud.bloqueado:
        return redirect('solicitar_registro')
    error = None
    if request.method == 'POST':
        if request.POST.get('accion') == 'reenviar':
            if solicitud.codigo_enviado and timezone.now() < solicitud.codigo_enviado + timedelta(seconds=60):
                error = 'Espera un minuto antes de pedir otro código.'
            else:
                try:
                    enviar_codigo(solicitud)
                except (SMTPException, OSError):
                    error = 'No pudimos enviar el código. Inténtalo nuevamente.'
                else:
                    messages.success(request, 'Enviamos un nuevo código a tu correo.')
                    return redirect('verificar_correo')
        elif not solicitud.codigo_enviado or timezone.now() > solicitud.codigo_enviado + timedelta(minutes=10):
            error = 'El código venció o no se ha enviado. Solicita uno nuevo.'
        elif solicitud.codigo_intentos >= 5:
            error = 'Alcanzaste los 5 intentos. Solicita un nuevo código.'
        else:
            codigo = request.POST.get('codigo', '').strip()
            solicitud.codigo_intentos += 1
            if len(codigo) == 4 and codigo.isascii() and codigo.isdigit() and check_password(codigo, solicitud.codigo_hash):
                solicitud.correo_verificado = True
                solicitud.codigo_hash = ''
                solicitud.save(update_fields=['correo_verificado', 'codigo_hash', 'codigo_intentos'])
                return redirect('verificar_correo')
            solicitud.save(update_fields=['codigo_intentos'])
            error = 'El código no coincide. Revisa los 4 números del correo.'
    return render(request, 'verificar_correo.html', {'solicitud': solicitud, 'error': error})
