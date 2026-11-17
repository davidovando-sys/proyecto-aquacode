from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from core.models import HistorialBloqueo,SolicitudRegistro

CLAVE = 'Clave-Segura-123'


def crear_cuenta(email, nombre='Usuario Prueba', staff=False, activo=True, aprobado=True, verificado=True):
    usuario = User.objects.create_user(
        username=email, email=email, password=CLAVE,
        first_name=nombre, is_staff=staff, is_active=activo,
    )
    solicitud = SolicitudRegistro.objects.create(
        nombre=nombre, comuna='Santiago', email=email, aprobado=aprobado, correo_verificado=verificado,
    )
    return usuario, solicitud


class ControlDeAccesoTests(TestCase):
    #Tarea Jira CIA-50: acceso por role
    RUTAS_ADMIN = ('dashboard_admin', 'crear_admin')

    def setUp(self):
        self.admin, _ = crear_cuenta('admin@test.cl', staff=True)
        self.monitor, _ = crear_cuenta('monitor@test.cl')

    def test_visitante_es_enviado_al_login(self):
        for nombre in self.RUTAS_ADMIN + ('medicion',):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertTrue(respuesta.url.startswith(reverse('login')), nombre)

    def test_monitor_no_entra_a_rutas_de_administracion(self):
        self.client.force_login(self.monitor)
        for nombre in self.RUTAS_ADMIN:
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertTrue(respuesta.url.startswith(reverse('login')), nombre)

    def test_monitor_si_entra_al_formulario_de_mediciones(self):
        self.client.force_login(self.monitor)
        self.assertEqual(self.client.get(reverse('medicion')).status_code, 200)

    def test_administrador_entra_a_todas_las_rutas(self):
        self.client.force_login(self.admin)
        for nombre in self.RUTAS_ADMIN + ('medicion',):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)


class AprobarRechazarTests(TestCase):
    #Tarea Jira CIA-60,75 y 82:aprobar o rechazar solicitudes y avisar por correo

    def setUp(self):
        admin, _ = crear_cuenta('admin@test.cl', staff=True)
        self.client.force_login(admin)
        _, self.pendiente = crear_cuenta('pendiente@test.cl', 'Pendiente', activo=False, aprobado=False)

    def test_aprobar_activa_la_cuenta_y_avisa_por_correo(self):
        self.client.post(reverse('aprobar_solicitud', args=[self.pendiente.id]))
        self.pendiente.refresh_from_db()
        self.assertTrue(self.pendiente.aprobado)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['pendiente@test.cl'])
        self.assertTrue(Client().login(username='pendiente@test.cl', password=CLAVE))

    def test_rechazar_guarda_el_motivo_y_lo_incluye_en_el_correo(self):
        self.client.post(reverse('rechazar_solicitud', args=[self.pendiente.id]), {
            'motivo_rechazo': 'otro',
            'detalle_rechazo': 'No pertenece a la zona de monitoreo',
        })
        self.pendiente.refresh_from_db()
        self.assertTrue(self.pendiente.rechazado)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('No pertenece a la zona de monitoreo', mail.outbox[0].body)
        self.assertFalse(Client().login(username='pendiente@test.cl', password=CLAVE))

    def test_rechazar_sin_motivo_no_cambia_nada_ni_envia_correo(self):
        self.client.post(reverse('rechazar_solicitud', args=[self.pendiente.id]), {})
        self.pendiente.refresh_from_db()
        self.assertFalse(self.pendiente.rechazado)
        self.assertEqual(len(mail.outbox), 0)

    def test_motivo_otro_exige_detalle(self):
        self.client.post(reverse('rechazar_solicitud', args=[self.pendiente.id]),
                         {'motivo_rechazo': 'otro', 'detalle_rechazo': ''})
        self.pendiente.refresh_from_db()
        self.assertFalse(self.pendiente.rechazado)
        self.assertEqual(len(mail.outbox), 0)

    def test_aprobar_solo_acepta_post(self):
        respuesta = self.client.get(reverse('aprobar_solicitud', args=[self.pendiente.id]))
        self.assertEqual(respuesta.status_code, 405)

    def test_no_se_aprueba_una_solicitud_sin_correo_verificado(self):
        _, sin_verificar = crear_cuenta('sin-verificar@test.cl', activo=False, aprobado=False, verificado=False)
        self.client.post(reverse('aprobar_solicitud', args=[sin_verificar.id]))
        sin_verificar.refresh_from_db()
        self.assertFalse(sin_verificar.aprobado)
        self.assertEqual(len(mail.outbox), 0)

    def test_el_panel_solo_lista_solicitudes_con_correo_verificado(self):
        crear_cuenta('sin-verificar@test.cl', activo=False, aprobado=False, verificado=False)
        filas = self.client.get(reverse('dashboard_admin')).context['filas']
        correos = [fila['solicitud'].email for fila in filas]
        self.assertIn('pendiente@test.cl', correos)
        self.assertNotIn('sin-verificar@test.cl', correos)

class BloqueoDeUsuariosTests(TestCase):
    #Tarea del Jira CIA-42:bloquear, desbloquear y eliminar cuentas

    def setUp(self):
        self.admin, self.sol_admin = crear_cuenta('admin@test.cl', staff=True)
        self.monitor, self.sol_monitor = crear_cuenta('monitor@test.cl')
        self.client.force_login(self.admin)

    def test_bloquear_impide_iniciar_sesion(self):
        self.client.post(reverse('bloquear_usuario', args=[self.sol_monitor.id]))
        self.sol_monitor.refresh_from_db()
        self.assertTrue(self.sol_monitor.bloqueado)
        self.assertFalse(Client().login(username='monitor@test.cl', password=CLAVE))

    def test_desbloquear_devuelve_el_acceso(self):
        self.client.post(reverse('bloquear_usuario', args=[self.sol_monitor.id]))
        self.client.post(reverse('desbloquear_usuario', args=[self.sol_monitor.id]))
        self.assertTrue(Client().login(username='monitor@test.cl', password=CLAVE))

    def test_el_administrador_no_puede_bloquearse_a_si_mismo(self):
        self.client.post(reverse('bloquear_usuario', args=[self.sol_admin.id]))
        self.sol_admin.refresh_from_db()
        self.assertFalse(self.sol_admin.bloqueado)

    def test_eliminar_borra_cuenta_y_solicitud(self):
        self.client.post(reverse('eliminar_usuario', args=[self.sol_monitor.id]))
        self.assertFalse(User.objects.filter(email='monitor@test.cl').exists())
        self.assertFalse(SolicitudRegistro.objects.filter(email='monitor@test.cl').exists())

    def test_el_administrador_no_puede_eliminarse_a_si_mismo(self):
        self.client.post(reverse('eliminar_usuario', args=[self.sol_admin.id]))
        self.assertTrue(User.objects.filter(email='admin@test.cl').exists())

    def test_bloquear_registra_el_motivo_en_el_historial(self):
        self.client.post(reverse('bloquear_usuario', args=[self.sol_monitor.id]), {'motivo_bloqueo': 'Uso indebido'})
        registro = HistorialBloqueo.objects.get()
        self.assertEqual(registro.motivo, 'Uso indebido')
        self.assertEqual(registro.administrador, self.admin)

    def test_bloquear_sin_motivo_usa_el_motivo_por_defecto(self):
        self.client.post(reverse('bloquear_usuario', args=[self.sol_monitor.id]))
        self.assertEqual(HistorialBloqueo.objects.get().motivo, 'Bloqueo realizado por administrador')

    def test_desactivar_desde_editar_exige_un_motivo(self):
        url = reverse('editar_usuario', args=[self.sol_monitor.id])
        datos = {'nombre': 'Usuario Prueba', 'email': 'monitor@test.cl', 'comuna': 'Santiago', 'rol': 'monitor'}
        self.client.post(url, datos)  # sin "activo" se intenta desactivar, pero falta el motivo
        self.assertTrue(User.objects.get(email='monitor@test.cl').is_active)
        self.assertEqual(HistorialBloqueo.objects.count(), 0)
        self.client.post(url, {**datos, 'motivo_bloqueo': 'Spam'})
        self.assertFalse(User.objects.get(email='monitor@test.cl').is_active)
        self.assertEqual(HistorialBloqueo.objects.get().motivo, 'Spam')


class CrearAdministradorTests(TestCase):
    #Tarea del Jira CIA-87: un administrador crea cuentas de administrador

    def setUp(self):
        admin, _ = crear_cuenta('admin@test.cl', staff=True)
        self.client.force_login(admin)

    def datos(self, **cambios):
        datos = {'nombre': 'Nuevo Admin', 'email': 'nuevo@test.cl', 'password': CLAVE, 'password2': CLAVE}
        datos.update(cambios)
        return datos

    def test_crea_un_administrador_que_puede_iniciar_sesion(self):
        self.client.post(reverse('crear_admin'), self.datos(email='Nuevo@Test.cl'))
        nuevo = User.objects.get(email='nuevo@test.cl')  # el correo se guarda en minúsculas
        self.assertTrue(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertTrue(SolicitudRegistro.objects.get(email='nuevo@test.cl').aprobado)
        self.assertTrue(Client().login(username='nuevo@test.cl', password=CLAVE))

    def test_correo_repetido_con_otra_capitalizacion_se_rechaza(self):
        respuesta = self.client.post(reverse('crear_admin'), self.datos(email='ADMIN@test.cl'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact='admin@test.cl').count(), 1)

    def test_contrasenas_distintas_o_debiles_se_rechazan(self):
        for cambios in ({'password2': 'otra-clave'}, {'password': '12345678', 'password2': '12345678'}):
            respuesta = self.client.post(reverse('crear_admin'), self.datos(**cambios))
            self.assertEqual(respuesta.status_code, 200)
            self.assertFalse(User.objects.filter(email='nuevo@test.cl').exists())

    def test_un_monitor_no_puede_crear_administradores(self):
        monitor, _ = crear_cuenta('monitor@test.cl')
        self.client.force_login(monitor)
        self.client.post(reverse('crear_admin'), self.datos())
        self.assertFalse(User.objects.filter(email='nuevo@test.cl').exists())


from usuarios.models import IntentoInicioSesion

class IntentoInicioSesionTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='monitor@example.com',
            email='monitor@example.com',
            password='ClaveSegura123!',
        )

    def test_registra_un_intento_cuando_la_contrasena_es_incorrecta(self):
        self.client.post(
            reverse('login'),
            {'username': self.usuario.username, 'password': 'clave-incorrecta'},
            REMOTE_ADDR='127.0.0.1',
        )

        intento = IntentoInicioSesion.objects.get()
        self.assertEqual(intento.usuario, self.usuario)
        self.assertEqual(intento.identificador, self.usuario.username)
        self.assertEqual(intento.direccion_ip, '127.0.0.1')

    def test_no_registra_un_intento_cuando_el_inicio_de_sesion_es_correcto(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.usuario.username, 'password': 'ClaveSegura123!'},
        )

        self.assertRedirects(response, reverse('home'))
        self.assertFalse(IntentoInicioSesion.objects.exists())
