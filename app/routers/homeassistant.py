import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import verify_token
from app.database import get_pool
from app.notifications import notify_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/homeassistant", tags=["homeassistant"])


class HAEvent(BaseModel):
    entity_id: str
    value: Decimal
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def ingest_event(
    event: HAEvent,
    app_name: str = Depends(verify_token),
) -> dict:
    pool = get_pool()

    entity = await pool.fetchrow("SELECT id FROM entities WHERE id = $1", event.entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown entity_id: {event.entity_id}",
        )

    try:
        await pool.execute(
            """
            INSERT INTO measurements (timestamp, entity_id, value, source)
            VALUES ($1, $2, $3, $4)
            """,
            event.timestamp,
            event.entity_id,
            event.value,
            app_name,
        )
    except Exception as exc:
        msg = f"DB insert failed for measurements: {exc}"
        logger.error(msg)
        await notify_error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc

    logger.info("measurements insert — entity_id=%s source=%s", event.entity_id, app_name)
    return {"status": "ok"}
