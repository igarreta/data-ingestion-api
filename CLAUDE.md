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
| **DB schema** | Managed manually on Castor — this API only validates and inserts, never runs migrations |
| **Deployment** | `podman-compose up -d --build` on Cygnus |

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
    homeassistant.py POST /homeassistant/events → inserts into ha_events table
```

---

## Conventions

### Adding a new domain endpoint

Copy `app/routers/homeassistant.py` as a template:
1. Define a Pydantic model for the request body
2. Write the `INSERT` query for the target table on Castor
3. Call `notify_error()` before raising a 500 HTTPException
4. Include the router in `app/main.py`

### Auth

All routes use `verify_token` as a FastAPI `Depends`. It reads `APP_TOKEN_<NAME>` env vars at request time — add/remove tokens by editing `.env` and restarting the container.

### Error handling pattern

```python
except Exception as exc:
    msg = f"DB insert failed for <table>: {exc}"
    logger.error(msg)
    await notify_error(msg)
    raise HTTPException(status_code=500, detail="Internal server error") from exc
```

### Logging

Use `logger = logging.getLogger(__name__)` in every module. Log each successful insert at `INFO` level including entity/origin. Do not log sensitive values.

### Tokens

One env var per client app: `APP_TOKEN_HOMEASSISTANT`, `APP_TOKEN_OTRAAPP`, etc. Revoke by removing the var and restarting.

---

## Database tables

### `ha_events` (Home Assistant)

Suggested schema to create on Castor:

```sql
CREATE TABLE ha_events (
    id        BIGSERIAL PRIMARY KEY,
    entity    TEXT        NOT NULL,
    value     TEXT        NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);
```

---

## Do NOT

- Run or generate database migrations from this codebase
- Expose DB credentials to client applications
- Catch exceptions silently without logging and notifying
- Add business logic to `main.py` — keep it to app wiring only
