from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_configuracionalerta_conductividad_base_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordatorioMedicion',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'dias_sin_medicion',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, 'Primer recordatorio (1 día)'),
                            (7, 'Segundo recordatorio (7 días)'),
                        ],
                    ),
                ),
                (
                    'fecha_referencia',
                    models.DateTimeField(
                        help_text='Fecha de la última medición o de creación de la cuenta.',
                    ),
                ),
                ('fecha_envio', models.DateTimeField(auto_now_add=True)),
                (
                    'usuario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recordatorios_medicion',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-fecha_envio'],
                'indexes': [
                    models.Index(
                        fields=['usuario', 'fecha_referencia'],
                        name='recordatorio_usuario_ciclo_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('usuario', 'dias_sin_medicion', 'fecha_referencia'),
                        name='recordatorio_unico_por_ciclo',
                    ),
                ],
            },
        ),
    ]
