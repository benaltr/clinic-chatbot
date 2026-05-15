import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.messaging.meta_provider import MetaProvider
from app.services import message_service
from app.tenants.models import ClinicConfig
from app.tenants.registry import registry

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_clinic_by_number(number: str) -> ClinicConfig | None:
    """Look up clinic by display phone number from Meta webhook metadata."""
    config = registry.get_by_number(number)
    if config is None:
        # Try without country code prefix variations
        for stored_number, cfg in registry._by_number.items():
            if stored_number.replace("+", "").replace("-", "") in number.replace("+", "").replace("-", ""):
                return cfg
    return config


@router.get("/webhook/meta")
async def meta_webhook_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """Meta webhook verification handshake (GET request)."""
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")

    # Accept if any registered clinic's verify token matches
    for config in registry.all_configs():
        token = config.whatsapp.meta_verify_token or settings.meta_verify_token
        if hub_verify_token == token:
            return int(hub_challenge)

    # Fallback to global verify token
    if hub_verify_token == settings.meta_verify_token:
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verify token mismatch")


@router.post("/webhook/meta")
async def meta_webhook_receive(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive incoming WhatsApp messages from Meta Cloud API."""
    payload = await request.json()

    # Acknowledge immediately — Meta requires 200 within 20s
    # We'll process synchronously here (for scale, move to background task)

    # Extract the to-number from metadata to route to the right clinic
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        metadata = value.get("metadata", {})
        display_number = metadata.get("display_phone_number", "")
        phone_number_id = metadata.get("phone_number_id", "")
    except (KeyError, IndexError):
        return {"status": "ok"}

    # Resolve clinic by phone number
    clinic = _get_clinic_by_number(display_number) or _get_clinic_by_id_from_meta(phone_number_id)
    if clinic is None:
        logger.warning("No clinic found for number: %s (id: %s)", display_number, phone_number_id)
        return {"status": "ok"}

    # Use this clinic's MetaProvider to parse the message
    meta = MetaProvider(
        access_token=clinic.whatsapp.meta_access_token or settings.meta_access_token,
        phone_number_id=clinic.whatsapp.meta_phone_number_id or settings.meta_phone_number_id,
        verify_token=clinic.whatsapp.meta_verify_token or settings.meta_verify_token,
    )
    incoming = meta.parse_incoming(payload)
    if incoming is None:
        return {"status": "ok"}

    await message_service.handle_incoming(incoming, clinic, db)
    return {"status": "ok"}


def _get_clinic_by_id_from_meta(phone_number_id: str) -> ClinicConfig | None:
    for config in registry.all_configs():
        if config.whatsapp.meta_phone_number_id == phone_number_id:
            return config
    return None
