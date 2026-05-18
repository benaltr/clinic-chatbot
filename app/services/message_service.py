from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.calendar import get_calendar_provider
from app.conversation.session import append_message, get_or_create_session, get_recent_messages, save_session
from app.conversation.states import ConversationState
from app.core.config import settings
from app.messaging.base import IncomingMessage, OutgoingMessage
from app.messaging.meta_provider import MetaProvider
from app.tenants.models import ClinicConfig

logger = logging.getLogger(__name__)

_ai_provider = OpenAIProvider(api_key=settings.openai_api_key)


def _get_messaging_provider(clinic: ClinicConfig) -> MetaProvider:
    cfg = clinic.whatsapp
    return MetaProvider(
        access_token=cfg.meta_access_token or settings.meta_access_token,
        phone_number_id=cfg.meta_phone_number_id or settings.meta_phone_number_id,
        verify_token=cfg.meta_verify_token or settings.meta_verify_token,
        api_version=settings.meta_api_version,
    )


async def handle_incoming(msg: IncomingMessage, clinic: ClinicConfig, db: AsyncSession) -> None:
    session = await get_or_create_session(db, clinic.clinic_id, msg.from_number)

    # Don't respond when a human agent has taken over
    if session.state == ConversationState.HUMAN_HANDOFF:
        return

    # Fast-path handoff keywords — skip AI call entirely
    if any(kw in msg.body for kw in clinic.handoff.trigger_keywords):
        session.state = ConversationState.HUMAN_HANDOFF
        session.data = {}
        await _send_and_persist(msg, clinic.handoff.message, clinic, session, db)
        return

    history = await get_recent_messages(db, session.conversation_id, limit=20)
    calendar = get_calendar_provider(clinic, db)

    try:
        reply = await _ai_provider.converse(
            message=msg.body,
            history=history,
            session=session,
            clinic=clinic,
            calendar=calendar,
        )
    except Exception:
        logger.exception("AI converse failed for %s", msg.from_number)
        reply = "מצטערים, נתקלנו בבעיה טכנית. אנא נסה שוב או שלח *נציג* לעזרה."

    await _send_and_persist(msg, reply, clinic, session, db)


async def _send_and_persist(msg, reply, clinic, session, db) -> None:
    await append_message(db, session.conversation_id, "user", msg.body)
    await append_message(db, session.conversation_id, "assistant", reply)
    await save_session(db, session)
    await db.commit()

    messaging = _get_messaging_provider(clinic)
    await messaging.send_message(OutgoingMessage(to_number=msg.from_number, body=reply))
