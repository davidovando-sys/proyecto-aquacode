import json
from pathlib import Path

import shapely
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from shapely.geometry import mapping, shape

from core.models import Comuna

# Carpeta donde están tus GeoJSON. Si tu carpeta static está dentro de la app,
# cambia esta línea por: Path(settings.BASE_DIR) / 'core' / 'static' / 'data'
ORIGEN = Path(settings.BASE_DIR) / 'static' / 'data'
SALIDA = Path(settings.BASE_DIR) / 'core' / 'data' / 'comunas_simplificado.geojson'


class Command(BaseCommand):
    help = "Fusiona y simplifica los GeoJSON de comunas en un solo archivo."

    def handle(self, *args, **opts):
        if not ORIGEN.exists():
            raise CommandError(f"No existe la carpeta {ORIGEN}")

        features = {}
        for ruta in sorted(list(ORIGEN.glob('*.geojson')) + list(ORIGEN.glob('*.json'))):
            try:
                datos = json.loads(ruta.read_text(encoding='utf-8'))
            except ValueError:
                continue
            if not isinstance(datos, dict) or datos.get('type') != 'FeatureCollection':
                self.stdout.write(f"Omitido (no es un GeoJSON): {ruta.name}")
                continue

            for f in datos['features']:
                codigo = str(f['properties']['codigo']).zfill(5)
                geom = shape(f['geometry'])
                if not geom.is_valid:
                    geom = geom.buffer(0)
                geom = geom.simplify(0.0005, preserve_topology=True)  
                geom = shapely.set_precision(geom, 1e-5)
                if codigo in features:
                    self.stdout.write(f"Código repetido (se usa el último): {codigo}")
                features[codigo] = {
                    'type': 'Feature',
                    'properties': {'codigo': codigo},
                    'geometry': mapping(geom),
                }
            self.stdout.write(f"Leído {ruta.name}")

        if not features:
            raise CommandError(f"No se encontraron polígonos en {ORIGEN}")

        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        SALIDA.write_text(
            json.dumps({'type': 'FeatureCollection', 'features': list(features.values())},
                       separators=(',', ':')),
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(
            f"{len(features)} polígonos guardados en {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)"
        ))

        faltan = set(Comuna.objects.values_list('codigo', flat=True)) - set(features)
        if faltan:
            self.stdout.write(self.style.WARNING(
                f"Comunas del catálogo SIN polígono ({len(faltan)}): {sorted(faltan)}"
            ))