from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.states import ConversationState
from app.db.models import Conversation, Message

logger = logging.getLogger(__name__)


@dataclass
class ConversationSession:
    conversation_id: str
    clinic_id: str
    phone_number: str
    state: ConversationState = ConversationState.IDLE
    data: dict = field(default_factory=dict)


async def get_or_create_session(
    db: AsyncSession, clinic_id: str, phone_number: str
) -> ConversationSession:
    from app.db.models import Clinic

    # Resolve slug → UUID if needed
    clinic_uuid = clinic_id
    if len(clinic_id) < 32:  # it's a slug, not a UUID
        result = await db.execute(select(Clinic).where(Clinic.slug == clinic_id))
        clinic_db = result.scalar_one_or_none()
        if clinic_db is None:
            raise ValueError(f"Clinic not found in DB: {clinic_id}")
        clinic_uuid = clinic_db.id

    result = await db.execute(
        select(Conversation).where(
            Conversation.clinic_id == clinic_uuid,
            Conversation.phone_number == phone_number,
        )
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        conv = Conversation(
            clinic_id=clinic_uuid,
            phone_number=phone_number,
            state=ConversationState.IDLE,
            state_data={},
        )
        db.add(conv)
        await db.flush()

    return ConversationSession(
        conversation_id=conv.id,
        clinic_id=clinic_uuid,
        phone_number=phone_number,
        state=ConversationState(conv.state),
        data=conv.state_data or {},
    )


async def save_session(db: AsyncSession, session: ConversationSession) -> None:
    await db.execute(
        update(Conversation)
        .where(Conversation.id == session.conversation_id)
        .values(
            state=session.state,
            state_data=session.data,
            last_message_at=datetime.utcnow(),
        )
    )


async def append_message(db: AsyncSession, conversation_id: str, role: str, content: str) -> None:
    db.add(Message(conversation_id=conversation_id, role=role, content=content))
