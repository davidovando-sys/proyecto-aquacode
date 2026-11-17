
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from core.forms import ConfiguracionAlertaForm, ContenidoWebForm
from core.models import ConfiguracionAlerta, ContenidoWeb, SolicitudRegistro, Comuna
from formularios.models import Medicion
from core.utils_mapa import coordenadas_para_mapa

def _ubicacion(m):
    if m.comuna:
        return {
            'comuna': m.comuna.nombre,
            'comuna_codigo': m.comuna_id,
            'region': m.comuna.codigo_region,
        }
    # mediciones antiguas todavía sin comuna asociada se muestran, pero no entran en los filtros de comuna/región.
    return {'comuna': m.ubicacion, 'comuna_codigo': '', 'region': ''}

def home_view(request):
    es_admin = (
        request.user.is_authenticated
        and request.user.is_staff
        and not request.session.get('vista_usuario')
    )

    mediciones = list(
        Medicion.objects
        .filter(fecha_registro__gte=timezone.now() - timedelta(days=30))
        .select_related('usuario', 'comuna')
        .order_by('-fecha_registro')
    )
 
    solicitudes = {}
    if es_admin:
        correos = {m.usuario.email for m in mediciones if m.usuario and m.usuario.email}
        solicitudes = {
            s.email.lower(): s
            for s in SolicitudRegistro.objects.filter(email__in=correos)
        }
 
    puntos_mapa = []
    for m in mediciones:
        ubicacion= coordenadas_para_mapa(m)
        if ubicacion is None:
            continue
        lat, lng, aproximada = ubicacion

        punto = {
            'lat': lat if es_admin else round(lat, 3),
            'lng': lng if es_admin else round(lng, 3),
            'aproximada': aproximada,
            **_ubicacion(m),
            'alerta': m.alerta_general,
            'fecha': timezone.localtime(m.fecha_registro).isoformat(),
            'fecha_texto': timezone.localtime(m.fecha_registro).strftime('%d/%m/%Y %H:%M'),
            'ph': m.ph,
            'conductividad': m.conductividad,
            'tds': m.tds,
            'temperatura': m.temperatura,
        }
        if es_admin:
            usuario = m.usuario
            solicitud = solicitudes.get(usuario.email.lower()) if usuario and usuario.email else None
            punto['registrado_por'] = None if not usuario else {
                'nombre': (solicitud.nombre if solicitud else usuario.first_name) or usuario.username,
                'correo': usuario.email or usuario.username,
                'comuna': solicitud.comuna if solicitud else '',
            }
        puntos_mapa.append(punto)
 
    datos_graficos = [
        {
            'fecha': timezone.localtime(m.fecha_registro).isoformat(),
            'etiqueta': timezone.localtime(m.fecha_registro).strftime('%d/%m %H:%M'),
            **_ubicacion(m),
            'ph': m.ph,
            'conductividad': m.conductividad,
            'tds': m.tds,
            'temperatura': m.temperatura,
        }
        for m in reversed(mediciones)
    ]
 
    regiones = list(
        Comuna.objects.order_by('codigo_region')
        .values_list('codigo_region', 'region').distinct()
    )
 
    return render(request, 'inicio.html', {
        'contenido_web': ContenidoWeb.actual(),
        'datos_graficos': datos_graficos,
        'puntos_mapa': puntos_mapa,
        'regiones': regiones,
    })

def sobre_nosotros_view(request):
    return render(request, 'sobre_nosotros.html', {'contenido_web': ContenidoWeb.actual()})

@staff_member_required(login_url='login')
def admin_umbrales_view(request):
    configuracion = ConfiguracionAlerta.actual()
    formulario = ConfiguracionAlertaForm(request.POST or None, instance=configuracion)
    if request.method == 'POST' and formulario.is_valid():
        formulario.save()
        messages.success(request, 'Los umbrales de alerta fueron actualizados correctamente.')
        return redirect('admin_umbrales')
    return render(request, 'admin_panel/umbrales.html', {
        'formulario': formulario,
        'configuracion': configuracion,
        'seccion_activa': 'umbrales',
    })


@staff_member_required(login_url='login')
def admin_contenido_view(request):
    contenido = ContenidoWeb.actual()
    formulario = ContenidoWebForm(request.POST or None, instance=contenido)
    if request.method == 'POST' and formulario.is_valid():
        formulario.save()
        messages.success(request, 'El contenido web fue publicado correctamente.')
        return redirect('admin_contenido')
    return render(request, 'admin_panel/contenido.html', {
        'formulario': formulario,
        'contenido': contenido,
        'seccion_activa': 'contenido',
    })

#Vista de usuario para el admins
@staff_member_required(login_url='login')
def activar_vista_usuario(request):
    request.session['vista_usuario'] = True
    return redirect('home')

@staff_member_required(login_url='login')
def desactivar_vista_usuario(request):
    request.session.pop('vista_usuario',None)
    return redirect('dashboard_admin')
