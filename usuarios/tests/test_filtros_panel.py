from django.test import TestCase
from django.urls import reverse

from usuarios.tests import crear_cuenta


class FiltrosPanelTests(TestCase):
    def setUp(self):
        admin, _ = crear_cuenta('admin@panel.cl', staff=True)
        self.client.force_login(admin)
        _, self.activo = crear_cuenta('activo@panel.cl')
        _, self.bloqueado = crear_cuenta('bloqueado@panel.cl', activo=False)
        self.bloqueado.bloqueado = True
        self.bloqueado.save()
        _, self.inactivo = crear_cuenta('inactivo@panel.cl', activo=False)
        _, self.pendiente = crear_cuenta('pendiente@panel.cl', activo=False, aprobado=False)
        crear_cuenta('noverificado@panel.cl', aprobado=False, verificado=False)
        _, rechazado = crear_cuenta('rechazado@panel.cl', aprobado=False)
        rechazado.rechazado = True
        rechazado.save()

    def test_filtra_y_conserva_contadores_globales(self):
        casos = {
            'todos': {self.activo.pk, self.bloqueado.pk, self.inactivo.pk, self.pendiente.pk},
            'activos': {self.activo.pk},
            'bloqueados': {self.bloqueado.pk},
            'pendientes': {self.pendiente.pk},
        }
        for estado, esperados in casos.items():
            with self.subTest(estado=estado):
                response = self.client.get(reverse('dashboard_admin'), {'estado': estado})
                self.assertEqual({f['solicitud'].pk for f in response.context['filas']}, esperados)
                self.assertEqual(response.context['total_usuarios'], 4)
                for clave in ('total_activos', 'total_bloqueados', 'total_pendientes'):
                    self.assertEqual(response.context[clave], 1)
                self.assertContains(response, 'aria-current="true"', count=1)

    def test_paginacion_conserva_estado_y_filtra_antes_de_paginar(self):
        for i in range(11):
            crear_cuenta(f'pendiente{i}@panel.cl', aprobado=False, activo=False)
        response = self.client.get(reverse('dashboard_admin'), {'estado': 'pendientes'})
        self.assertEqual(len(response.context['filas']), 10)
        self.assertEqual(response.context['pagina_obj'].paginator.count, 12)
        self.assertContains(response, '?estado=pendientes&amp;page=2')
        response = self.client.get(reverse('dashboard_admin'), {'estado': 'pendientes', 'page': 2})
        self.assertEqual(len(response.context['filas']), 2)
        self.assertTrue(all(not f['solicitud'].aprobado for f in response.context['filas']))

    def test_estado_desconocido_muestra_todos(self):
        response = self.client.get(reverse('dashboard_admin'), {'estado': 'desconocido'})
        self.assertEqual(response.context['estado_seleccionado'], 'todos')
        self.assertEqual(len(response.context['filas']), 4)

    def test_estado_vacio_muestra_mensaje(self):
        self.pendiente.delete()
        response = self.client.get(reverse('dashboard_admin'), {'estado': 'pendientes'})
        self.assertContains(response, 'No hay resultados')
        self.assertEqual(len(response.context['filas']), 0)
