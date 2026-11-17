from django.conf import settings
from django.db import models


class IntentoInicioSesion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intentos_inicio_sesion_fallidos',
    )
    identificador = models.CharField(
        max_length=150,
        help_text='Correo o nombre de usuario ingresado en el formulario.',
    )
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'intento fallido de inicio de sesión'
        verbose_name_plural = 'intentos fallidos de inicio de sesión'
        indexes = [
            models.Index(fields=['identificador', 'fecha'], name='intento_ident_fecha_idx'),
            models.Index(fields=['usuario', 'fecha'], name='intento_usuario_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.identificador} - {self.fecha:%d/%m/%Y %H:%M}'

    
class ControlAcceso(models.Model):
    username = models.CharField(max_length=150, unique=True, verbose_name="Nombre de usuario o correo")
    intentos_fallidos = models.IntegerField(default=0, verbose_name="Intentos fallidos")
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, verbose_name="Bloqueado hasta")

    def __str__(self):
        return f"{self.username} - Fallos: {self.intentos_fallidos}"
