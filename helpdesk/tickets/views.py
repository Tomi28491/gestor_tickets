from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AdjuntoForm,
    ComentarioInternoForm,
    LoginForm,
    MensajePublicoForm,
    RegistroUsuarioForm,
    TicketFiltroForm,
    TicketForm,
    TicketGestionForm,
)
from .models import ArticuloBaseConocimiento, Perfil, Ticket, TicketAdjunto, TicketHistorial, TicketMensaje


def obtener_rol(request):
    if not request.user.is_authenticated:
        return None
    if request.user.is_superuser:
        return Perfil.Rol.SISTEMAS
    perfil = getattr(request.user, "perfil", None)
    return perfil.rol if perfil else Perfil.Rol.USUARIO


def es_sistemas(request):
    return obtener_rol(request) == Perfil.Rol.SISTEMAS


def enviar_notificacion(destinatario, asunto, mensaje):
    if not destinatario:
        return
    if not getattr(settings, "DEFAULT_FROM_EMAIL", ""):
        return
    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [destinatario], fail_silently=True)


def registrar_historial(ticket, descripcion, actor=None):
    TicketHistorial.objects.create(ticket=ticket, descripcion=descripcion, actor=actor)


def timeline_estado(ticket):
    pasos = [
        (Ticket.Estado.ABIERTO, "Abierto"),
        (Ticket.Estado.EN_PROCESO, "En proceso"),
        (Ticket.Estado.RESUELTO, "Resuelto"),
        (Ticket.Estado.CERRADO, "Cerrado"),
    ]
    actual = ticket.estado
    indice_actual = next((i for i, (valor, _) in enumerate(pasos) if valor == actual), 0)
    timeline = []
    for indice, (valor, etiqueta) in enumerate(pasos):
        if indice < indice_actual:
            estado = "completado"
        elif indice == indice_actual:
            estado = "actual"
        else:
            estado = "pendiente"
        timeline.append({"valor": valor, "etiqueta": etiqueta, "estado": estado})
    return timeline


def preparar_ticket_ui(ticket):
    ticket.timeline = timeline_estado(ticket)
    return ticket


def tickets_visibles_para(request):
    queryset = Ticket.objects.select_related("creado_por", "respondido_por", "asignado_a")
    if es_sistemas(request):
        return queryset.all()
    return queryset.filter(creado_por=request.user)


def aplicar_filtros(queryset, data, es_staff):
    filtro = TicketFiltroForm(data or None, es_sistemas=es_staff)
    if filtro.is_valid():
        q = filtro.cleaned_data.get("q")
        if q:
            queryset = queryset.filter(
                Q(asunto__icontains=q)
                | Q(descripcion__icontains=q)
                | Q(usuario__icontains=q)
                | Q(mensajes__contenido__icontains=q)
            ).distinct()
        estado = filtro.cleaned_data.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        prioridad = filtro.cleaned_data.get("prioridad")
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        categoria = filtro.cleaned_data.get("categoria")
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        if es_staff:
            asignado_a = filtro.cleaned_data.get("asignado_a")
            if asignado_a:
                queryset = queryset.filter(asignado_a=asignado_a)
        if filtro.cleaned_data.get("solo_vencidos"):
            queryset = queryset.filter(
                vencimiento__lt=timezone.now(),
            ).exclude(estado__in=[Ticket.Estado.RESUELTO, Ticket.Estado.CERRADO])
    return queryset, filtro


def login_view(request):
    if request.user.is_authenticated:
        return redirect("tickets:index")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Sesion iniciada correctamente.")
        return redirect("tickets:index")
    return render(request, "tickets/login.html", {"form": form})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect("tickets:index")

    form = RegistroUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Tu cuenta fue creada. Ya puedes cargar tickets.")
        return redirect("tickets:index")
    return render(request, "tickets/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "La sesion se cerro correctamente.")
    return redirect("tickets:login")


@login_required
def index(request):
    rol = obtener_rol(request)
    staff = rol == Perfil.Rol.SISTEMAS

    if request.method == "POST" and not staff:
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.usuario = request.user.get_full_name().strip() or request.user.username
            ticket.creado_por = request.user
            ticket.save()
            TicketMensaje.objects.create(
                ticket=ticket,
                autor=request.user,
                contenido=ticket.descripcion,
            )
            registrar_historial(ticket, "Ticket creado", request.user)
            enviar_notificacion(
                request.user.email,
                f"Ticket creado: {ticket.asunto}",
                f"Tu ticket fue registrado con estado {ticket.get_estado_display()}.",
            )
            messages.success(request, "El ticket se creo correctamente.")
            return redirect("tickets:detalle", ticket_id=ticket.id)
    else:
        form = TicketForm()

    tickets = tickets_visibles_para(request)
    tickets, filtro_form = aplicar_filtros(tickets, request.GET, staff)

    resumen_estados = {
        "abiertos": tickets.filter(estado=Ticket.Estado.ABIERTO).count(),
        "en_proceso": tickets.filter(estado=Ticket.Estado.EN_PROCESO).count(),
        "resueltos": tickets.filter(estado=Ticket.Estado.RESUELTO).count(),
        "cerrados": tickets.filter(estado=Ticket.Estado.CERRADO).count(),
        "vencidos": sum(1 for ticket in tickets if ticket.esta_vencido),
    }
    metricas = {
        "sin_asignar": tickets.filter(asignado_a__isnull=True).count() if staff else 0,
        "cerrados_por_usuario": tickets.filter(cerrado_por_usuario=True).count(),
        "por_categoria": tickets.values("categoria").annotate(total=Count("id")).order_by("-total"),
    }
    tickets = [preparar_ticket_ui(ticket) for ticket in tickets]
    articulos = ArticuloBaseConocimiento.objects.filter(publicado=True)[:4]
    context = {
        "form": form,
        "tickets": tickets,
        "resumen_estados": resumen_estados,
        "metricas": metricas,
        "filtro_form": filtro_form,
        "rol": rol,
        "es_sistemas": staff,
        "articulos": articulos,
    }
    return render(request, "tickets/index.html", context)


def obtener_ticket_para_usuario(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related("creado_por", "respondido_por", "asignado_a"),
        pk=ticket_id,
    )
    if es_sistemas(request):
        return ticket
    if ticket.creado_por_id != request.user.id:
        raise PermissionError
    return ticket


@login_required
def ticket_detalle(request, ticket_id):
    try:
        ticket = preparar_ticket_ui(obtener_ticket_para_usuario(request, ticket_id))
    except PermissionError:
        return HttpResponseForbidden("No tienes permisos para ver este ticket.")

    staff = es_sistemas(request)
    gestion_form = TicketGestionForm(instance=ticket)
    mensaje_form = MensajePublicoForm()
    comentario_form = ComentarioInternoForm()
    adjunto_form = AdjuntoForm()

    mensajes_visibles = ticket.mensajes.select_related("autor")
    if not staff:
        mensajes_visibles = mensajes_visibles.filter(es_interno=False)

    context = {
        "ticket": ticket,
        "gestion_form": gestion_form,
        "mensaje_form": mensaje_form,
        "comentario_form": comentario_form,
        "adjunto_form": adjunto_form,
        "mensajes_ticket": mensajes_visibles,
        "historial": ticket.historial.select_related("actor")[:12],
        "adjuntos": ticket.adjuntos.select_related("subido_por"),
        "es_sistemas": staff,
    }
    return render(request, "tickets/detail.html", context)


@login_required
def accion_rapida_ticket(request, ticket_id, accion):
    if request.method != "POST":
        return redirect("tickets:index")
    if not es_sistemas(request):
        return HttpResponseForbidden("No tienes permisos para gestionar tickets.")

    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if accion == "tomar":
        ticket.asignado_a = request.user
        registrar_historial(ticket, "Ticket tomado desde acciones rapidas", request.user)
        mensaje = "Te asignaste el ticket correctamente."
    elif accion == "proceso":
        ticket.estado = Ticket.Estado.EN_PROCESO
        if not ticket.asignado_a:
            ticket.asignado_a = request.user
        registrar_historial(ticket, "Ticket movido a En proceso desde acciones rapidas", request.user)
        mensaje = "El ticket paso a En proceso."
    elif accion == "resolver":
        ticket.estado = Ticket.Estado.RESUELTO
        ticket.resuelto_en = timezone.now()
        if not ticket.asignado_a:
            ticket.asignado_a = request.user
        registrar_historial(ticket, "Ticket resuelto desde acciones rapidas", request.user)
        mensaje = "El ticket fue marcado como resuelto."
    else:
        messages.error(request, "La accion solicitada no existe.")
        return redirect("tickets:index")

    ticket.cerrado_por_usuario = False
    ticket.save()
    messages.success(request, mensaje)
    return redirect("tickets:index")


@login_required
def gestionar_ticket(request, ticket_id):
    if request.method != "POST":
        return redirect("tickets:detalle", ticket_id=ticket_id)
    if not es_sistemas(request):
        return HttpResponseForbidden("No tienes permisos para gestionar tickets.")

    ticket = get_object_or_404(Ticket, pk=ticket_id)
    previo = {
        "estado": ticket.estado,
        "prioridad": ticket.prioridad,
        "categoria": ticket.categoria,
        "asignado_a_id": ticket.asignado_a_id,
        "vencimiento": ticket.vencimiento,
    }
    form = TicketGestionForm(request.POST, instance=ticket)
    if form.is_valid():
        ticket = form.save(commit=False)
        if ticket.estado == Ticket.Estado.RESUELTO and previo["estado"] != Ticket.Estado.RESUELTO:
            ticket.resuelto_en = timezone.now()
        if ticket.estado in {Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO}:
            ticket.cerrado_por_usuario = False
        ticket.save()

        cambios = []
        for campo, etiqueta in {
            "estado": "Estado",
            "prioridad": "Prioridad",
            "categoria": "Categoria",
            "asignado_a_id": "Asignacion",
            "vencimiento": "Vencimiento",
        }.items():
            nuevo = getattr(ticket, campo)
            if previo[campo] != nuevo:
                cambios.append(etiqueta)
        if cambios:
            registrar_historial(ticket, f"Cambios en: {', '.join(cambios)}", request.user)

        enviar_notificacion(
            ticket.creado_por.email if ticket.creado_por else "",
            f"Actualizacion en tu ticket: {ticket.asunto}",
            f"Tu ticket ahora esta en estado {ticket.get_estado_display()}.",
        )
        messages.success(request, "La gestion del ticket fue actualizada.")
    else:
        errores = []
        for field, field_errors in form.errors.items():
            etiqueta = form.fields[field].label if field in form.fields else field
            errores.append(f"{etiqueta}: {' '.join(field_errors)}")
        detalle = " | ".join(errores) if errores else "Revisa la informacion enviada."
        messages.error(request, f"No se pudieron guardar los cambios del ticket. {detalle}")
    return redirect("tickets:detalle", ticket_id=ticket.id)


@login_required
def agregar_mensaje(request, ticket_id):
    if request.method != "POST":
        return redirect("tickets:detalle", ticket_id=ticket_id)

    try:
        ticket = obtener_ticket_para_usuario(request, ticket_id)
    except PermissionError:
        return HttpResponseForbidden("No tienes permisos para responder este ticket.")

    staff = es_sistemas(request)
    tipo = request.POST.get("tipo", "publico")
    form_class = ComentarioInternoForm if tipo == "interno" and staff else MensajePublicoForm
    form = form_class(request.POST)
    if form.is_valid():
        mensaje = form.save(commit=False)
        mensaje.ticket = ticket
        mensaje.autor = request.user
        mensaje.es_interno = tipo == "interno" and staff
        mensaje.save()
        ticket.actualizado_en = timezone.now()
        if not mensaje.es_interno:
            ticket.respuesta = mensaje.contenido
            ticket.respondido_por = request.user if staff else ticket.respondido_por
            ticket.respondido_en = timezone.now() if staff else ticket.respondido_en
            if staff and ticket.estado == Ticket.Estado.ABIERTO:
                ticket.estado = Ticket.Estado.EN_PROCESO
        ticket.save()
        descripcion = "Comentario interno agregado" if mensaje.es_interno else "Nuevo mensaje en la conversacion"
        registrar_historial(ticket, descripcion, request.user)
        enviar_notificacion(
            ticket.creado_por.email if ticket.creado_por and staff and not mensaje.es_interno else "",
            f"Nueva respuesta en ticket: {ticket.asunto}",
            "Se agrego una nueva respuesta a tu ticket.",
        )
        messages.success(request, "El mensaje fue agregado.")
    else:
        messages.error(request, "No se pudo guardar el mensaje.")
    return redirect("tickets:detalle", ticket_id=ticket.id)


@login_required
def adjuntar_archivo(request, ticket_id):
    if request.method != "POST":
        return redirect("tickets:detalle", ticket_id=ticket_id)

    try:
        ticket = obtener_ticket_para_usuario(request, ticket_id)
    except PermissionError:
        return HttpResponseForbidden("No tienes permisos para adjuntar archivos.")

    form = AdjuntoForm(request.POST, request.FILES)
    if form.is_valid():
        adjunto = form.save(commit=False)
        adjunto.ticket = ticket
        adjunto.subido_por = request.user
        adjunto.save()
        registrar_historial(ticket, "Se adjunto un archivo", request.user)
        messages.success(request, "El archivo fue adjuntado correctamente.")
    else:
        messages.error(request, "No se pudo adjuntar el archivo.")
    return redirect("tickets:detalle", ticket_id=ticket.id)


@login_required
def cerrar_ticket(request, ticket_id):
    if request.method != "POST":
        return redirect("tickets:detalle", ticket_id=ticket_id)

    try:
        ticket = obtener_ticket_para_usuario(request, ticket_id)
    except PermissionError:
        return HttpResponseForbidden("No tienes permisos para cerrar este ticket.")

    if es_sistemas(request):
        return HttpResponseForbidden("Esta accion esta reservada para el usuario final.")

    ticket.estado = Ticket.Estado.CERRADO
    ticket.cerrado_por_usuario = True
    ticket.save(update_fields=["estado", "cerrado_por_usuario", "actualizado_en"])
    registrar_historial(ticket, "El usuario cerro el ticket", request.user)
    messages.success(request, "El ticket fue cerrado.")
    return redirect("tickets:detalle", ticket_id=ticket.id)


@login_required
def reabrir_ticket(request, ticket_id):
    if request.method != "POST":
        return redirect("tickets:detalle", ticket_id=ticket_id)

    try:
        ticket = obtener_ticket_para_usuario(request, ticket_id)
    except PermissionError:
        return HttpResponseForbidden("No tienes permisos para reabrir este ticket.")

    if es_sistemas(request):
        return HttpResponseForbidden("Esta accion esta reservada para el usuario final.")

    ticket.estado = Ticket.Estado.ABIERTO
    ticket.cerrado_por_usuario = False
    ticket.save(update_fields=["estado", "cerrado_por_usuario", "actualizado_en"])
    registrar_historial(ticket, "El usuario reabrio el ticket", request.user)
    messages.success(request, "El ticket fue reabierto.")
    return redirect("tickets:detalle", ticket_id=ticket.id)


@login_required
def base_conocimiento(request):
    articulos = ArticuloBaseConocimiento.objects.filter(publicado=True)
    query = request.GET.get("q", "").strip()
    if query:
        articulos = articulos.filter(
            Q(titulo__icontains=query) | Q(resumen__icontains=query) | Q(contenido__icontains=query)
        )
    return render(
        request,
        "tickets/knowledge_base.html",
        {"articulos": articulos, "query": query},
    )


@login_required
def articulo_detalle(request, slug):
    articulo = get_object_or_404(ArticuloBaseConocimiento, slug=slug, publicado=True)
    return render(request, "tickets/knowledge_detail.html", {"articulo": articulo})
