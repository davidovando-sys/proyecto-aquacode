from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_solicitudregistro_fecha_rechazo_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionAlerta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ph_minimo_normal', models.FloatField(default=6.5, verbose_name='pH mínimo normal')),
                ('ph_maximo_normal', models.FloatField(default=8.5, verbose_name='pH máximo normal')),
                ('ph_minimo_critico', models.FloatField(default=6.0, verbose_name='pH mínimo crítico')),
                ('ph_maximo_critico', models.FloatField(default=9.0, verbose_name='pH máximo crítico')),
                ('conductividad_preventiva', models.FloatField(default=100.0, verbose_name='Conductividad preventiva (mS/cm)')),
                ('conductividad_critica', models.FloatField(default=150.0, verbose_name='Conductividad crítica (mS/cm)')),
                ('tds_preventivo', models.FloatField(default=1000.0, verbose_name='TDS preventivo (ppm)')),
                ('tds_critico', models.FloatField(default=1500.0, verbose_name='TDS crítico (ppm)')),
                ('temperatura_preventiva', models.FloatField(default=25.0, verbose_name='Temperatura preventiva (°C)')),
                ('temperatura_critica', models.FloatField(default=35.0, verbose_name='Temperatura crítica (°C)')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'configuración de alertas', 'verbose_name_plural': 'configuraciones de alertas'},
        ),
        migrations.CreateModel(
            name='ContenidoWeb',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto_hero', models.CharField(default='Monitoreo ciudadano de la calidad del agua', max_length=180, verbose_name='Texto principal del inicio')),
                ('descripcion_mision', models.TextField(default='Acercamos información clara sobre la calidad del agua a cada comunidad.', verbose_name='Descripción de la misión')),
                ('mensaje_bienvenida', models.TextField(default='Bienvenido a AquaCivis, una plataforma para monitorear y comprender la calidad del agua.', verbose_name='Mensaje de bienvenida')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'contenido web', 'verbose_name_plural': 'contenidos web'},
        ),
    ]
