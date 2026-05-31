# CLAUDE.md — data-ingestion-api

FastAPI gateway that receives data from homelab applications, validates it with Pydantic, and inserts it into PostgreSQL. Client apps never hold database credentials.

---

## Stack

| Library | Version | Role |
|---|---|---|
| FastAPI | 0.115 | Web framework |
| asyncpg | 0.30 | Async PostgreSQL driver |
| Pydantic v2 | 2.11 | Request validation |
| uvicorn | 0.34 | ASGI server |
| httpx | 0.28 | Async HTTP client (Pushover) |
| python-dotenv | 1.1 | `.env` loading |

---

## Infrastructure

| Component | Detail |
|---|---|
| **API host** | Cygnus — CT 202, unprivileged LXC, Podman, `10.0.100.0/24` internal network |
| **Database** | Castor — PostgreSQL at `10.0.100.11:5432`, database `homelab` |
| **DB user** | `ingestion_api` — SELECT on `entities`, INSERT on `measurements` only |
| **DB schema** | Managed manually on Castor — this API only validates and inserts, never runs migrations |
| **Deployment** | `podman-compose up -d --build` on Cygnus |

---

## Database schema

### Design

Generic time-series model: one row per measurement, keyed by `entity_id`.

- `entities` — catalogue of known entities, managed manually by the sysadmin.
- `measurements` — append-only table of numeric measurements.

`entity_id` examples: `bomba_agua.run_secs`, `sensor.temperatura_exterior`

The API validates that `entity_id` exists in `entities` before inserting; unknown entities return 422.

### Tables

```sql
CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    unit        TEXT,
    description TEXT,
    device      TEXT
);

CREATE TABLE measurements (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL,
    entity_id   TEXT NOT NULL REFERENCES entities(id),
    value       NUMERIC NOT NULL,
    source      TEXT
);

CREATE INDEX idx_measurements_entity_time
    ON measurements (entity_id, timestamp DESC);
```

Migration script: `db/migrations/001_initial_schema.sql`

### Adding a new entity

Entities are created manually on Castor:

```sql
INSERT INTO entities (id, unit, description, device)
VALUES ('bomba_agua.run_secs', 'seconds', 'Duración de encendido', 'bomba_agua');
```

### DB permissions

```sql
GRANT CONNECT ON DATABASE homelab TO ingestion_api;
GRANT USAGE ON SCHEMA public TO ingestion_api;
GRANT SELECT ON TABLE entities TO ingestion_api;
GRANT INSERT ON TABLE measurements TO ingestion_api;
GRANT USAGE ON SEQUENCE measurements_id_seq TO ingestion_api;
```

---

## Module map

```
app/
  main.py            FastAPI app + lifespan (init/close DB pool)
  config.py          Settings class reading from env vars; get_tokens() loads APP_TOKEN_* vars
  auth.py            verify_token() FastAPI dependency — validates Bearer token, returns app name
  database.py        asyncpg pool singleton: init_pool(), close_pool(), get_pool()
  logging_config.py  RotatingFileHandler (10 MB, 7 backups) + console handler
  notifications.py   notify_error(msg) — sends Pushover message to iphoneRSI on 500 errors
  routers/
    homeassistant.py POST /homeassistant/events → validates entity_id, inserts into measurements
db/
  migrations/
    001_initial_schema.sql  DDL for entities and measurements tables
```

---

## Conventions

### Adding a new domain endpoint

Copy `app/routers/homeassistant.py` as a template:
1. Define a Pydantic model with `entity_id` (str), `value` (Decimal), `timestamp` (datetime)
2. Validate that `entity_id` exists in `entities` — return 422 if not found
3. Insert into `measurements` with `source` populated from the auth token
4. Call `notify_error()` before raising a 500 HTTPException
5. Include the router in `app/main.py`

### Auth

All routes use `verify_token` as a FastAPI `Depends`. It reads `APP_TOKEN_<NAME>` env vars at request time — add/remove tokens by editing `.env` and restarting the container.

### Error handling pattern

```python
except Exception as exc:
    msg = f"DB insert failed for measurements: {exc}"
    logger.error(msg)
    await notify_error(msg)
    raise HTTPException(status_code=500, detail="Internal server error") from exc
```

### Logging

Use `logger = logging.getLogger(__name__)` in every module. Log each successful insert at `INFO` level including `entity_id` and `source`. Do not log sensitive values.

### Tokens

One env var per client app: `APP_TOKEN_HOMEASSISTANT`, `APP_TOKEN_OTRAAPP`, etc. Revoke by removing the var and restarting.

---

## Do NOT

- Run or generate database migrations from this codebase
- Expose DB credentials to client applications
- Catch exceptions silently without logging and notifying
- Add business logic to `main.py` — keep it to app wiring only
- Insert into `entities` from the API — the catalogue is managed manually
