from django import forms
from .validadores import *
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import ConfiguracionAlerta, ContenidoWeb, SolicitudRegistro


class FormularioConEstilo(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs['class'] = 'form-control'


class ConfiguracionAlertaForm(FormularioConEstilo):
    class Meta:
        model = ConfiguracionAlerta
        exclude = ('fecha_actualizacion',)
        widgets = {
            campo: forms.NumberInput(attrs={'step': '0.01'})
            for campo in (
                'ph_minimo_normal', 'ph_maximo_normal', 'ph_minimo_critico',
                'ph_maximo_critico', 'conductividad_preventiva',
                'conductividad_critica', 'temperatura_preventiva', 
                'temperatura_critica', 'tds_base'
            )
        }


class ContenidoWebForm(FormularioConEstilo):
    class Meta:
        model = ContenidoWeb
        exclude = ('fecha_actualizacion',)
        widgets = {
            'texto_hero': forms.TextInput(attrs={'maxlength': 180}),
            'descripcion_mision': forms.Textarea(attrs={'rows': 4}),
            'mensaje_bienvenida': forms.Textarea(attrs={'rows': 4}),
        }


class EditarUsuarioForm(forms.Form):
    ROLES = (
        ('monitor', 'Monitor'),
        ('administrador', 'Administrador'),
    )

    nombre = forms.CharField(max_length=150, label='Nombre completo')
    email = forms.EmailField(label='Correo electrónico')
    comuna = forms.CharField(max_length=100, label='Comuna')
    rol = forms.ChoiceField(choices=ROLES, label='Rol y permisos')
    activo = forms.BooleanField(required=False, label='Cuenta activa')

    def clean_comuna(self):
        from .comunas import exigir_comuna
        valor = self.cleaned_data['comuna']
        if valor == 'Administración' and self.solicitud.comuna == valor:
            self.comuna_catalogo = None
            return valor
        codigo = (self.data.get('comuna_codigo') or '').strip()
        try:
            self.comuna_catalogo = exigir_comuna(codigo or valor)
        except ValueError as error:
            raise forms.ValidationError(str(error))
        return self.comuna_catalogo.nombre
    
    def clean_nombre(self):
        nombre = normalizar_nombre(self.cleaned_data.get('nombre'))
        validar_nombre(nombre)
        return nombre

    def __init__(self, *args, solicitud, usuario, administrador, **kwargs):
        self.solicitud = solicitud
        self.usuario = usuario
        self.administrador = administrador
        inicial = kwargs.setdefault('initial', {})
        inicial.update({
            'nombre': usuario.first_name or solicitud.nombre,
            'email': usuario.email or solicitud.email,
            'comuna': solicitud.comuna,
            'rol': 'administrador' if usuario.is_staff else 'monitor',
            'activo': usuario.is_active,
        })
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            if nombre == 'activo':
                clase='form-check-input'
            elif isinstance(campo.widget, forms.Select):
                clase='form-select'
            else:
                clase='form-control'
            campo.widget.attrs['class'] = clase
        # El rol se bloquea si te editas a ti mismo, o si editas a otro admin sin ser superadmin.
        es_propia_cuenta = usuario.pk == administrador.pk
        es_admin_ajeno = usuario.is_staff and not administrador.is_superuser
        if es_propia_cuenta or es_admin_ajeno:
            self.fields['rol'].disabled = True
            self.fields['rol'].help_text = (
                'No puedes cambiar tu propio rol.' if es_propia_cuenta
                else 'Solo un superadministrador puede cambiar el rol de otro administrador.'
            )
        self.fields['activo'].disabled = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        usuarios = User.objects.exclude(pk=self.usuario.pk)
        if usuarios.filter(email__iexact=email).exists() or usuarios.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        if SolicitudRegistro.objects.exclude(pk=self.solicitud.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una solicitud con este correo.')
        return email

    def clean(self):
        datos = super().clean()
        pierde_acceso_admin = datos.get('rol') != 'administrador' or not datos.get('activo')
        if self.usuario.is_superuser and pierde_acceso_admin:
            raise forms.ValidationError('Una cuenta principal no puede desactivarse ni cambiarse a Monitor desde este panel.')
        if self.usuario == self.administrador and pierde_acceso_admin:
            raise forms.ValidationError('No puedes quitarte tu propio acceso de administrador.')
        if self.usuario.is_staff and self.usuario.is_active and pierde_acceso_admin:
            existen_otros = User.objects.filter(is_staff=True, is_active=True).exclude(pk=self.usuario.pk).exists()
            if not existen_otros:
                raise forms.ValidationError('Debe permanecer al menos un administrador activo.')
        return datos

class CrearAdministradorForm(forms.Form):
    nombre = forms.CharField(max_length=150, label='Nombre completo')
    comuna = forms.CharField(max_length=100, label='Comuna de monitoreo')
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña inicial')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Repetir contraseña')

    def clean_nombre(self):
        nombre = normalizar_nombre(self.cleaned_data.get('nombre'))
        validar_nombre(nombre)
        return nombre

    def clean_password(self):
        password = self.cleaned_data.get('password')
        validar_password(password)
        return password

    def clean_comuna(self):
        from .comunas import exigir_comuna
        try:
            self.comuna_catalogo = exigir_comuna(self.cleaned_data['comuna'])
        except ValueError as error:
            raise forms.ValidationError(str(error))
        return self.comuna_catalogo.nombre

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        if SolicitudRegistro.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una solicitud con este correo.')
        return email

    def clean(self):
        datos = super().clean()
        password = datos.get('password')
        password2 = datos.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return datos
