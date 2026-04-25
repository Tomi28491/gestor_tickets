from django.urls import path

from . import views


app_name = "tickets"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.index, name="index"),
    path("tickets/<int:ticket_id>/", views.ticket_detalle, name="detalle"),
    path("tickets/<int:ticket_id>/gestionar/", views.gestionar_ticket, name="gestionar"),
    path("tickets/<int:ticket_id>/accion/<str:accion>/", views.accion_rapida_ticket, name="accion_rapida"),
    path("tickets/<int:ticket_id>/mover-estado/", views.mover_ticket_estado, name="mover_estado"),
    path("tickets/<int:ticket_id>/mensaje/", views.agregar_mensaje, name="agregar_mensaje"),
    path("tickets/<int:ticket_id>/adjunto/", views.adjuntar_archivo, name="adjuntar_archivo"),
    path("tickets/<int:ticket_id>/cerrar/", views.cerrar_ticket, name="cerrar"),
    path("tickets/<int:ticket_id>/reabrir/", views.reabrir_ticket, name="reabrir"),
    path("base-conocimiento/", views.base_conocimiento, name="base_conocimiento"),
    path("base-conocimiento/<slug:slug>/", views.articulo_detalle, name="articulo_detalle"),
    path("reportes/mensual/", views.reporte_mensual, name="reporte_mensual"),
]
