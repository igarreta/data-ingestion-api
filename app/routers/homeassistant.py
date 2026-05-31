import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import verify_token
from app.database import get_pool
from app.notifications import notify_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/homeassistant", tags=["homeassistant"])


class HAEvent(BaseModel):
    entity: str
    value: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def ingest_event(
    event: HAEvent,
    app_name: str = Depends(verify_token),
) -> dict:
    pool = get_pool()
    try:
        await pool.execute(
            """
            INSERT INTO ha_events (entity, value, timestamp)
            VALUES ($1, $2, $3)
            """,
            event.entity,
            event.value,
            event.timestamp,
        )
    except Exception as exc:
        msg = f"DB insert failed for ha_events: {exc}"
        logger.error(msg)
        await notify_error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc

    logger.info("ha_events insert — entity=%s origin=%s", event.entity, app_name)
    return {"status": "ok"}
