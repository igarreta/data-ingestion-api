# data-ingestion-api

API gateway entre las aplicaciones del homelab y la base de datos PostgreSQL en Castor. Recibe datos de múltiples aplicaciones, los valida con Pydantic y los persiste en la BD. Las aplicaciones clientes no necesitan credenciales de base de datos.

---

## Infraestructura

| Componente | Detalle |
|---|---|
| **API** | Podman en Cygnus (CT 202, LXC no privilegiado) |
| **Red** | `10.0.100.0/24` (interna, no expuesta al exterior) |
| **Base de datos** | PostgreSQL en Castor — `10.0.100.11:5432`, BD `homelab` |
| **Usuario BD** | `ingestion_api` — SELECT en `entities`, INSERT en `measurements` |
| **Framework** | FastAPI (Python 3.12) |

---

## Diseño de la base de datos

Modelo genérico de series de tiempo: una fila por medición, identificada por `entity_id`.

- `entities` — catálogo de entidades conocidas, administrado manualmente.
- `measurements` — tabla append-only de mediciones numéricas.

Ejemplos de `entity_id`: `bomba_agua.run_secs`, `sensor.temperatura_exterior`

La API valida que el `entity_id` exista en `entities` antes de insertar. Si no existe, devuelve 422.

El script DDL completo está en `db/migrations/001_initial_schema.sql`.

### Registrar una entidad nueva

Las entidades se crean manualmente en Castor:

```sql
INSERT INTO entities (id, unit, description, device)
VALUES ('bomba_agua.run_secs', 'seconds', 'Duración de encendido', 'bomba_agua');
```

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
├── db/
│   └── migrations/
│       └── 001_initial_schema.sql  # DDL de entities y measurements
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
| `DB_USER` | Usuario de la BD (`ingestion_api`) |
| `DB_PASSWORD` | Contraseña de la BD |
| `APP_TOKEN_<NOMBRE>` | Token Bearer por aplicación cliente (ej. `APP_TOKEN_HOMEASSISTANT`) |
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

Ingesta de mediciones desde Home Assistant.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "entity_id": "bomba_agua.run_secs",
  "value": 600,
  "timestamp": "2026-05-31T10:00:00Z"
}
```

`timestamp` es opcional; si se omite se usa la hora actual (UTC).

**Respuestas:**

| Código | Significado |
|---|---|
| `201` | Inserción exitosa |
| `401` | Token inválido o ausente |
| `422` | `entity_id` desconocido, o datos inválidos |
| `500` | Error interno (falla de BD u otro) |

**Ejemplo curl:**

```bash
curl -X POST http://10.0.100.x:8000/homeassistant/events \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "bomba_agua.run_secs", "value": 600}'
```

---

## Autenticación

Cada aplicación cliente tiene su propio token Bearer, definido como variable de entorno con el patrón `APP_TOKEN_<NOMBRE>` en el `.env`:

```
APP_TOKEN_HOMEASSISTANT=mi-token-secreto
APP_TOKEN_OTRAAPP=otro-token
```

Para revocar el acceso de una aplicación, basta con eliminar o cambiar su variable y reiniciar el contenedor.

---

## Logging

Los logs se escriben en `logs/api.log` con rotación automática:
- Tamaño máximo por archivo: **10 MB**
- Archivos de backup: **7**

Cada inserción se registra con `entity_id` y el origen (nombre de la app cliente).

---

## Notificaciones

Se envía una notificación Pushover al dispositivo `iphoneRSI` únicamente ante errores `500`.

---

## Agregar un nuevo dominio

1. Crear `app/routers/<dominio>.py` usando `app/routers/homeassistant.py` como plantilla
2. Definir el modelo Pydantic con `entity_id`, `value` y `timestamp`
3. Validar que `entity_id` existe en `entities` antes de insertar
4. Registrar el router en `app/main.py`
5. Añadir `APP_TOKEN_<NOMBRE>` en `.env`

---

## Próximos pasos

- [ ] Configurar `.env` en Cygnus con credenciales reales
- [ ] Primer despliegue del contenedor en Cygnus con `podman-compose up -d --build`
- [ ] Registrar la primera entidad en `entities` (ej. `bomba_agua.run_secs`)
- [ ] Configurar Home Assistant para enviar eventos al endpoint `/homeassistant/events`
- [ ] Verificar inserción con un curl de prueba y consultar `measurements` en psql
- [ ] Evaluar app de visualización (custom primero, Grafana después)
