from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone
from django.utils.dateparse import parse_date


@dataclass
class RangoFechas:
    desde: date | None = None
    hasta: date | None = None
    hoy: date | None = None
    minima: date | None = None
    errores: list = field(default_factory=list)
    

    @property
    def valor_desde(self):
        return self.desde.isoformat() if self.desde else ""

    @property
    def valor_hasta(self):
        return self.hasta.isoformat() if self.hasta else ""

    @property
    def valido(self):
        return not self.errores

    def aplicar(self, queryset, campo="fecha_registro"):
        if self.desde:
            queryset = queryset.filter(**{f"{campo}__date__gte": self.desde})
        if self.hasta:
            queryset = queryset.filter(**{f"{campo}__date__lte": self.hasta})
        return queryset


def _leer_fecha(texto, etiqueta, errores):
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        fecha = parse_date(texto)
    except ValueError:          # formato correcto pero fecha imposible (2026-02-31)
        fecha = None
    if fecha is None:
        errores.append(f"La fecha {etiqueta} no es válida.")
    return fecha

FECHA_MINIMA = date(2026, 9, 1)

def leer_rango_fechas(parametros, nombre_desde="desde", nombre_hasta="hasta",
                      permitir_futuro=False, fecha_minima=FECHA_MINIMA):
    hoy = timezone.localdate()
    errores = []

    desde = _leer_fecha(parametros.get(nombre_desde), "inicial", errores)
    hasta = _leer_fecha(parametros.get(nombre_hasta), "final", errores)

    if not permitir_futuro:
        if desde and desde > hoy:
            errores.append("La fecha inicial no puede ser futura.")
            desde = None
        if hasta and hasta > hoy:
            errores.append("La fecha final no puede ser futura.")
            hasta = None

    if fecha_minima:
        if desde and desde < fecha_minima:
            errores.append(f"La fecha inicial no puede ser anterior a {fecha_minima.isoformat()}.")
            desde = None
        if hasta and hasta < fecha_minima:
            errores.append(f"La fecha final no puede ser anterior a {fecha_minima.isoformat()}.")
            hasta = None

    if desde and hasta and desde > hasta:
        errores.append("La fecha inicial no puede ser posterior a la final.")
        desde = hasta = None

    return RangoFechas(
        desde=desde,
        hasta=hasta,
        hoy=None if permitir_futuro else hoy,
        minima=fecha_minima,
        errores=errores,
    )