from decimal import Decimal, InvalidOperation
from core.shared.paginacion import paginar
from django.utils.dateparse import parse_date
from core.shared.filtro_fechas import leer_rango_fechas
from django.shortcuts import render, redirect
from .models import Medicion, ConfiguracionParametro
from .validaciones import (validar_ph, validar_conductividad,
                           validar_tds, validar_temperatura, validar_ubicacion)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import ConfiguracionAlerta
from core.comunas import exigir_comuna, normalizar

from django.utils import timezone
from datetime import time


def calcular_alerta(ph, conductividad, tds, temperatura, promedio_tds):
    configuracion = ConfiguracionAlerta.actual()
    alerta = "Verde"

    # Evaluar pH
    if ph < configuracion.ph_minimo_critico or ph > configuracion.ph_maximo_critico:
        alerta = "Rojo"
    elif ph < configuracion.ph_minimo_normal or ph > configuracion.ph_maximo_normal:
        alerta = "Amarillo"

    # Evaluar TDS con la nueva lógica
    alerta_tds = "Verde"
    if tds < 50 or tds > 1000:
        alerta_tds = "Rojo"
    elif tds > promedio_tds:
        alerta_tds = "Amarillo"

    # Evaluar Conductividad y Temperatura, y fusionar resultados
    if (
        conductividad > configuracion.conductividad_critica
        or temperatura > configuracion.temperatura_critica
        or alerta_tds == "Rojo"
    ):
        alerta = "Rojo"
    elif alerta != "Rojo" and (
        conductividad > configuracion.conductividad_preventiva
        or temperatura > configuracion.temperatura_preventiva
        or alerta_tds == "Amarillo"
    ):
        alerta = "Amarillo"

    return alerta


def evaluar_ph(valor):
    if 6.8 <= valor <= 8.2:
        return {
            "nivel": "Bajo",
            "color": "success",
            "icono": "bi-check-circle-fill",
            "mensaje": (
                "pH dentro del rango esperado. "
                "El valor se encuentra dentro del intervalo establecido "
                "para agua potable."
            )
        }
    elif 6.5 <= valor < 6.8 or 8.2 < valor <= 8.5:
        return {
            "nivel": "Medio",
            "color": "warning",
            "icono": "bi-exclamation-triangle-fill",
            "mensaje": (
                "pH cercano al límite. "
                "El valor se aproxima a los límites recomendados. "
                "Se sugiere continuar observando y repetir la medición."
            )
        }
    else:
        return {
            "nivel": "Alto",
            "color": "danger",
            "icono": "bi-x-octagon-fill",
            "mensaje": (
                "pH fuera de rango. "
                "El valor está fuera del intervalo establecido para agua potable. "
                "Se recomienda verificar la medición y realizar análisis complementarios."
            )
        }


def evaluar_tds(valor, promedio_comuna):
    if valor < 50 or valor > 1000:
        return {
            "nivel": "Alto",
            "color": "danger",
            "icono": "bi-x-octagon-fill",
            "mensaje": (
                f"TDS crítico ({valor} ppm). "
                "El valor está fuera de los rangos absolutos permitidos (50-1000 ppm). "
                "Se recomienda verificar el agua de inmediato."
            )
        }
    elif valor <= promedio_comuna:
        return {
            "nivel": "Bajo",
            "color": "success",
            "icono": "bi-check-circle-fill",
            "mensaje": (
                f"TDS dentro del rango esperado ({valor} ppm). "
                f"El valor es normal para esta comuna (Referencia calculada: {promedio_comuna:.1f} ppm)."
            )
        }
    else:
        return {
            "nivel": "Medio",
            "color": "warning",
            "icono": "bi-exclamation-triangle-fill",
            "mensaje": (
                f"TDS elevado ({valor} ppm). "
                f"Supera la normalidad de su comuna ({promedio_comuna:.1f} ppm) pero está dentro de los límites de consumo seguro. "
                "Se sugiere monitorear."
            )
        }

def evaluar_conductividad(valor, configuracion):
    if valor > configuracion.conductividad_critica:
        return {
            "nivel": "Alto",
            "color": "danger",
            "icono": "bi-x-octagon-fill",
            "mensaje": (
                f"Conductividad registrada: {valor:.2f} mS/cm. "
                f"Supera el umbral crítico configurado "
                f"({configuracion.conductividad_critica:.2f} mS/cm). "
                "Se recomienda verificar la medición y revisar la fuente."
            )
        }

    elif valor > configuracion.conductividad_preventiva:
        return {
            "nivel": "Medio",
            "color": "warning",
            "icono": "bi-exclamation-triangle-fill",
            "mensaje": (
                f"Conductividad registrada: {valor:.2f} mS/cm. "
                f"Supera el umbral preventivo "
                f"({configuracion.conductividad_preventiva:.2f} mS/cm). "
                "Se recomienda continuar monitoreando."
            )
        }

    return {
        "nivel": "Bajo",
        "color": "success",
        "icono": "bi-check-circle-fill",
        "mensaje": (
            f"Conductividad registrada: {valor:.2f} mS/cm. "
            "Se encuentra dentro de los umbrales configurados."
        )
    }


def evaluar_temperatura(valor, configuracion):
    if valor > configuracion.temperatura_critica:
        return {
            "nivel": "Alto",
            "color": "danger",
            "icono": "bi-x-octagon-fill",
            "mensaje": (
                f"Temperatura registrada: {valor:.2f} °C. "
                f"Supera el umbral crítico configurado "
                f"({configuracion.temperatura_critica:.2f} °C). "
                "Se recomienda verificar las condiciones de medición."
            )
        }

    elif valor > configuracion.temperatura_preventiva:
        return {
            "nivel": "Medio",
            "color": "warning",
            "icono": "bi-exclamation-triangle-fill",
            "mensaje": (
                f"Temperatura registrada: {valor:.2f} °C. "
                f"Supera el umbral preventivo "
                f"({configuracion.temperatura_preventiva:.2f} °C). "
                "Se recomienda continuar monitoreando."
            )
        }

    return {
        "nivel": "Bajo",
        "color": "success",
        "icono": "bi-check-circle-fill",
        "mensaje": (
            f"Temperatura registrada: {valor:.2f} °C. "
            "Se encuentra dentro de los umbrales configurados."
        )
    }
@login_required
def nueva_medicion_view(request):
    alertas = []
    estado_general = None
    config = {c.nombre_parametro: c for c in ConfiguracionParametro.objects.all()}
 
    if request.method == 'POST':
        try:
            # 1. Definir el bloque horario según la hora actual
            hora_actual = timezone.localtime().time()
            bloque_actual = None
 
            if time(8, 0) <= hora_actual < time(12, 0):
                bloque_actual = 'Mañana'
            elif time(12, 0) <= hora_actual < time(16, 0):
                bloque_actual = 'Día'
            elif time(16, 0) <= hora_actual <= time(20, 0):
                bloque_actual = 'Noche'
            else:
                # Si está fuera de horario, bloqueamos el registro
                messages.error(request, "Las mediciones solo se pueden registrar en los bloques habilitados (08:00 a 20:00).")
                return render(request, 'formularios/nueva_medicion.html', {"alertas": alertas, "config": config})
 
            ph_val = validar_ph(request.POST.get('ph'))
            cond_val = validar_conductividad(request.POST.get('conductividad'))
            tds_val = validar_tds(request.POST.get('tds'))
            temp_val = validar_temperatura(request.POST.get('temperatura'))
 
            # Comuna: si viene el código, manda el código; el texto solo se usa para comprobar
            # que ambos hablan de la misma comuna. Así no falla con nombres repetidos.
            ubicacion_texto = request.POST.get('ubicacion', '')
            if not ubicacion_texto.strip():
                raise ValueError("La ubicación es obligatoria y no puede estar vacía.")
            comuna = exigir_comuna(request.POST.get('comuna_codigo') or ubicacion_texto)
            if normalizar(comuna.nombre) != normalizar(ubicacion_texto):
                raise ValueError('La comuna seleccionada no coincide con la ubicación.')
            ubicacion_val = comuna.nombre  # siempre el nombre oficial del catálogo
 
            # Origen de la ubicación
            origen = request.POST.get('origen_ubicacion', 'gps')
            if origen not in dict(Medicion.ORIGENES_UBICACION):
                origen = 'gps'
 
            lat_val = request.POST.get('latitud')
            lng_val = request.POST.get('longitud')
            lat_float = float(lat_val) if lat_val else None
            lng_float = float(lng_val) if lng_val else None
            if (lat_float is not None and not -90 <= lat_float <= 90) or \
               (lng_float is not None and not -180 <= lng_float <= 180):
                raise ValueError('Las coordenadas están fuera de rango.')
 
            # Si la persona mantuvo una comuna distinta a donde está, esas coordenadas
            # no corresponden al lugar de la medición: no se guardan.
            if origen == 'comuna_seleccionada':
                lat_float = lng_float = None
 
            config_alerta = ConfiguracionAlerta.actual()
 
            # Últimas "N" mediciones de esta comuna para sacar el promedio
            mediciones_previas = Medicion.objects.filter(
                comuna=comuna
            ).order_by('-fecha_registro')[:config_alerta.tds_muestras_minimas]
 
            if len(mediciones_previas) >= config_alerta.tds_muestras_minimas:
                promedio_tds = sum(m.tds for m in mediciones_previas) / len(mediciones_previas)
            else:
                promedio_tds = config_alerta.tds_base
 
            # Evaluar individualmente los cuatro parámetros
            alertas.append({
                "parametro": "pH",
                "valor": ph_val,
                "unidad": "",
                **evaluar_ph(ph_val)
            })
 
            alertas.append({
                "parametro": "TDS",
                "valor": tds_val,
                "unidad": "ppm",
                **evaluar_tds(tds_val, promedio_tds)
            })
 
            alertas.append({
                "parametro": "Conductividad eléctrica",
                "valor": cond_val,
                "unidad": "mS/cm",
                **evaluar_conductividad(cond_val, config_alerta)
            })
 
            alertas.append({
                "parametro": "Temperatura",
                "valor": temp_val,
                "unidad": "°C",
                **evaluar_temperatura(temp_val, config_alerta)
            })
 
            color_alerta = calcular_alerta(
                ph_val,
                cond_val,
                tds_val,
                temp_val,
                promedio_tds
            )
 
            # Convertir el resultado general a un formato visual
            estados_generales = {
                "Verde": {
                    "nivel": "Bajo",
                    "color": "success",
                    "icono": "bi-check-circle-fill"
                },
                "Amarillo": {
                    "nivel": "Medio",
                    "color": "warning",
                    "icono": "bi-exclamation-triangle-fill"
                },
                "Rojo": {
                    "nivel": "Alto",
                    "color": "danger",
                    "icono": "bi-x-octagon-fill"
                }
            }
 
            estado_general = estados_generales.get(
                color_alerta,
                {
                    "nivel": "Sin clasificar",
                    "color": "secondary",
                    "icono": "bi-question-circle-fill"
                }
            )
 
            usuario_actual = request.user if request.user.is_authenticated else None
 
            # 2. Buscar si el usuario ya registró algo hoy en este mismo bloque
            hoy = timezone.localtime().date()
            medicion_existente = Medicion.objects.filter(
                usuario=usuario_actual,
                bloque_horario=bloque_actual,
                fecha_registro__date=hoy
            ).first()
 
            # 3. Lógica de guardado
            if medicion_existente:
                # Si ya existe, simplemente actualizamos sus valores (guardando solo la última)
                medicion_existente.ph = ph_val
                medicion_existente.conductividad = cond_val
                medicion_existente.tds = tds_val
                medicion_existente.temperatura = temp_val
                medicion_existente.ubicacion = ubicacion_val
                medicion_existente.comuna = comuna
                medicion_existente.origen_ubicacion = origen
                medicion_existente.alerta_general = color_alerta
                medicion_existente.latitud = lat_float
                medicion_existente.longitud = lng_float
                medicion_existente.fecha_registro = timezone.now()
                medicion_existente.save()
                messages.info(request, f"Se ha actualizado tu medición para el bloque '{bloque_actual}'.")
            else:
                Medicion.objects.create(
                    ph=ph_val,
                    conductividad=cond_val,
                    tds=tds_val,
                    temperatura=temp_val,
                    ubicacion=ubicacion_val,
                    comuna=comuna,
                    origen_ubicacion=origen,
                    alerta_general=color_alerta,
                    usuario=usuario_actual,
                    latitud=lat_float,
                    longitud=lng_float,
                    bloque_horario=bloque_actual
                )
                messages.success(request, f"Tu medición para el bloque '{bloque_actual}' fue guardada exitosamente.")
 
            return render(request, 'formularios/nueva_medicion.html',
                          {"alertas": alertas, "config": config, "estado_general": estado_general})
 
        except ValueError as e:
            messages.error(request, f"Error en la validación de datos: {str(e)}")
            alertas.append({
                "parametro": "Error", "nivel": "Error", "color": "danger",
                "icono": "bi-x-circle-fill",
                "mensaje": str(e) or "Ingrese valores válidos."
            })
 
    return render(
        request,
        'formularios/nueva_medicion.html',
        {
            "alertas": alertas,
            "config": config,
            "estado_general": estado_general
        }
    )


@login_required
def historial_mediciones(request):
    parametros = {
        "ph": "pH",
        "conductividad": "Conductividad (mS/cm)",
        "tds": "TDS (ppm)",
        "temperatura": "Temperatura (°C)",
    }
    alertas_disponibles = {
        "Verde": "Riesgo bajo (verde)",
        "Amarillo": "Riesgo medio (amarillo)",
        "Rojo": "Riesgo alto (rojo)",
        "Gris": "Sin clasificar (gris)",
    }

    filtros = {
        "parametro": request.GET.get("parametro", "").strip(),
        "minimo": request.GET.get("minimo", "").strip(),
        "maximo": request.GET.get("maximo", "").strip(),
        "alerta": request.GET.get("alerta", "").strip(),
        "desde": request.GET.get("desde", "").strip(),
        "hasta": request.GET.get("hasta", "").strip(),
        "bloque_horario": request.GET.get("bloque_horario", "").strip(),
    }
    errores = []
    mediciones = Medicion.objects.filter(usuario=request.user)

    # Lista blanca: el usuario no puede elegir campos arbitrarios de la BD.
    campo = filtros["parametro"]
    if campo and campo not in parametros:
        errores.append("El parámetro seleccionado no es válido.")
        campo = ""

    # Estos riesgos son los que realmente almacena Medicion.alerta_general.
    riesgo = filtros["alerta"]
    if riesgo:
        if riesgo in alertas_disponibles:
            mediciones = mediciones.filter(alerta_general=riesgo)
        else:
            errores.append("El nivel de alerta seleccionado no es válido.")
    #Filtrar por la hora real de registro
    bloque = filtros["bloque_horario"]

    horarios = {
        "Mañana": (time(8, 0), time(12, 0)),
        "Día": (time(12, 0), time(16, 0)),
        "Noche": (time(16, 0), time(20, 0)),
    }

    if bloque:
        if bloque in horarios:
            inicio, fin = horarios[bloque]

            mediciones = mediciones.filter(
                fecha_registro__time__gte=inicio,
                fecha_registro__time__lt=fin
            )
        else:
            errores.append(
                "El bloque horario seleccionado no es válido."
            )
    # El rango numérico se aplica al parámetro elegido, no a los cuatro.
    def leer_numero(nombre):
        texto = filtros[nombre]
        if not texto:
            return None
        try:
            numero = Decimal(texto.replace(",", "."))
        except InvalidOperation:
            errores.append(f"El valor de {nombre} debe ser un número válido.")
            return None
        if not numero.is_finite():
            errores.append(f"El valor de {nombre} debe ser finito.")
            return None
        return numero

    minimo = leer_numero("minimo")
    maximo = leer_numero("maximo")
    if minimo is not None or maximo is not None:
        if not campo:
            errores.append("Selecciona un parámetro para filtrar por valor.")
        elif minimo is not None and maximo is not None and minimo > maximo:
            errores.append("El valor mínimo no puede ser mayor que el máximo.")
        else:
            if minimo is not None:
                mediciones = mediciones.filter(**{f"{campo}__gte": minimo})
            if maximo is not None:
                mediciones = mediciones.filter(**{f"{campo}__lte": maximo})

    rango = leer_rango_fechas(request.GET)          # usa los parámetros "desde" y "hasta"
    errores.extend(rango.errores)
    mediciones = rango.aplicar(mediciones, "fecha_registro")
    filtros["desde"], filtros["hasta"] = rango.valor_desde, rango.valor_hasta

    mediciones = mediciones.order_by("-fecha_registro", "-pk")
    pagina = paginar(request, mediciones, por_pagina=10) 

    return render(
        request,
        "formularios/historial_mediciones.html",
        {
            "pagina": pagina,
            "total_registros": pagina.paginator.count,
            "parametros": parametros,
            "alertas_disponibles": alertas_disponibles,
            "filtros": filtros,
            "errores": errores,
            "rango": rango,
        },
    )
