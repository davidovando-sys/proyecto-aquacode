import json
import random
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from shapely.geometry import Point, shape
from shapely.prepared import prep

ARCHIVO = Path(settings.BASE_DIR) / 'core' / 'data' / 'comunas_simplificado.geojson'


@lru_cache(maxsize=1)
def _poligonos():
    """Carga los polígonos una sola vez por proceso."""
    comunas = {}
    datos = json.loads(ARCHIVO.read_text(encoding='utf-8'))
    for f in datos['features']:
        geom = shape(f['geometry'])
        partes = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        comunas[f['properties']['codigo']] = {
            'partes': partes,
            'preparadas': [prep(p) for p in partes],
            'areas': [p.area for p in partes],
        }
    return comunas


def punto_en_comuna(codigo, semilla):
    """(lat, lng) estable dentro de la comuna, o None si no hay polígono."""
    datos = _poligonos().get(str(codigo).zfill(5))
    if not datos:
        return None

    rng = random.Random(f"medicion-{semilla}")  # misma medición = mismo punto siempre
    i = rng.choices(range(len(datos['partes'])), weights=datos['areas'])[0]
    parte, preparada = datos['partes'][i], datos['preparadas'][i]

    minx, miny, maxx, maxy = parte.bounds
    for _ in range(200):
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if preparada.contains(Point(x, y)):
            return y, x  

    p = parte.representative_point()  # respaldo para polígonos muy delgados
    return p.y, p.x