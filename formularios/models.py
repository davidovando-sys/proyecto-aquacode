from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class Medicion(models.Model):
    BLOQUES_HORARIOS = [
        ('Mañana', 'Mañana (08:00-12:00)'),
        ('Día', 'Día (12:00-16:00)'),
        ('Noche', 'Noche (16:00-20:00)'),
    ]

    ORIGENES_UBICACION = [
    ('gps', 'GPS'),
    ('pin_manual', 'Pin ajustado manualmente'),
    ('comuna_seleccionada', 'Comuna elegida (distinta a la ubicación actual)'),
    ]

    ph = models.FloatField(validators=[MinValueValidator(0.01), MaxValueValidator(14.00)], verbose_name="pH")
    conductividad = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(200.0)], verbose_name="Conductividad (mS/cm)")
    tds = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(9990.0)], verbose_name="TDS (ppm)")
    temperatura = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(80.0)], verbose_name="Temperatura (°C)")
    
    ubicacion = models.CharField(max_length=200, verbose_name="Ubicación (Comuna/Zona)")
    comuna = models.ForeignKey('core.Comuna', null=True, blank=True, on_delete=models.PROTECT)
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    alerta_general = models.CharField(max_length=20, default="Gris", verbose_name="Nivel de Alerta")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Registrado por")

    # NUEVO: Bloque horario
    bloque_horario = models.CharField(max_length=20, choices=BLOQUES_HORARIOS, default='Mañana', verbose_name="Bloque Horario")

    # Coordenadas GPS exactas
    latitud = models.FloatField(null=True, blank=True, verbose_name="Latitud")
    longitud = models.FloatField(null=True, blank=True, verbose_name="Longitud")

    origen_ubicacion = models.CharField(max_length=20, choices=ORIGENES_UBICACION, default='gps',verbose_name="Origen de la ubicación",)

    def __str__(self):
        return f"{self.ubicacion} - {self.bloque_horario} - {self.alerta_general}"
    
#Esto permitirá al admin editar la configuración de los parámetros y la información
class ConfiguracionParametro(models.Model):
    PARAMETRO_CHOICES = [
        ('ph', 'pH'),
        ('conductividad', 'Conductividad'),
        ('tds', 'Sólidos Disueltos (TDS)'),
        ('temperatura', 'Temperatura'),
    ]
    nombre_parametro = models.CharField(max_length=20, choices=PARAMETRO_CHOICES, unique=True)
    valor_min = models.FloatField()
    valor_max = models.FloatField()
    texto_informativo = models.TextField()

    def __str__(self):
        return self.get_nombre_parametro_display()
