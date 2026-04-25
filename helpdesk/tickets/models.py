from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone


class Perfil(models.Model):
    class Rol(models.TextChoices):
        USUARIO = "usuario", "Usuario"
        SISTEMAS = "sistemas", "Sistemas"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.USUARIO,
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_rol_display()})"

    @property
    def es_sistemas(self):
        return self.rol == self.Rol.SISTEMAS


class Ticket(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "abierto", "Abierto"
        EN_PROCESO = "en_proceso", "En proceso"
        RESUELTO = "resuelto", "Resuelto"
        CERRADO = "cerrado", "Cerrado"

    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Critica"

    class Categoria(models.TextChoices):
        HARDWARE = "hardware", "Hardware"
        SOFTWARE = "software", "Software"
        RED = "red", "Red"
        ACCESO = "acceso", "Acceso"
        CUENTA = "cuenta", "Cuenta"
        OTROS = "otros", "Otros"

    asunto = models.CharField(max_length=120)
    usuario = models.CharField(max_length=255)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_creados",
        null=True,
        blank=True,
    )
    descripcion = models.TextField()
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.OTROS,
    )
    prioridad = models.CharField(
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ABIERTO,
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tickets_asignados",
        null=True,
        blank=True,
    )
    respuesta = models.TextField(blank=True)
    respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tickets_respondidos",
        null=True,
        blank=True,
    )
    respondido_en = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tickets_resueltos",
        null=True,
        blank=True,
    )
    resuelto_en = models.DateTimeField(null=True, blank=True)
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tickets_cerrados",
        null=True,
        blank=True,
    )
    cerrado_en = models.DateTimeField(null=True, blank=True)
    cerrado_por_usuario = models.BooleanField(default=False)
    vencimiento = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["estado", "-creado_en"]

    def __str__(self):
        return f"{self.asunto} - {self.usuario}"

    @property
    def tiene_respuesta(self):
        return bool(self.respuesta.strip())

    @property
    def esta_vencido(self):
        return bool(
            self.vencimiento
            and self.vencimiento < timezone.now()
            and self.estado not in {self.Estado.RESUELTO, self.Estado.CERRADO}
        )

    @property
    def sla_estado(self):
        if not self.vencimiento:
            return "sin_objetivo"
        if self.estado in {self.Estado.RESUELTO, self.Estado.CERRADO}:
            return "cumplido"

        ahora = timezone.now()
        if self.vencimiento < ahora:
            return "vencido"

        horas_restantes = (self.vencimiento - ahora).total_seconds() / 3600
        if horas_restantes <= 24:
            return "riesgo"
        return "en_tiempo"

    @property
    def sla_texto(self):
        etiquetas = {
            "sin_objetivo": "Sin objetivo",
            "cumplido": "Cumplido",
            "vencido": "Vencido",
            "riesgo": "Por vencer",
            "en_tiempo": "En tiempo",
        }
        return etiquetas[self.sla_estado]


class TicketMensaje(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="mensajes")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mensajes_ticket",
    )
    contenido = models.TextField()
    es_interno = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]

    def __str__(self):
        tipo = "Interno" if self.es_interno else "Publico"
        return f"{tipo} - Ticket #{self.ticket_id}"


class TicketAdjunto(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="adjuntos")
    archivo = models.FileField(upload_to="tickets/adjuntos/%Y/%m/%d")
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="adjuntos_ticket",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return self.archivo.name.rsplit("/", maxsplit=1)[-1]


class TicketHistorial(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="historial")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_ticket",
    )
    descripcion = models.CharField(max_length=255)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Ticket #{self.ticket_id}: {self.descripcion}"


class ArticuloBaseConocimiento(models.Model):
    titulo = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, blank=True)
    resumen = models.CharField(max_length=220)
    contenido = models.TextField()
    publicado = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Articulo de base de conocimiento"
        verbose_name_plural = "Articulos de base de conocimiento"
        ordering = ["titulo"]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)
