import json
import unicodedata
from pathlib import Path
from django.db import migrations


def normalizar(valor):
    return ''.join(c for c in unicodedata.normalize('NFD', valor or '')
                   if not unicodedata.combining(c)).casefold().strip()


def cargar(apps, schema_editor):
    alias = schema_editor.connection.alias
    Comuna = apps.get_model('core', 'Comuna')
    datos = json.loads((Path(__file__).resolve().parents[1] / 'data/comunas.json').read_text(encoding='utf-8'))
    Comuna.objects.using(alias).bulk_create([Comuna(**c) for c in datos], ignore_conflicts=True)
    por_nombre = {}
    for c in datos:
        por_nombre.setdefault(normalizar(c['nombre']), []).append(c['codigo'])
    for app, modelo, texto, relacion in [
        ('core', 'SolicitudRegistro', 'comuna', 'comuna_catalogo_id'),
        ('formularios', 'Medicion', 'ubicacion', 'comuna_id'),
    ]:
        Modelo = apps.get_model(app, modelo)
        for registro in Modelo.objects.using(alias).all().iterator():
            candidatos = por_nombre.get(normalizar(getattr(registro, texto)), [])
            if len(candidatos) == 1:
                Modelo.objects.using(alias).filter(pk=registro.pk).update(**{relacion: candidatos[0]})
    if schema_editor.connection.vendor == 'postgresql':
        # Django accede como propietario; no exponemos el catálogo por la Data API.
        schema_editor.execute('ALTER TABLE core_comuna ENABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [('core', '0011_comuna_solicitudregistro_comuna_catalogo'),
                    ('formularios', '0007_medicion_comuna')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
