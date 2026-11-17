
import csv
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_POST
from .models import Medicion
from collections import Counter
from django.contrib.auth.models import User
from django.db.models import Count
from core.models import Comuna, SolicitudRegistro


@staff_member_required(login_url='login')
def admin_mediciones_view(request):
    comunas = list(Comuna.objects.all())
    por_codigo = {c.codigo: c for c in comunas}
    seleccionada = por_codigo.get(request.GET.get('comuna'))
    regiones = sorted({(c.codigo_region, c.region) for c in comunas})
    region = seleccionada.codigo_region if seleccionada else request.GET.get('region', '')
    if region not in dict(regiones):
        region = ''
    conteos = dict(Medicion.objects.exclude(comuna=None).values('comuna_id').annotate(total=Count('id')).values_list('comuna_id', 'total'))
    # La solicitud es la fuente actual de la comuna de monitoreo del usuario.
    cuentas = {u.email.casefold(): u for u in User.objects.all().order_by('id') if u.email}
    usuarios = []
    for solicitud in SolicitudRegistro.objects.filter(aprobado=True, rechazado=False).select_related('comuna_catalogo'):
        usuario = cuentas.get(solicitud.email.casefold())
        if usuario:
            usuarios.append({'nombre': usuario.first_name or solicitud.nombre,
                             'email': usuario.email, 'comuna': solicitud.comuna,
                             'codigo': solicitud.comuna_catalogo_id,
                             'activo': usuario.is_active and not solicitud.bloqueado,
                             'solicitud_id': solicitud.pk})
    conteos_usuarios = Counter(u['codigo'] for u in usuarios if u['codigo'])
    mediciones = Medicion.objects.select_related('usuario', 'comuna').order_by('-fecha_registro', '-pk')
    sin_comuna = mediciones.filter(comuna=None).count()
    if seleccionada:
        mediciones = mediciones.filter(comuna=seleccionada)
        usuarios = [u for u in usuarios if u['codigo'] == seleccionada.codigo]
    elif region:
        mediciones = mediciones.filter(comuna__codigo_region=region)
        usuarios = [u for u in usuarios if u['codigo'] and por_codigo[u['codigo']].codigo_region == region]
    total_mediciones = mediciones.count()
    resumen = [dict(codigo=c.codigo, nombre=c.nombre, region=c.codigo_region,
                    mediciones=conteos.get(c.codigo, 0), usuarios=conteos_usuarios[c.codigo]) for c in comunas]
    return render(request, 'admin_panel/mediciones.html', {
        'mediciones': mediciones,
        'total_mediciones': total_mediciones,
        'seccion_activa': 'mediciones',
        'usuarios_comuna': usuarios, 'comuna_seleccionada': seleccionada,
        'regiones': regiones, 'region_seleccionada': region,
        'resumen_comunas': resumen, 'sin_comuna': sin_comuna,
        'con_mediciones': len(conteos), 'sin_mediciones': len(comunas) - len(conteos),
    })


@staff_member_required(login_url='login')
@require_POST
def eliminar_medicion_view(request, medicion_id):
    medicion = get_object_or_404(Medicion, id=medicion_id)
    ubicacion = medicion.ubicacion
    medicion.delete()
    messages.success(request, f'La medición de {ubicacion} fue eliminada.')
    return redirect('admin_mediciones')





@staff_member_required(login_url='login')
def admin_descargas_view(request):
    mediciones = Medicion.objects.all()
    return render(request, 'admin_panel/descargas.html', {
        'seccion_activa': 'descargas',
        'total_mediciones': mediciones.count(),
        'total_comunas': mediciones.values('ubicacion').distinct().count(),
        'ultima_medicion': mediciones.order_by('-fecha_registro').first(),
    })


def _filas_exportacion():
    return Medicion.objects.select_related('usuario').order_by('-fecha_registro')


@staff_member_required(login_url='login')
def exportar_mediciones_csv_view(request):
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = 'attachment; filename="mediciones_aquacivis.csv"'
    respuesta.write('\ufeff')
    escritor = csv.writer(respuesta)
    escritor.writerow(['Fecha', 'Ubicación', 'pH', 'Conductividad', 'TDS', 'Temperatura', 'Estado', 'Registrado por'])
    for medicion in _filas_exportacion():
        escritor.writerow([
            timezone.localtime(medicion.fecha_registro).strftime('%d/%m/%Y %H:%M'),
            medicion.ubicacion,
            medicion.ph,
            medicion.conductividad,
            medicion.tds,
            medicion.temperatura,
            medicion.alerta_general,
            medicion.usuario.email if medicion.usuario else '',
        ])
    return respuesta


@staff_member_required(login_url='login')
def exportar_mediciones_excel_view(request):
    respuesta = HttpResponse(content_type='application/vnd.ms-excel; charset=utf-8')
    respuesta['Content-Disposition'] = 'attachment; filename="mediciones_aquacivis.xls"'
    filas = ''.join(
        '<tr>' + ''.join(f'<td>{escape(valor)}</td>' for valor in (
            timezone.localtime(medicion.fecha_registro).strftime('%d/%m/%Y %H:%M'),
            medicion.ubicacion, medicion.ph, medicion.conductividad, medicion.tds,
            medicion.temperatura, medicion.alerta_general,
            medicion.usuario.email if medicion.usuario else '',
        )) + '</tr>'
        for medicion in _filas_exportacion()
    )
    respuesta.write(
        '<html><head><meta charset="utf-8"></head><body><table border="1">'
        '<tr><th>Fecha</th><th>Ubicación</th><th>pH</th><th>Conductividad</th>'
        '<th>TDS</th><th>Temperatura</th><th>Estado</th><th>Registrado por</th></tr>'
        f'{filas}</table></body></html>'
    )
    return respuesta
