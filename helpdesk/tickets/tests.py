import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    ArticuloBaseConocimiento,
    Perfil,
    Ticket,
    TicketAdjunto,
    TicketHistorial,
    TicketMensaje,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="helpdesk@test.local",
    MEDIA_ROOT=tempfile.gettempdir(),
)
class TicketViewsTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="ana",
            password="claveSegura123",
            first_name="Ana",
            last_name="Perez",
            email="ana@test.local",
        )
        self.sistemas = User.objects.create_user(
            username="soporte",
            password="claveSegura123",
            first_name="Mesa",
            last_name="Ayuda",
            email="soporte@test.local",
        )
        self.sistemas.perfil.rol = Perfil.Rol.SISTEMAS
        self.sistemas.perfil.save(update_fields=["rol"])
        self.articulo = ArticuloBaseConocimiento.objects.create(
            titulo="Problemas con VPN",
            resumen="Pasos basicos para reconectar la VPN.",
            contenido="Reinicia el cliente, valida credenciales y prueba nuevamente.",
        )

    def crear_ticket(self, **kwargs):
        data = {
            "asunto": "Error de acceso",
            "usuario": "Ana Perez",
            "creado_por": self.usuario,
            "descripcion": "No puedo iniciar sesion.",
            "categoria": Ticket.Categoria.ACCESO,
            "prioridad": Ticket.Prioridad.MEDIA,
        }
        data.update(kwargs)
        return Ticket.objects.create(**data)

    def test_login_muestra_la_pagina(self):
        response = self.client.get(reverse("tickets:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesion")

    def test_usuario_puede_crear_un_ticket_y_se_envia_correo(self):
        self.client.login(username="ana", password="claveSegura123")
        response = self.client.post(
            reverse("tickets:index"),
            {
                "asunto": "Error de acceso",
                "categoria": Ticket.Categoria.ACCESO,
                "prioridad": Ticket.Prioridad.ALTA,
                "descripcion": "No puedo iniciar sesion.",
                "vencimiento": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)
        self.assertEqual(ticket.creado_por, self.usuario)
        self.assertEqual(ticket.usuario, "Ana Perez")
        self.assertEqual(ticket.mensajes.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_sistemas_puede_gestionar_y_responder_un_ticket(self):
        ticket = self.crear_ticket()
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:gestionar", args=[ticket.id]),
            {
                "estado": Ticket.Estado.EN_PROCESO,
                "prioridad": Ticket.Prioridad.CRITICA,
                "categoria": Ticket.Categoria.SOFTWARE,
                "asignado_a": self.sistemas.id,
                "vencimiento": "",
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("tickets:agregar_mensaje", args=[ticket.id]),
            {
                "tipo": "publico",
                "contenido": "Estamos revisando el incidente.",
            },
        )

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ticket.estado, Ticket.Estado.EN_PROCESO)
        self.assertEqual(ticket.asignado_a, self.sistemas)
        self.assertEqual(ticket.prioridad, Ticket.Prioridad.CRITICA)
        self.assertEqual(ticket.respondido_por, self.sistemas)
        self.assertTrue(TicketHistorial.objects.filter(ticket=ticket).exists())
        self.assertTrue(TicketMensaje.objects.filter(ticket=ticket, es_interno=False).exists())

    def test_superusuario_puede_asignarse_y_cambiar_estado(self):
        admin = User.objects.create_superuser(
            username="admin",
            password="claveSegura123",
            email="admin@test.local",
        )
        ticket = self.crear_ticket()
        self.client.login(username="admin", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:gestionar", args=[ticket.id]),
            {
                "estado": Ticket.Estado.RESUELTO,
                "prioridad": Ticket.Prioridad.ALTA,
                "categoria": Ticket.Categoria.SOFTWARE,
                "asignado_a": admin.id,
                "vencimiento": "",
            },
            follow=True,
        )

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ticket.estado, Ticket.Estado.RESUELTO)
        self.assertEqual(ticket.asignado_a, admin)

    def test_sistemas_puede_agregar_comentario_interno(self):
        ticket = self.crear_ticket()
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:agregar_mensaje", args=[ticket.id]),
            {"tipo": "interno", "contenido": "Necesita revision de infraestructura."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TicketMensaje.objects.get(ticket=ticket).es_interno)

    def test_accion_rapida_pone_ticket_en_proceso_y_lo_asigna(self):
        ticket = self.crear_ticket()
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.post(reverse("tickets:accion_rapida", args=[ticket.id, "proceso"]))

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ticket.estado, Ticket.Estado.EN_PROCESO)
        self.assertEqual(ticket.asignado_a, self.sistemas)

    def test_accion_rapida_resuelve_ticket(self):
        ticket = self.crear_ticket(estado=Ticket.Estado.EN_PROCESO, asignado_a=self.sistemas)
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.post(reverse("tickets:accion_rapida", args=[ticket.id, "resolver"]))

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ticket.estado, Ticket.Estado.RESUELTO)
        self.assertIsNotNone(ticket.resuelto_en)
        self.assertEqual(ticket.resuelto_por, self.sistemas)

    def test_sistemas_puede_mover_ticket_de_columna(self):
        ticket = self.crear_ticket()
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:mover_estado", args=[ticket.id]),
            {"estado": Ticket.Estado.EN_PROCESO},
        )

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ticket.estado, Ticket.Estado.EN_PROCESO)
        self.assertEqual(ticket.asignado_a, self.sistemas)
        self.assertTrue(
            TicketHistorial.objects.filter(
                ticket=ticket,
                descripcion__icontains="desde el tablero",
            ).exists()
        )

    def test_usuario_no_puede_mover_ticket_de_columna(self):
        ticket = self.crear_ticket()
        self.client.login(username="ana", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:mover_estado", args=[ticket.id]),
            {"estado": Ticket.Estado.EN_PROCESO},
        )

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)

    def test_reporte_mensual_muestra_tickets_cerrados_y_resueltos(self):
        ticket = self.crear_ticket(estado=Ticket.Estado.CERRADO, asignado_a=self.sistemas)
        ticket.resuelto_por = self.sistemas
        ticket.resuelto_en = ticket.creado_en
        ticket.cerrado_por = self.usuario
        ticket.cerrado_en = ticket.creado_en
        ticket.cerrado_por_usuario = True
        ticket.save(
            update_fields=[
                "resuelto_por",
                "resuelto_en",
                "cerrado_por",
                "cerrado_en",
                "cerrado_por_usuario",
            ]
        )

        self.client.login(username="soporte", password="claveSegura123")
        response = self.client.get(reverse("tickets:reporte_mensual"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reporte mensual")
        self.assertContains(response, ticket.asunto)
        self.assertContains(response, self.sistemas.username)

    def test_reporte_mensual_csv_descarga(self):
        ticket = self.crear_ticket(estado=Ticket.Estado.CERRADO, asignado_a=self.sistemas)
        ticket.resuelto_por = self.sistemas
        ticket.resuelto_en = ticket.creado_en
        ticket.cerrado_por = self.usuario
        ticket.cerrado_en = ticket.creado_en
        ticket.cerrado_por_usuario = True
        ticket.save(
            update_fields=[
                "resuelto_por",
                "resuelto_en",
                "cerrado_por",
                "cerrado_en",
                "cerrado_por_usuario",
            ]
        )

        self.client.login(username="soporte", password="claveSegura123")
        response = self.client.get(reverse("tickets:reporte_mensual"), {"format": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(ticket.asunto, response.content.decode("utf-8"))

    def test_usuario_no_puede_ver_reporte_mensual(self):
        self.client.login(username="ana", password="claveSegura123")

        response = self.client.get(reverse("tickets:reporte_mensual"))

        self.assertEqual(response.status_code, 403)

    def test_usuario_no_puede_gestionar_tickets(self):
        ticket = self.crear_ticket()
        self.client.login(username="ana", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:gestionar", args=[ticket.id]),
            {
                "estado": Ticket.Estado.RESUELTO,
                "prioridad": Ticket.Prioridad.MEDIA,
                "categoria": Ticket.Categoria.ACCESO,
                "asignado_a": "",
                "vencimiento": "",
            },
        )

        ticket.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)

    def test_usuario_solo_ve_sus_tickets(self):
        self.crear_ticket(asunto="VPN")
        otro = User.objects.create_user(username="juan", password="claveSegura123")
        Ticket.objects.create(
            asunto="Monitor",
            usuario="Juan",
            creado_por=otro,
            descripcion="Parpadea.",
            categoria=Ticket.Categoria.HARDWARE,
            prioridad=Ticket.Prioridad.BAJA,
        )

        self.client.login(username="ana", password="claveSegura123")
        response = self.client.get(reverse("tickets:index"))

        self.assertContains(response, "VPN")
        self.assertNotContains(response, "Monitor")

    def test_usuario_puede_cerrar_y_reabrir_ticket(self):
        ticket = self.crear_ticket(estado=Ticket.Estado.RESUELTO)
        self.client.login(username="ana", password="claveSegura123")

        cerrar = self.client.post(reverse("tickets:cerrar", args=[ticket.id]))
        ticket.refresh_from_db()
        self.assertEqual(cerrar.status_code, 302)
        self.assertEqual(ticket.estado, Ticket.Estado.CERRADO)

        reabrir = self.client.post(reverse("tickets:reabrir", args=[ticket.id]))
        ticket.refresh_from_db()
        self.assertEqual(reabrir.status_code, 302)
        self.assertEqual(ticket.estado, Ticket.Estado.ABIERTO)

    def test_se_puede_adjuntar_archivo(self):
        ticket = self.crear_ticket()
        self.client.login(username="ana", password="claveSegura123")

        response = self.client.post(
            reverse("tickets:adjuntar_archivo", args=[ticket.id]),
            {"archivo": SimpleUploadedFile("evidencia.txt", b"contenido de prueba")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketAdjunto.objects.filter(ticket=ticket).count(), 1)

    def test_filtro_por_estado_funciona(self):
        self.crear_ticket(asunto="Uno", estado=Ticket.Estado.ABIERTO)
        self.crear_ticket(asunto="Dos", estado=Ticket.Estado.RESUELTO)
        self.client.login(username="soporte", password="claveSegura123")

        response = self.client.get(reverse("tickets:index"), {"estado": Ticket.Estado.RESUELTO})

        self.assertContains(response, "Dos")
        self.assertNotContains(response, "Uno")

    def test_base_de_conocimiento_lista_articulos(self):
        self.client.login(username="ana", password="claveSegura123")
        response = self.client.get(reverse("tickets:base_conocimiento"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.articulo.titulo)

    def test_detalle_ticket_oculta_comentarios_internos_al_usuario(self):
        ticket = self.crear_ticket()
        TicketMensaje.objects.create(ticket=ticket, autor=self.sistemas, contenido="nota interna", es_interno=True)
        TicketMensaje.objects.create(ticket=ticket, autor=self.sistemas, contenido="respuesta publica", es_interno=False)

        self.client.login(username="ana", password="claveSegura123")
        response = self.client.get(reverse("tickets:detalle", args=[ticket.id]))

        self.assertContains(response, "respuesta publica")
        self.assertNotContains(response, "nota interna")
