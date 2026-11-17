# archivo para tener las validaciones de los formularios de medicion (reutilizables)
from .models import ConfiguracionParametro
from core.comunas import *

# Valores de respaldo, en caso de que no exista en la base de datos
RANGOS_POR_DEFECTO = {
    'ph': (0.01, 14.00),
    'conductividad': (0.0, 200.0),
    'tds': (0.0, 9990.0),
    'temperatura': (0.0, 80.0),
}

def obtener_rango(nombre_parametro):
    try:
        config = ConfiguracionParametro.objects.get(nombre_parametro=nombre_parametro)
        return config.valor_min, config.valor_max
    except ConfiguracionParametro.DoesNotExist:
        return RANGOS_POR_DEFECTO[nombre_parametro]

def validar_ph(valor):
    try:
        val = float(valor)
    except (TypeError, ValueError):
        raise ValueError("El pH debe ser un número válido.")

    minimo, maximo = obtener_rango('ph')
    if not (minimo <= val <= maximo):
        raise ValueError(f"Valor invalido, el pH debe estar entre {minimo} y {maximo}.")
    return val

def validar_conductividad(valor):
    try:
        val = float(valor)
    except (TypeError, ValueError):
        raise ValueError("La conductividad debe ser un número válido.")

    minimo, maximo = obtener_rango('conductividad')
    if not (minimo <= val <= maximo):
        raise ValueError(f"Valor invalido, la conductividad debe estar entre {minimo} y {maximo} mS/cm.")
    return val

def validar_tds(valor):
    try:
        val = float(valor)
    except (TypeError, ValueError):
        raise ValueError("Los TDS deben ser un número válido.")

    minimo, maximo = obtener_rango('tds')
    if not (minimo <= val <= maximo):
        raise ValueError(f"Valor invalido, los TDS deben estar entre {minimo} y {maximo} ppm.")
    return val

def validar_temperatura(valor):
    try:
        val = float(valor)
    except (TypeError, ValueError):
        raise ValueError("La temperatura debe ser un número válido.")

    minimo, maximo = obtener_rango('temperatura')
    if not (minimo <= val <= maximo):
        raise ValueError(f"Valor invalido, la temperatura debe estar entre {minimo} y {maximo} °C.")
    return val

def validar_ubicacion(valor):
    if not valor or not str(valor).strip():
        raise ValueError("La ubicación es obligatoria y no puede estar vacía.")
    from core.comunas import exigir_comuna
    return exigir_comuna(valor).nombre
