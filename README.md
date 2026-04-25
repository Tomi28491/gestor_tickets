# Gestor de Tickets

Aplicacion web hecha con Django para registrar, gestionar y dar seguimiento a tickets de soporte. El sistema diferencia entre usuarios finales y personal de sistemas, incluye conversacion por ticket, comentarios internos, adjuntos, SLA, tablero visual tipo Kanban y reporte mensual de resoluciones y cierres.

## Caracteristicas principales

- Registro e inicio de sesion de usuarios.
- Roles de acceso: `Usuario` y `Sistemas`.
- Creacion de tickets con asunto, categoria, prioridad, descripcion y fecha objetivo.
- Tablero principal para soporte con columnas por estado:
  `Abierto`, `En proceso`, `Resuelto`, `Cerrado`.
- Cambio de estado por drag and drop desde el tablero.
- Vista de detalle del ticket con:
  conversacion, comentarios internos, historial, adjuntos y gestion administrativa.
- Acciones rapidas para soporte:
  asignarse un ticket, pasarlo a proceso y resolverlo.
- Cierre y reapertura por parte del usuario final.
- Seguimiento de SLA:
  `Sin objetivo`, `En tiempo`, `Por vencer`, `Vencido`, `Cumplido`.
- Base de conocimiento con listado y detalle de articulos.
- Reporte mensual para sistemas con:
  tickets creados, resueltos, cerrados, cerrados por usuario, cerrados por sistemas y exportacion CSV.
- Trazabilidad con historial de cambios.
- Suite de tests para flujos principales.

## Stack tecnologico

- Python 3.11
- Django 5.2
- SQLite
- Templates de Django
- CSS y JavaScript vanilla

## Estructura del proyecto

```text
gestor_tickets/
|-- README.md
`-- helpdesk/
    |-- manage.py
    |-- db.sqlite3
    |-- media/
    |-- helpdesk/
    |   |-- settings.py
    |   |-- urls.py
    |   `-- ...
    `-- tickets/
        |-- admin.py
        |-- forms.py
        |-- models.py
        |-- tests.py
        |-- urls.py
        |-- views.py
        |-- migrations/
        `-- templates/tickets/
```

## Modelos principales

### `Perfil`

Relaciona cada usuario con un rol:

- `usuario`
- `sistemas`

### `Ticket`

Guarda la informacion principal del caso:

- asunto
- usuario
- creador del ticket
- descripcion
- categoria
- prioridad
- estado
- tecnico asignado
- vencimiento
- fechas de creacion y actualizacion
- quien respondio, resolvio y cerro
- si el cierre fue hecho por el usuario final

Estados disponibles:

- `abierto`
- `en_proceso`
- `resuelto`
- `cerrado`

Prioridades:

- `baja`
- `media`
- `alta`
- `critica`

Categorias:

- `hardware`
- `software`
- `red`
- `acceso`
- `cuenta`
- `otros`

### `TicketMensaje`

Mensajes asociados al ticket. Pueden ser:

- publicos
- internos

### `TicketAdjunto`

Archivos cargados dentro del ticket.

### `TicketHistorial`

Registro de cambios y eventos relevantes del ticket.

### `ArticuloBaseConocimiento`

Articulos publicados para consulta de usuarios.

## Funcionalidades por rol

### Usuario final

- Registrarse e iniciar sesion.
- Crear tickets.
- Ver solo sus propios tickets.
- Responder en la conversacion publica.
- Adjuntar archivos.
- Cerrar tickets resueltos o reabrir tickets cerrados.
- Consultar base de conocimiento.

### Sistemas

- Ver todos los tickets.
- Gestionar estado, prioridad, categoria, asignacion y fecha objetivo.
- Agregar comentarios internos.
- Usar acciones rapidas.
- Mover tickets entre columnas en el tablero.
- Consultar el reporte mensual.
- Exportar reporte en CSV.

## Flujo general del sistema

1. El usuario crea un ticket.
2. El sistema registra el primer mensaje con la descripcion.
3. Soporte visualiza el ticket en el tablero.
4. Un tecnico puede asignarse el ticket o moverlo a `En proceso`.
5. La conversacion y el historial quedan registrados en el detalle.
6. El tecnico puede marcarlo como `Resuelto`.
7. El usuario final puede cerrarlo o reabrirlo.
8. El reporte mensual consolida quienes resolvieron y cerraron tickets.

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/Tomi28491/gestor_tickets.git
cd gestor_tickets
```

### 2. Crear entorno virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

Si todavia no tienes Django instalado en el entorno:

```bash
pip install django
```

Si luego agregas un `requirements.txt`, puedes usar:

```bash
pip install -r requirements.txt
```

### 4. Aplicar migraciones

```bash
cd helpdesk
python manage.py migrate
```

### 5. Crear superusuario

```bash
python manage.py createsuperuser
```

### 6. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador:

```text
http://127.0.0.1:8000/
```

## Configuracion actual

En `helpdesk/helpdesk/settings.py` el proyecto usa:

- Base de datos `SQLite`
- `DEBUG = True`
- `LANGUAGE_CODE = "es"`
- `TIME_ZONE = "UTC"`
- `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`
- `MEDIA_URL = "/media/"`
- `MEDIA_ROOT = BASE_DIR / "media"`

Importante:

- En desarrollo, los correos se imprimen por consola.
- Los adjuntos se sirven solo con `DEBUG = True`.
- La clave secreta actual esta hardcodeada en `settings.py`, por lo que no deberia usarse asi en produccion.

## Migraciones

El proyecto ya incluye migraciones de la app `tickets`.

Para verificar el estado:

```bash
python manage.py showmigrations tickets
```

Para aplicar todas:

```bash
python manage.py migrate
```

Si el codigo espera campos nuevos y tu base no los tiene, normalmente se resuelve con:

```bash
python manage.py migrate tickets
```

## Usuarios y roles

Los usuarios nuevos se registran con rol `Usuario`.

Para convertir un usuario a `Sistemas` puedes hacerlo desde:

- el panel admin de Django
- la tabla/modelo `Perfil`

Ruta del admin:

```text
/admin/
```

## Rutas principales

### Autenticacion

- `/login/`
- `/registro/`
- `/logout/`

### Tickets

- `/`
- `/tickets/<id>/`
- `/tickets/<id>/gestionar/`
- `/tickets/<id>/accion/<accion>/`
- `/tickets/<id>/mover-estado/`
- `/tickets/<id>/mensaje/`
- `/tickets/<id>/adjunto/`
- `/tickets/<id>/cerrar/`
- `/tickets/<id>/reabrir/`

### Base de conocimiento

- `/base-conocimiento/`
- `/base-conocimiento/<slug>/`

### Reportes

- `/reportes/mensual/`

## Tablero Kanban

La vista principal para `Sistemas` funciona como tablero visual.

Permite:

- arrastrar tickets entre columnas
- actualizar estado sin recargar la pagina
- ver prioridad, SLA, tecnico asignado, mensajes y adjuntos
- abrir el detalle para gestion completa

Estados del tablero:

- `Abierto`
- `En proceso`
- `Resuelto`
- `Cerrado`

## Reporte mensual

Disponible solo para usuarios con rol `Sistemas`.

Incluye:

- selector de mes
- resumen de tickets creados, resueltos y cerrados
- diferencia entre cierres por usuario y cierres por sistemas
- tabla detallada con:
  ticket, estado, categoria, asignado, resuelto por, resuelto en, cerrado por y fecha de cierre
- exportacion CSV

## Notificaciones por correo

El proyecto dispara correos en algunos eventos, por ejemplo:

- creacion de ticket
- actualizacion de ticket
- nuevas respuestas publicas

Como el backend actual es de consola, esos correos no se envian realmente: se imprimen en la terminal.

## Adjuntos

Los archivos se almacenan en:

```text
helpdesk/media/
```

Los `upload_to` de tickets usan una estructura por fecha:

```text
tickets/adjuntos/%Y/%m/%d
```

## Pruebas

Para correr los tests de la app:

```bash
cd helpdesk
python manage.py test tickets
```

Para chequeo general:

```bash
python manage.py check
```

## Estado actual del proyecto

Actualmente el sistema ya cuenta con:

- tema oscuro fijo
- tablero visual ampliado para soporte
- detalle de ticket mejorado
- comentarios internos
- trazabilidad por historial
- reporte mensual y exportacion CSV

## Pendientes recomendados

Ideas utiles para seguir evolucionandolo:

- agregar `requirements.txt`
- mover configuraciones sensibles a variables de entorno
- mejorar reportes con graficos
- agregar filtros avanzados por fechas
- soporte de paginacion
- ordenar tarjetas dentro de una misma columna
- mejorar permisos a nivel mas fino
- preparar despliegue para produccion

## Capturas o demo

Si quieres, puedes agregar luego en este README:

- capturas del tablero
- capturas del detalle del ticket
- ejemplo del reporte mensual

## Licencia

Este proyecto no tiene una licencia declarada por ahora. Si vas a publicarlo formalmente, conviene agregar una.
