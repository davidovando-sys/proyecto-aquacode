from datetime import timedelta
from core.shared.filtro_fechas import leer_rango_fechas
from core.shared.paginacion import paginar
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from core.models import Comuna
from formularios.models import Medicion
from django.contrib import messages

def graficos_view(request):
    # filtros generales que afectan a los gráficos y a la tabla.
    periodo_seleccionado = request.GET.get('periodo', '30')
    periodos_validos = {'hoy', '7', '30', 'todo'}
 
    if periodo_seleccionado not in periodos_validos:
        periodo_seleccionado = '30'
 
    # el buscador de comunas envía el código (comuna_codigo).
    # opcionalmente se puede filtrar por región completa
    codigo_comuna = request.GET.get('comuna_codigo', '').strip()
    comuna_seleccionada = (
        Comuna.objects.filter(pk=codigo_comuna.zfill(5)).first()
        if codigo_comuna.isdigit() else None
    )
 
    regiones = list(
        Comuna.objects.order_by('codigo_region')
        .values_list('codigo_region', 'region').distinct()
    )
    region_seleccionada = request.GET.get('region', '').strip()
    if region_seleccionada not in {codigo for codigo, _ in regiones}:
        region_seleccionada = ''
 
    mediciones_base = (
        Medicion.objects
        .select_related('usuario', 'comuna')
        .order_by('-fecha_registro')
    )

    if comuna_seleccionada:
        mediciones_base = mediciones_base.filter(
            comuna=comuna_seleccionada
        )
    elif region_seleccionada:
        mediciones_base = mediciones_base.filter(
            comuna__codigo_region=region_seleccionada
        )

    # Los gráficos utilizan los filtros generales,
    # incluyendo el período seleccionado.
    mediciones_grafico = mediciones_base

    if periodo_seleccionado == 'hoy':
        mediciones_grafico = mediciones_grafico.filter(
            fecha_registro__date=timezone.localdate()
        )
    elif periodo_seleccionado != 'todo':
        dias = int(periodo_seleccionado)
        mediciones_grafico = mediciones_grafico.filter(
            fecha_registro__gte=timezone.now() - timedelta(days=dias)
        )

    mediciones_grafico = list(mediciones_grafico)

    datos_graficos = [
        {
            'etiqueta': timezone.localtime(m.fecha_registro).strftime('%d/%m %H:%M'),
            'comuna': m.comuna.nombre if m.comuna else m.ubicacion,
            'comuna_codigo': m.comuna_id or '',
            'ph': m.ph,
            'conductividad': m.conductividad,
            'tds': m.tds,
            'temperatura': m.temperatura,
        }
        for m in reversed(mediciones_grafico)
    ]

    # La tabla parte desde la consulta base, sin filtro de período.
    mediciones_tabla = mediciones_base

 
    # Filtros exclusivos de la tabla.
    alerta_seleccionada = request.GET.get('alerta', '').strip()
 
    alertas_validas = {'Verde', 'Amarillo', 'Rojo'}
 
    if alerta_seleccionada not in alertas_validas:
        alerta_seleccionada = ''
 
    mediciones_tabla = mediciones_base
 
    if alerta_seleccionada:
        mediciones_tabla = mediciones_tabla.filter(
            alerta_general=alerta_seleccionada
        )
    rango = leer_rango_fechas(request.GET, 'fecha_desde', 'fecha_hasta')
    for error in rango.errores:
        messages.error(request, error)
    mediciones_tabla = rango.aplicar(mediciones_tabla, 'fecha_registro')
 
    # Paginación: máximo 10 mediciones por página.
    pagina_obj = paginar(request, mediciones_tabla, por_pagina=10)

    nombre_comuna_seleccionada = (
    comuna_seleccionada.nombre if comuna_seleccionada else ''
    )

    codigo_comuna_seleccionada = (
        comuna_seleccionada.pk if comuna_seleccionada else ''
    )
 
    return render(request, 'historial.html', {
        # Solo los registros de la página actual se muestran en la tabla.
        'mediciones': pagina_obj.object_list,
        'pagina_obj': pagina_obj,
        'total_mediciones': pagina_obj.paginator.count,
 
        # Datos completos del período seleccionado para los gráficos.
        'datos_graficos': datos_graficos,
 
        # Ubicación: comuna_seleccionada ahora es un objeto Comuna (o None), no un texto.
        'comuna_seleccionada': comuna_seleccionada,
        'regiones': regiones,
        'region_seleccionada': region_seleccionada,
        'periodo_seleccionado': periodo_seleccionado,
 
        # Valores seleccionados en los filtros de la tabla.
        'alerta_seleccionada': alerta_seleccionada,
        'fecha_desde': rango.valor_desde,
        'fecha_hasta': rango.valor_hasta,
        'rango_fechas': rango,
        'nombre_comuna_seleccionada': nombre_comuna_seleccionada,
        'codigo_comuna_seleccionada': codigo_comuna_seleccionada,
    })