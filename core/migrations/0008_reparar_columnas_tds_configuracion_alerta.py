from django.db import migrations


def agregar_columnas_tds_si_faltan(apps, schema_editor):
    """Repara bases creadas antes de que los campos TDS fueran incluidos."""
    ConfiguracionAlerta = apps.get_model('core', 'ConfiguracionAlerta')
    tabla = ConfiguracionAlerta._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columnas_actuales = {
            columna.name
            for columna in schema_editor.connection.introspection.get_table_description(cursor, tabla)
        }

    for nombre_campo in ('tds_preventivo', 'tds_critico'):
        if nombre_campo not in columnas_actuales:
            campo = ConfiguracionAlerta._meta.get_field(nombre_campo)
            schema_editor.add_field(ConfiguracionAlerta, campo)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_recordatoriomedicion'),
    ]

    operations = [
        migrations.RunPython(
            agregar_columnas_tds_si_faltan,
            migrations.RunPython.noop,
        ),
    ]
