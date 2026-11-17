# Registro con código de correo

1. El usuario completa el registro y recibe un código de 4 números.
2. Ingresa el código en la app y pulsa «Verificar y enviar solicitud».
3. Solo entonces aparece en la bandeja del administrador.
4. El administrador aprueba o rechaza; la cuenta permanece inactiva hasta aprobarla.

Los códigos vencen a los 10 minutos, permiten hasta 5 intentos y se guardan como hash. El usuario puede pedir otro código después de 60 segundos; el anterior deja de servir. No se usan enlaces ni una pantalla adicional de aceptación.

## Configuración del responsable de AquaCivis

El envío SMTP sigue siendo necesario para entregar los códigos. Los usuarios que se registran no configuran Gmail ni generan contraseñas de aplicación.

Configura EMAIL_HOST=smtp-relay.brevo.com (sujeto a cambios), EMAIL_PORT=587, EMAIL_USE_TLS=true, EMAIL_USE_SSL=false, EMAIL_HOST_USER con la dirección remitente, EMAIL_HOST_PASSWORD con su clave SMTP y DEFAULT_FROM_EMAIL con la misma dirección. Se leen desde variables de entorno; NUNCA EXPONER CREDENCIALES en el repositorio.

Antes de iniciar el servidor aplica las migraciones:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

La migración 0007 agrega la confirmación y la 0008 almacena el hash, fecha e intentos del código. No se modifican las cuentas aprobadas existentes.

Si falla el envío inicial, se conserva el registro inactivo y se abre la pantalla de código, indicando que todavía no se envió. Se puede reintentar desde esa pantalla. Volver a registrar el mismo correo y contraseña permite retomar la verificación sin duplicar la solicitud. Un fallo al reenviar conserva el código anterior. La verificación se completa en el mismo navegador del registro.

Pruebas locales con base temporal y correo en memoria:

```powershell
.\venv\Scripts\python.exe manage.py test core --settings=aquacode_backend.test_settings
```
