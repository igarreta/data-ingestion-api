# Client guide — `sensor.bomba_agua_run_secs`

How a client application sends measurements for the **water-pump run-time**
sensor to `data-ingestion-api`.

## Entity

| Field | Value |
|---|---|
| `entity_id` | `sensor.bomba_agua_run_secs` |
| Domain | `sensor` (numeric, read-only) |
| Unit | seconds |
| Meaning | How many seconds the water pump ran |
| Device | `bomba_agua` |
| `source` | set automatically from your API token (do **not** send it) |

The entity must already exist in the `entities` catalogue on the server. It does
— if you get a `422`, contact the sysadmin; the client must not create entities.

## Endpoint

```
POST http://192.168.1.3:8000/homeassistant/events
```

- `192.168.1.3` is the Proxmox host (gr-srv03) on the LAN, port-forwarded to
  Cygnus — works with the internet **offline**. Use this from Home Assistant.
- Internal (from the `10.0.100.0/24` network): `http://10.0.100.10:8000`.
- Fallback (off-LAN / remote): `http://100.96.140.37:8000` (Cygnus via Tailscale,
  needs internet).
- `Content-Type: application/json`
- Auth: `Authorization: Bearer <APP_TOKEN_HOMEASSISTANT>` — ask the sysadmin for
  the token; never hard-code it in a shared repo.

## Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `entity_id` | string | yes | Must be exactly `sensor.bomba_agua_run_secs` |
| `value` | number | yes | Seconds the pump ran (e.g. `312`) |
| `timestamp` | string (ISO-8601) | no | Defaults to server time (UTC) on receipt |

```json
{
  "entity_id": "sensor.bomba_agua_run_secs",
  "value": 312
}
```

Send one event each time the pump finishes a run, with `value` = the duration of
that run in seconds.

## Examples

### curl

```bash
curl -X POST http://192.168.1.3:8000/homeassistant/events \
  -H "Authorization: Bearer $APP_TOKEN_HOMEASSISTANT" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"sensor.bomba_agua_run_secs","value":312}'
```

### Home Assistant `rest_command`

```yaml
rest_command:
  bomba_agua_run_secs:
    url: "http://192.168.1.3:8000/homeassistant/events"
    method: POST
    headers:
      Authorization: !secret data_ingestion_api_token
      Content-Type: application/json
    payload: >
      {"entity_id":"sensor.bomba_agua_run_secs","value":{{ value }}}
    content_type: application/json
```

Call it from an automation when the pump switches off, passing the elapsed
seconds:

```yaml
action:
  - service: rest_command.bomba_agua_run_secs
    data:
      value: "{{ (now() - state_attr('switch.bomba_agua','last_changed_ts')) | int }}"
```

## Responses

| Status | Meaning | Action |
|---|---|---|
| `201 Created` | `{"status":"ok"}` — measurement stored | none |
| `401 Unauthorized` | Missing/invalid Bearer token | check the token |
| `422 Unprocessable Entity` | Unknown `entity_id` or body fails validation | fix payload; if the id is correct, contact sysadmin |
| `500 Internal Server Error` | Server/DB failure (sysadmin is paged via Pushover) | retry later |
