
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils import timezone
from core.models import SolicitudRegistro
from core.comunas import *
from .verificacion_views import iniciar_verificacion
from usuarios.models import IntentoInicioSesion, ControlAcceso
from datetime import timedelta
from core.validadores import *


def obtener_ip_cliente(request):
    """Obtiene la IP disponible sin guardar contraseñas ni otros datos sensibles."""
    return request.META.get('REMOTE_ADDR')


MAX_INTENTOS = 5
TIEMPO_BLOQUEO_MINUTOS = 15


def login_view(request):
    # Datos que se devuelven al formulario. Solo el usuario: la contraseña
    # nunca se vuelve a mostrar, así queda vacía cuando hay un error.
    contexto = {}

    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        contrasena = request.POST.get('password')

        contexto['username'] = (usuario_input or '').strip()

        # 1. Normalizamos el input (en minúsculas) para evitar que evadan el bloqueo usando mayúsculas
        username_limpio = usuario_input.strip().lower() if usuario_input else ''

        # 2. Obtenemos o creamos el registro de seguridad de este usuario
        control, creado = ControlAcceso.objects.get_or_create(username=username_limpio)

        # 3. Verificamos si la cuenta está bloqueada por intentos fallidos
        if control.bloqueado_hasta and control.bloqueado_hasta > timezone.now():
            tiempo_restante = int((control.bloqueado_hasta - timezone.now()).total_seconds() / 60)
            tiempo_restante = tiempo_restante if tiempo_restante > 0 else 1 # Para que no diga 0 minutos

            messages.error(request, f'Cuenta bloqueada temporalmente por múltiples intentos fallidos. Intenta nuevamente en {tiempo_restante} minuto(s).')
            return render(request, 'login.html', contexto)

        # 4. Revisamos el bloqueo aplicado por un administrador.
        solicitud = SolicitudRegistro.objects.filter(email=username_limpio).first()
        if solicitud and solicitud.bloqueado:
            if solicitud.bloqueado_hasta and timezone.now() > solicitud.bloqueado_hasta:
                # El castigo expiró, lo desbloqueamos automáticamente
                solicitud.bloqueado = False
                solicitud.bloqueado_hasta = None
                solicitud.save()

                usuario_django = User.objects.filter(email=username_limpio).first()
                if usuario_django:
                    usuario_django.is_active = True
                    usuario_django.save()
            elif solicitud.bloqueado_hasta:
                # El castigo aún está vigente
                segundos = (solicitud.bloqueado_hasta - timezone.now()).total_seconds()
                dias = max(1, -(-int(segundos) // 86400))  # redondea hacia arriba
                messages.error(request, f'Tu cuenta está suspendida. Quedan {dias} día(s) de bloqueo.')
                return render(request, 'login.html', contexto)
            else:
                messages.error(request, 'Tu cuenta se encuentra bloqueada por un administrador.')
                return render(request, 'login.html', contexto)

        # 5. Intentamos autenticar con Django
        user = authenticate(request, username=usuario_input, password=contrasena)

        if user is not None:
            # Éxito: Reiniciar los contadores de seguridad
            control.intentos_fallidos = 0
            control.bloqueado_hasta = None
            control.save()

            login(request, user)
            messages.success(request, f'Sesión iniciada correctamente. Bienvenido, {user.first_name or user.username}.')
            return redirect('home')
        else:
            identificador = (usuario_input or '').strip()
            usuario_existente = User.objects.filter(username__iexact=identificador).first()
            IntentoInicioSesion.objects.create(
                usuario=usuario_existente,
                identificador=identificador,
                direccion_ip=obtener_ip_cliente(request),
            )
            # Fallo: Incrementar el contador y evaluar si merece bloqueo
            control.intentos_fallidos += 1

            if control.intentos_fallidos >= MAX_INTENTOS:
                control.bloqueado_hasta = timezone.now() + timedelta(minutes=TIEMPO_BLOQUEO_MINUTOS)
                control.save()
                messages.error(request, f'Has superado el límite de intentos ({MAX_INTENTOS}). Por seguridad, tu acceso ha sido bloqueado temporalmente por {TIEMPO_BLOQUEO_MINUTOS} minutos.')
            else:
                control.save()
                intentos_restantes = MAX_INTENTOS - control.intentos_fallidos
                messages.error(request, f'Credenciales incorrectas. Te quedan {intentos_restantes} intento(s) antes del bloqueo de seguridad.')

    return render(request, 'login.html', contexto)

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('home')


CAMPOS_REGISTRO = ('nombre', 'comuna', 'comuna_codigo', 'email', 'motivo')


def _mostrar_registro(request, datos, errores): #esta funcion permite que no se eliminen los campos sin errores en el formulario de registro
    datos = dict(datos)
    for campo in errores:
        datos.pop(campo, None)
        if campo == 'comuna':
            datos.pop('comuna_codigo', None)
    return render(request,'solicitar_registro.html',{'datos': datos, 'errores': errores},)


def solicitar_registro_view(request):
    if request.method != 'POST':
        return render(request, 'solicitar_registro.html', {'datos': {}, 'errores': {}})

    datos = {c: (request.POST.get(c) or '').strip() for c in CAMPOS_REGISTRO}
    password = request.POST.get('password') or ''
    password2 = request.POST.get('password2') or ''

    nombre = normalizar_nombre(datos['nombre'])
    datos['nombre'] = nombre
    email = datos['email'].lower()
    motivo = datos['motivo']
    errores = {}

    error = primer_error(validar_nombre, nombre)
    if error:
        errores['nombre'] = error

    if not email:
        errores['email'] = 'Ingresa tu correo electrónico.'

    error = primer_error(validar_password, password)
    if error:
        errores['password'] = error
    
    if not password2:
        errores['password2'] = 'Repite tu contraseña.'
    elif password and password != password2:
        errores['password2'] = 'Las contraseñas no coinciden.'

    comuna = ''
    comuna_catalogo = None
    try:
        comuna_catalogo = exigir_comuna(datos['comuna_codigo'] or datos['comuna'])
        comuna = comuna_catalogo.nombre.strip()
    except ValueError as error:
        errores['comuna'] = str(error)

    if errores:
        return _mostrar_registro(request, datos, errores)

    #Reglas sobre el correo
    solicitud_existente = SolicitudRegistro.objects.filter(email__iexact=email).first()

    if (
        solicitud_existente
        and not solicitud_existente.correo_verificado
        and not solicitud_existente.aprobado
        and not solicitud_existente.rechazado
        and not solicitud_existente.bloqueado
    ):
        usuario = User.objects.filter(email__iexact=email, is_active=False).first()
        if usuario and usuario.check_password(password):
            return iniciar_verificacion(request, solicitud_existente)

    if solicitud_existente and solicitud_existente.rechazado:
        if solicitud_existente.fecha_rechazo:
            dias_pasados = (timezone.now() - solicitud_existente.fecha_rechazo).days
            if dias_pasados < 7:
                errores['email'] = (
                    f'Tu solicitud anterior fue rechazada. Debes esperar '
                    f'{7 - dias_pasados} día(s) para enviar una nueva.'
                )
                return _mostrar_registro(request, datos, errores)

        # Se reutiliza la solicitud anterior y se vuelve a dejar como Pendiente
        SolicitudRegistro.objects.filter(pk=solicitud_existente.pk).update(
            nombre=nombre,
            comuna=comuna,
            comuna_catalogo=comuna_catalogo,
            motivo=motivo,
            rechazado=False,
            correo_verificado=False,
            codigo_hash='',
            codigo_enviado=None,
            codigo_intentos=0,
            fecha_rechazo=None,
            motivo_rechazo='',
            detalle_rechazo='',
            fecha_creacion=timezone.now(),
        )
        usuario_existente = User.objects.filter(email=email).first()
        if usuario_existente:
            usuario_existente.first_name = nombre
            usuario_existente.set_password(password)
            usuario_existente.is_active = False
            usuario_existente.save()
        else:
            User.objects.create_user(
                username=email, email=email, password=password,
                first_name=nombre, is_active=False
            )

        solicitud_existente.refresh_from_db()
        return iniciar_verificacion(request, solicitud_existente)

    # Cuenta ya existente con ese correo
    if User.objects.filter(email=email).exists():
        errores['email'] = 'Ya existe una cuenta asociada a este correo.'
        return _mostrar_registro(request, datos, errores)

    # Solicitud anterior con ese correo
    if SolicitudRegistro.objects.filter(email=email).exists():
        errores['email'] = 'Este correo ya tiene una solicitud registrada.'
        return _mostrar_registro(request, datos, errores)

    #Crear usuario INACTIVO y solicitud pendiente
    usuario = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=nombre,
    )
    usuario.is_active = False
    usuario.save()

    solicitud = SolicitudRegistro.objects.create(
        nombre=nombre,
        comuna=comuna,
        comuna_catalogo=comuna_catalogo,
        email=email,
        motivo=motivo,
        aprobado=False,
    )

    return iniciar_verificacion(request, solicitud)