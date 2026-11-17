from django.urls import path
from django.contrib.auth import views as auth_views
from .views import autenticacion_views, panel_views, verificacion_views

urlpatterns = [
    path('verificar-correo/', verificacion_views.verificar_correo_view, name='verificar_correo'),
    path('login/', autenticacion_views.login_view, name='login'),
    path('logout/', autenticacion_views.logout_view, name='logout'),
    path('solicitar-registro/', autenticacion_views.solicitar_registro_view, name='solicitar_registro'),

    # Recuperación de contraseña por correo
    path(
        'recuperar-password/',
        auth_views.PasswordResetView.as_view(
            template_name='recuperar_password.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'recuperar-password/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'recuperar-password/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html',
        ),
        name='password_reset_confirm',
    ),
    path(
        'recuperar-password/completo/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # Rutas existentes de administración
    path('dashboard/', panel_views.dashboard_admin_view, name='dashboard_admin'),
    path('dashboard/usuarios/nuevo-administrador/', panel_views.crear_administrador_view, name='crear_admin'),
    path('dashboard/aprobar/<int:solicitud_id>/', panel_views.aprobar_solicitud_view, name='aprobar_solicitud'),
    path('dashboard/rechazar/<int:solicitud_id>/', panel_views.rechazar_solicitud_view, name='rechazar_solicitud'),
    path('dashboard/eliminar/<int:solicitud_id>/', panel_views.eliminar_usuario_view, name='eliminar_usuario'),
    path('dashboard/bloquear/<int:solicitud_id>/', panel_views.bloquear_usuario_view, name='bloquear_usuario'),
    path('dashboard/desbloquear/<int:solicitud_id>/', panel_views.desbloquear_usuario_view, name='desbloquear_usuario'),
    path('dashboard/usuarios/<int:solicitud_id>/editar/', panel_views.editar_usuario_view, name='editar_usuario'),
    path('usuarios/<int:solicitud_id>/', panel_views.ver_usuario_view, name='ver_usuario'),

]