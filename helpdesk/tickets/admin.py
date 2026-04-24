from django.contrib import admin

from .models import (
    ArticuloBaseConocimiento,
    Perfil,
    Ticket,
    TicketAdjunto,
    TicketHistorial,
    TicketMensaje,
)


class TicketMensajeInline(admin.TabularInline):
    model = TicketMensaje
    extra = 0


class TicketAdjuntoInline(admin.TabularInline):
    model = TicketAdjunto
    extra = 0


class TicketHistorialInline(admin.TabularInline):
    model = TicketHistorial
    extra = 0
    readonly_fields = ("descripcion", "actor", "creado_en")
    can_delete = False


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "rol")
    list_filter = ("rol",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "asunto",
        "usuario",
        "estado",
        "prioridad",
        "categoria",
        "asignado_a",
        "creado_en",
        "actualizado_en",
    )
    list_filter = ("estado", "prioridad", "categoria", "creado_en")
    search_fields = ("asunto", "usuario", "descripcion", "respuesta")
    inlines = [TicketMensajeInline, TicketAdjuntoInline, TicketHistorialInline]


@admin.register(TicketMensaje)
class TicketMensajeAdmin(admin.ModelAdmin):
    list_display = ("ticket", "autor", "es_interno", "creado_en")
    list_filter = ("es_interno", "creado_en")
    search_fields = ("ticket__asunto", "autor__username", "contenido")


@admin.register(TicketAdjunto)
class TicketAdjuntoAdmin(admin.ModelAdmin):
    list_display = ("ticket", "archivo", "subido_por", "creado_en")
    list_filter = ("creado_en",)
    search_fields = ("ticket__asunto", "archivo", "subido_por__username")


@admin.register(TicketHistorial)
class TicketHistorialAdmin(admin.ModelAdmin):
    list_display = ("ticket", "descripcion", "actor", "creado_en")
    list_filter = ("creado_en",)
    search_fields = ("ticket__asunto", "descripcion", "actor__username")


@admin.register(ArticuloBaseConocimiento)
class ArticuloBaseConocimientoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "publicado", "actualizado_en")
    list_filter = ("publicado",)
    prepopulated_fields = {"slug": ("titulo",)}
    search_fields = ("titulo", "resumen", "contenido")
