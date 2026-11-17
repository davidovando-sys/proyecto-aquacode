
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import request
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.correos import enviar_correo_estado_solicitud
from core.forms import EditarUsuarioForm, CrearAdministradorForm
from core.models import SolicitudRegistro, HistorialBloqueo
from formularios.models import Medicion
from datetime import timedelta
from django.db.models import Count, Q, IntegerField, Case, When
from core.shared.paginacion import paginar



@staff_member_required(login_url='login')
def dashboard_admin_view(request):
    solicitudes = (
        SolicitudRegistro.objects
        .filter(rechazado=False)
        .filter(Q(correo_verificado=True) | Q(aprobado=True))
    )

    if request.user.email:
        solicitudes = solicitudes.exclude(email__iexact=request.user.email)

    emails_inactivos = (
        User.objects.filter(is_active=False)
        .exclude(email='')
        .values('email')
    )

    totales = solicitudes.aggregate(
        pendientes=Count('pk', filter=Q(aprobado=False)),
        bloqueados=Count('pk', filter=Q(bloqueado=True)),
        activos=Count(
            'pk',
            filter=Q(aprobado=True, bloqueado=False)
            & ~Q(email__in=emails_inactivos),
        ),
    )

    total_usuarios = solicitudes.count()

    # Filtro por estado
    filtros_estado = {
        'activos': Q(aprobado=True, bloqueado=False)
                   & ~Q(email__in=emails_inactivos),
        'bloqueados': Q(bloqueado=True),
        'pendientes': Q(aprobado=False),
    }

    estado = request.GET.get('estado', 'todos')

    if estado in filtros_estado:
        solicitudes = solicitudes.filter(filtros_estado[estado])
    else:
        estado = 'todos'

    etiquetas_estado = {
        'todos': 'Usuarios y solicitudes',
        'activos': 'Usuarios activos',
        'bloqueados': 'Usuarios bloqueados',
        'pendientes': 'Solicitudes pendientes',
    }

    # Buscador
    buscar = request.GET.get('buscar', '').strip()

    if buscar:
        solicitudes = solicitudes.filter(
            Q(nombre__icontains=buscar)
            | Q(email__icontains=buscar)
            | Q(comuna__icontains=buscar)
        )

    # Ordenamiento
    ordenes = {
        'recientes': '-fecha_creacion',
        'antiguos': 'fecha_creacion',
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'correo_asc': 'email',
        'correo_desc': '-email',
        'comuna_asc': 'comuna',
        'comuna_desc': '-comuna',
    }

    orden = request.GET.get('orden', 'recientes')

    if orden not in ordenes:
        orden = 'recientes'

    solicitudes = solicitudes.annotate(
    prioridad_bloqueo=Case(
        When(
            Q(bloqueado=True) | Q(email__in=emails_inactivos),
            then=1
        ),
        default=0,
        output_field=IntegerField()
    )
    ).order_by(
        'prioridad_bloqueo',
        ordenes[orden],
        '-pk'
    )

    # Paginación
    pagina_obj = paginar(request, solicitudes, por_pagina=10)
    solicitudes_pagina = list(pagina_obj.object_list)

    #usuarios y conteos de las filas de esta página
    usuarios_por_email = {
        usuario.email: usuario
        for usuario in User.objects.filter(
            email__in=[s.email for s in solicitudes_pagina]
        )
    }

    conteos = {
        fila['usuario']: fila['total']
        for fila in (
            Medicion.objects
            .filter(usuario__in=usuarios_por_email.values())
            .values('usuario')
            .annotate(total=Count('id'))
        )
    }

    filas = []

    for solicitud in solicitudes_pagina:
        usuario = usuarios_por_email.get(solicitud.email)

        filas.append({
            'solicitud': solicitud,
            'usuario': usuario,
            'mediciones': conteos.get(usuario.pk, 0) if usuario else 0,
        })

    return render(request, 'admin_panel/usuarios.html', {
        'filas': filas,
        'pagina_obj': pagina_obj,
        'total_usuarios': total_usuarios,
        'estado_seleccionado': estado,
        'titulo_listado': etiquetas_estado[estado],
        'seccion_activa': 'usuarios',
        'total_pendientes': totales['pendientes'],
        'total_activos': totales['activos'],
        'total_bloqueados': totales['bloqueados'],
        'motivos_rechazo': SolicitudRegistro.MOTIVOS_RECHAZO,
        'buscar': buscar,
        'orden': orden,
    })

@staff_member_required(login_url='login')
@require_POST
def aprobar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRegistro, id=solicitud_id)
    if not solicitud.correo_verificado or solicitud.rechazado or solicitud.bloqueado:
        messages.error(request, 'Primero debe verificar su correo para aprobar la solicitud.')
        return redirect('dashboard_admin')


    if not solicitud.aprobado:
        solicitud.aprobado = True
        solicitud.save()

        usuario = User.objects.filter(email=solicitud.email).first()

        if usuario:
            usuario.is_active = True
            usuario.save()

        try:
            enviar_correo_estado_solicitud(solicitud)
        except Exception:
            messages.warning(request, 'La solicitud se aprobó, pero no se pudo enviar el correo de aviso.')

        messages.success(
            request,
            f'La solicitud de {solicitud.nombre} ha sido aprobada.'
        )

    return redirect('dashboard_admin')

# --- NUEVA VISTA PARA RECHAZAR ---
@staff_member_required(login_url='login')
@require_POST
def rechazar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRegistro, id=solicitud_id)

    motivo = request.POST.get('motivo_rechazo', '')
    detalle = request.POST.get('detalle_rechazo', '').strip()

    if motivo not in dict(SolicitudRegistro.MOTIVOS_RECHAZO):
        messages.error(request, 'Debes seleccionar un motivo de rechazo.')
        return redirect('dashboard_admin')

    if motivo == 'otro' and not detalle:
        messages.error(request, 'Si el motivo es "Otro", debe especificarlo.')
        return redirect('dashboard_admin')

    if not solicitud.aprobado and not solicitud.rechazado:
        solicitud.rechazado = True
        solicitud.fecha_rechazo = timezone.now()
        solicitud.motivo_rechazo = motivo
        solicitud.detalle_rechazo = detalle
        solicitud.save()
        try:
            enviar_correo_estado_solicitud(solicitud)
        except Exception:
            messages.warning(request, 'La solicitud se rechazó, pero no se pudo enviar el correo de aviso.')
        messages.warning(
            request,
            f'La solicitud de {solicitud.nombre} fue rechazada por({solicitud.get_motivo_rechazo_display()}).'
        )
    return redirect('dashboard_admin')

@staff_member_required(login_url='login')
@require_POST # *evaluar si dejar esta funcion*
#(los profes dijeron que no era buena idea permitir que se eliminen usuarios de forma permanente)
def eliminar_usuario_view(request, solicitud_id): 
    solicitud = get_object_or_404(SolicitudRegistro, id=solicitud_id)
    if solicitud.aprobado:
        usuario_real = User.objects.filter(email=solicitud.email).first()
        if usuario_real:
            if usuario_real == request.user:
                messages.error(request, 'No puedes eliminar la cuenta con la que estás administrando el panel.')
                return redirect('dashboard_admin')
            if usuario_real.is_staff and usuario_real.is_active:
                hay_otro_admin = User.objects.filter(is_staff=True, is_active=True).exclude(pk=usuario_real.pk).exists()
                if not hay_otro_admin:
                    messages.error(request, 'No se puede eliminar el único administrador activo.')
                    return redirect('dashboard_admin')
            usuario_real.delete() # Esto borra sus credenciales de login
            
    nombre_eliminado = solicitud.nombre
    solicitud.delete()
    messages.success(request, f'El usuario {nombre_eliminado} y todos sus accesos han sido eliminados permanentemente.')
    
    return redirect('dashboard_admin')

@staff_member_required(login_url='login')
@require_POST
def bloquear_usuario_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRegistro, id=solicitud_id)
    
    if solicitud.aprobado and not solicitud.bloqueado:
        usuario_real = User.objects.filter(email=solicitud.email).first()
        if usuario_real == request.user:
            messages.error(request, 'No puedes bloquear la cuenta con la que estás administrando el panel.')
            return redirect('dashboard_admin')

        # Capturar el tipo de bloqueo enviado desde el modal
        tipo_bloqueo = request.POST.get('tipo_bloqueo', 'indefinido')
        
        solicitud.bloqueado = True
        if tipo_bloqueo == '7_dias':
            solicitud.bloqueado_hasta = timezone.now() + timedelta(days=7)
            mensaje = f'La cuenta de {solicitud.nombre} ha sido bloqueada por 7 días.'
        else:
            solicitud.bloqueado_hasta = None
            mensaje = f'La cuenta de {solicitud.nombre} ha sido bloqueada indefinidamente.'
            
        solicitud.save()
        # Registrar el bloqueo en el historial
        HistorialBloqueo.objects.create(
            solicitud=solicitud,
            administrador=request.user,
            motivo=request.POST.get('motivo_bloqueo', '').strip()
            or "Bloqueo realizado por administrador"
        )
        
        if usuario_real:
            usuario_real.is_active = False 
            usuario_real.save()
            
        messages.warning(request, mensaje)
        
    return redirect('dashboard_admin')


@staff_member_required(login_url='login') #funcion nueva para poder desbloquear a los usuarios
@require_POST
def desbloquear_usuario_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRegistro, id=solicitud_id)

    if solicitud.aprobado and solicitud.bloqueado:
        solicitud.bloqueado = False
        solicitud.save()

        usuario_real = User.objects.filter(email=solicitud.email).first()
        if usuario_real:
            usuario_real.is_active = True
            usuario_real.save()

        messages.success(request, f'La cuenta de {solicitud.nombre} ha sido desbloqueada.')

    return redirect('dashboard_admin')


@staff_member_required(login_url='login')
def editar_usuario_view(request, solicitud_id):

    solicitud = get_object_or_404(
        SolicitudRegistro,
        id=solicitud_id,
        aprobado=True,
        rechazado=False
    )

    usuario = get_object_or_404(
        User,
        email=solicitud.email
    )

    formulario = EditarUsuarioForm(
        request.POST or None,
        solicitud=solicitud,
        usuario=usuario,
        administrador=request.user,
    )

    if request.method == 'POST' and formulario.is_valid():

        datos = formulario.cleaned_data

        with transaction.atomic():

            # Actualizar datos de la solicitud sin ejecutar su save personalizado.
            SolicitudRegistro.objects.filter(
                pk=solicitud.pk
            ).update(
                nombre=datos['nombre'],
                email=datos['email'],
                comuna=datos['comuna'],
                comuna_catalogo=formulario.comuna_catalogo,
            )

            # Actualizar cuenta de usuario.
            usuario.first_name = datos['nombre']
            usuario.email = datos['email']
            usuario.username = datos['email']
            usuario.is_staff = datos['rol'] == 'administrador'

            usuario.save(
                update_fields=(
                    'first_name',
                    'email',
                    'username',
                    'is_staff',
                )
            )

        messages.success(
            request,
            f'Los datos y permisos de {datos["nombre"]} fueron actualizados.'
        )

        return redirect('dashboard_admin')

    return render(
        request,
        'admin_panel/editar_usuario.html',
        {
            'formulario': formulario,
            'solicitud': solicitud,
            'usuario_editado': usuario,
            'seccion_activa': 'usuarios',
        }
    )

@staff_member_required(login_url='login')
def crear_administrador_view(request):
    formulario = CrearAdministradorForm(request.POST or None)

    if request.method == 'POST' and formulario.is_valid():
        datos = formulario.cleaned_data
        with transaction.atomic():
            # el User va primero para que el save() de SolicitudRegistro no cree otra cuenta, hay que ver esto
            User.objects.create_user(
                username=datos['email'], email=datos['email'],
                password=datos['password'], first_name=datos['nombre'],
                is_staff=True, is_active=True,
            )
            SolicitudRegistro.objects.create(
                nombre=datos['nombre'], comuna=datos['comuna'],
                comuna_catalogo=formulario.comuna_catalogo,
                email=datos['email'], aprobado=True,
            )
        messages.success(request, f'La cuenta de administrador de {datos["nombre"]} fue creada.')
        return redirect('dashboard_admin')

    return render(request, 'admin_panel/crear_admin.html', {
        'formulario': formulario,
        'seccion_activa': 'usuarios',
    })

@staff_member_required(login_url='login')
def ver_usuario_view(request, solicitud_id):

    solicitud = get_object_or_404(
        SolicitudRegistro,
        id=solicitud_id,
        aprobado=True,
        rechazado=False
    )

    usuario = get_object_or_404(
        User,
        email=solicitud.email
    )

    # Historial de mediciones del usuario
    mediciones = Medicion.objects.filter(
        usuario=usuario
    ).select_related(
        'usuario'
    ).order_by(
        '-fecha_registro'
    )

    # Historial de bloqueos
    historial_bloqueos = solicitud.historial_bloqueos.order_by(
        '-fecha_bloqueo',
        '-pk'
    )

    return render(
        request,
        'admin_panel/ver_usuario.html',
        {
            'solicitud': solicitud,
            'usuario_editado': usuario,
            'mediciones': mediciones,
            'total_mediciones': mediciones.count(),
            'historial_bloqueos': historial_bloqueos,
            'seccion_activa': 'usuarios',
        }
    )