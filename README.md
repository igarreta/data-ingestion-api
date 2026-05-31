# data-ingestion-api

API gateway entre las aplicaciones del homelab y la base de datos PostgreSQL en Castor. Recibe datos de múltiples aplicaciones, los valida con Pydantic y los persiste en la BD. Las aplicaciones clientes no necesitan credenciales de base de datos.

---

## Infraestructura

| Componente | Detalle |
|---|---|
| **API** | Podman en Cygnus (CT 202, LXC no privilegiado) |
| **Red** | `10.0.100.0/24` (interna, no expuesta al exterior) |
| **Base de datos** | PostgreSQL en Castor — `10.0.100.11:5432`, BD `homelab` |
| **Framework** | FastAPI (Python 3.12) |

---

## Estructura del proyecto

```
data-ingestion-api/
├── app/
│   ├── main.py            # Aplicación FastAPI, lifespan (init/cierre del pool)
│   ├── config.py          # Settings leídos de variables de entorno
│   ├── auth.py            # Validación de Bearer token
│   ├── database.py        # Pool asyncpg (init / close / get)
│   ├── logging_config.py  # RotatingFileHandler + consola
│   ├── notifications.py   # Notificaciones Pushover (solo errores 500)
│   └── routers/
│       └── homeassistant.py  # POST /homeassistant/events
├── logs/                  # Logs con rotación (generado en runtime, ignorado por git)
├── .env.example           # Plantilla de variables de entorno
├── Containerfile          # Imagen Podman (python:3.12-slim)
├── podman-compose.yml     # Despliegue con podman-compose
└── requirements.txt       # Dependencias Python
```

---

## Configuración

Copiar `.env.example` a `.env` y completar los valores:

| Variable | Descripción |
|---|---|
| `DB_HOST` | IP del servidor PostgreSQL (`10.0.100.11`) |
| `DB_PORT` | Puerto PostgreSQL (default `5432`) |
| `DB_NAME` | Nombre de la base de datos (`homelab`) |
| `DB_USER` | Usuario de la BD |
| `DB_PASSWORD` | Contraseña de la BD |
| `APP_TOKEN_<NOMBRE>` | Token Bearer para cada aplicación cliente (ej. `APP_TOKEN_HOMEASSISTANT`) |
| `PUSHOVER_USER_KEY` | User key de Pushover |
| `PUSHOVER_API_TOKEN` | API token de Pushover |
| `PUSHOVER_DEVICE` | Dispositivo Pushover destino (default `iphoneRSI`) |
| `HOSTNAME` | Nombre del host para mensajes de error (default `cygnus`) |
| `SERVICE_NAME` | Nombre del servicio para mensajes de error (default `data-ingestion-api`) |

---

## Despliegue

```bash
# En Cygnus
git clone https://github.com/igarreta/data-ingestion-api.git
cd data-ingestion-api

cp .env.example .env
# Editar .env con los valores reales

podman-compose up -d --build
```

Verificar que la API está corriendo:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## Endpoints

### `GET /health`

```
200 OK
{"status": "ok"}
```

### `POST /homeassistant/events`

Ingesta de eventos de Home Assistant.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "entity": "sensor.temperatura_salon",
  "value": "21.5",
  "timestamp": "2026-05-30T10:00:00"
}
```

`timestamp` es opcional; si se omite se usa la hora actual (UTC).

**Respuestas:**

| Código | Significado |
|---|---|
| `201` | Inserción exitosa |
| `401` | Token inválido o ausente |
| `422` | Datos inválidos (validación Pydantic) |
| `500` | Error interno (falla de BD u otro) |

**Ejemplo curl:**

```bash
curl -X POST http://10.0.100.x:8000/homeassistant/events \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity": "sensor.temperatura_salon", "value": "21.5"}'
```

---

## Autenticación

Cada aplicación cliente tiene su propio token Bearer, definido como variable de entorno con el patrón `APP_TOKEN_<NOMBRE>` en el `.env`:

```
APP_TOKEN_HOMEASSISTANT=mi-token-secreto
APP_TOKEN_OTRAAPP=otro-token
```

Para revocar el acceso de una aplicación, basta con eliminar o cambiar su variable y reiniciar el contenedor, sin afectar a las demás.

---

## Logging

Los logs se escriben en `logs/api.log` con rotación automática:
- Tamaño máximo por archivo: **10 MB**
- Archivos de backup: **7** (equivalente a ~7 días de logs en uso normal)

Cada inserción se registra con el nombre de la entidad y el origen (nombre de la app cliente).

---

## Notificaciones

Se envía una notificación Pushover al dispositivo `iphoneRSI` únicamente ante errores `500`. El mensaje incluye el hostname y el nombre del servicio.

---

## Agregar un nuevo dominio

1. Crear `app/routers/<dominio>.py` usando `app/routers/homeassistant.py` como plantilla
2. Definir el modelo Pydantic con los campos del endpoint
3. Escribir la query `INSERT` correspondiente a la tabla en Castor
4. Registrar el router en `app/main.py`:
   ```python
   from app.routers import <dominio>
   app.include_router(<dominio>.router)
   ```
5. Añadir la variable `APP_TOKEN_<NOMBRE>` en `.env` para la aplicación cliente
