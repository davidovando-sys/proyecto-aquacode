from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    

    dependencies = [
        ('usuarios', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IntentoInicioSesion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificador', models.CharField(help_text='Correo o nombre de usuario ingresado en el formulario.', max_length=150)),
                ('direccion_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='intentos_inicio_sesion_fallidos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'intento fallido de inicio de sesión',
                'verbose_name_plural': 'intentos fallidos de inicio de sesión',
                'ordering': ['-fecha'],
            },
        ),
        migrations.AddIndex(
            model_name='intentoiniciosesion',
            index=models.Index(fields=['identificador', 'fecha'], name='intento_ident_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='intentoiniciosesion',
            index=models.Index(fields=['usuario', 'fecha'], name='intento_usuario_fecha_idx'),
        ),
    ]
