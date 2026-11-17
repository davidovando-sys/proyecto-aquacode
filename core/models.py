from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

class Comuna(models.Model):
    codigo = models.CharField(primary_key=True, max_length=5)
    nombre = models.CharField(max_length=100)
    codigo_region = models.CharField(max_length=2, db_index=True)
    region = models.CharField(max_length=100)

    class Meta:
        ordering = ['nombre', 'codigo']

    def __str__(self):
        return f'{self.nombre} — {self.region}'


class SolicitudRegistro(models.Model):
    MOTIVOS_RECHAZO = [
        ('datos_incompletos', 'Datos incompletos o inconsistentes'),
        ('correo_no_verificable', 'Correo electrónico no verificable'),
        ('comuna_fuera_cobertura', 'Comuna fuera de la cobertura del proyecto'),
        ('motivo_insuficiente', 'El motivo de la solicitud no es suficiente'),
        ('solicitud_duplicada', 'Solicitud duplicada'),
        ('otro', 'Otro (especificar)'),
    ]

    nombre = models.CharField(max_length=150)
    comuna = models.CharField(max_length=100)
    comuna_catalogo = models.ForeignKey(Comuna, null=True, blank=True, on_delete=models.PROTECT)
    email = models.EmailField(unique=True)
    motivo = models.TextField(blank=True, null=True)

    correo_verificado = models.BooleanField(default=False)
    codigo_hash = models.CharField(max_length=128, blank=True)
    codigo_enviado = models.DateTimeField(null=True, blank=True)
    codigo_intentos = models.PositiveSmallIntegerField(default=0)
    aprobado = models.BooleanField(default=False)
    rechazado = models.BooleanField(default=False)
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.CharField(max_length=30, choices=MOTIVOS_RECHAZO, blank=True)
    detalle_rechazo = models.TextField(max_length=500, blank=True)
    bloqueado = models.BooleanField(default=False)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, verbose_name="Bloqueado hasta")

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.aprobado:
            estado = "Aprobado"
        elif self.rechazado:
            estado = "Rechazado"
        else:
            estado = "Pendiente"
        return f"{self.nombre} - {self.comuna} ({estado})"

    def save(self, *args, **kwargs):
        if self.aprobado and not User.objects.filter(email=self.email).exists():
            nuevo_usuario = User.objects.create_user(
                username=self.email, 
                email=self.email,
                password='AquaCivis2026*' 
            )
            nuevo_usuario.first_name = self.nombre
            nuevo_usuario.save()

        super().save(*args, **kwargs)

# Historial de bloqueos de usuarios
class HistorialBloqueo(models.Model):
    solicitud = models.ForeignKey(
        SolicitudRegistro,
        on_delete=models.CASCADE,
        related_name='historial_bloqueos'
    )

    administrador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    motivo = models.TextField()

    fecha_bloqueo = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.solicitud.nombre} - {self.fecha_bloqueo}"

    class Meta:
        ordering = ['-fecha_bloqueo']

class RecordatorioMedicion(models.Model):
    RECORDATORIO_1_DIA = 1
    RECORDATORIO_7_DIAS = 7
    DIAS_CHOICES = [
        (RECORDATORIO_1_DIA, 'Primer recordatorio (1 día)'),
        (RECORDATORIO_7_DIAS, 'Segundo recordatorio (7 días)'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recordatorios_medicion',
    )
    dias_sin_medicion = models.PositiveSmallIntegerField(choices=DIAS_CHOICES)
    fecha_referencia = models.DateTimeField(
        help_text='Fecha de la última medición o de creación de la cuenta.',
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_envio']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'dias_sin_medicion', 'fecha_referencia'],
                name='recordatorio_unico_por_ciclo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['usuario', 'fecha_referencia'],
                name='recordatorio_usuario_ciclo_idx',
            ),
        ]

    def __str__(self):
        return f'{self.usuario} - {self.dias_sin_medicion} día(s)'


class ConfiguracionAlerta(models.Model):
    ph_minimo_normal = models.FloatField(default=6.5, verbose_name="pH mínimo normal")
    ph_maximo_normal = models.FloatField(default=8.5, verbose_name="pH máximo normal")
    ph_minimo_critico = models.FloatField(default=6.0, verbose_name="pH mínimo crítico")
    ph_maximo_critico = models.FloatField(default=9.0, verbose_name="pH máximo crítico")
    
    conductividad_preventiva = models.FloatField(default=100.0, verbose_name="Conductividad preventiva (mS/cm)")
    conductividad_critica = models.FloatField(default=150.0, verbose_name="Conductividad crítica (mS/cm)")
    
    tds_base = models.FloatField(default=300.0, validators=[MinValueValidator(0)], verbose_name="TDS base temporal (ppm)")
    tds_muestras_minimas = models.IntegerField(default=5, validators=[MinValueValidator(1)], verbose_name="Mínimo de muestras para promediar TDS")
    
    temperatura_preventiva = models.FloatField(default=25.0, verbose_name="Temperatura preventiva (°C)")
    temperatura_critica = models.FloatField(default=35.0, verbose_name="Temperatura crítica (°C)")
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    conductividad_base = models.FloatField(default=0.5, validators=[MinValueValidator(0)], verbose_name="Conductividad base (mS/cm)")
    temperatura_base = models.FloatField(default=15.0, validators=[MinValueValidator(0)], verbose_name="Temperatura base (°C)")

    class Meta:
        verbose_name = "configuración de alertas"
        verbose_name_plural = "configuraciones de alertas"

    def clean(self):
        errores = {}
        if not 0 <= self.ph_minimo_critico < self.ph_minimo_normal:
            errores['ph_minimo_critico'] = "Debe ser menor que el pH mínimo normal."
        if not self.ph_maximo_normal < self.ph_maximo_critico <= 14:
            errores['ph_maximo_critico'] = "Debe ser mayor que el pH máximo normal y no superar 14."
        if self.ph_minimo_normal >= self.ph_maximo_normal:
            errores['ph_maximo_normal'] = "Debe ser mayor que el pH mínimo normal."
        
        # Validación de campos de conductividad y temperatura
        for preventiva, critica in (
            ('conductividad_preventiva', 'conductividad_critica'),
            ('temperatura_preventiva', 'temperatura_critica'),
        ):
            if getattr(self, preventiva) < 0 or getattr(self, critica) <= getattr(self, preventiva):
                errores[critica] = "El nivel crítico debe ser mayor que el preventivo."
        if errores:
            raise ValidationError(errores)

    @classmethod
    def actual(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion

    def __str__(self):
        return "Umbrales generales de AquaCivis"


class ContenidoWeb(models.Model):
    texto_hero = models.CharField(
        max_length=180,
        default="Monitoreo ciudadano de la calidad del agua",
        verbose_name="Texto principal del inicio",
    )
    descripcion_mision = models.TextField(
        default="Acercamos información clara sobre la calidad del agua a cada comunidad.",
        verbose_name="Descripción de la misión",
    )
    mensaje_bienvenida = models.TextField(
        default="Bienvenido a AquaCivis, una plataforma para monitorear y comprender la calidad del agua.",
        verbose_name="Mensaje de bienvenida",
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "contenido web"
        verbose_name_plural = "contenidos web"

    @classmethod
    def actual(cls):
        contenido, _ = cls.objects.get_or_create(pk=1)
        return contenido

    def __str__(self):
        return "Contenido público de AquaCivis"
