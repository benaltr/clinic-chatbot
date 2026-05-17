import pytest

from app.conversation.session import ConversationSession
from app.conversation.state_machine import ConversationStateMachine
from app.conversation.states import ConversationState


@pytest.mark.asyncio
async def test_greeting_response(demo_clinic, mock_ai, mock_calendar):
    machine = ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)
    session = ConversationSession(
        conversation_id="test-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.IDLE,
    )

    reply = await machine.process(session, "שלום")

    assert "קליניקת טסט" in reply
    assert "קביעת תור" in reply


@pytest.mark.asyncio
async def test_book_keyword_skips_gpt(demo_clinic, mock_ai, mock_calendar):
    """The keyword 'תור' should jump straight to BOOKING_NAME without calling GPT."""
    machine = ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)
    session = ConversationSession(
        conversation_id="test-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.IDLE,
    )

    reply = await machine.process(session, "תור")

    assert session.state == ConversationState.BOOKING_NAME
    assert "שמך" in reply
    mock_ai.classify_intent.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_keyword(demo_clinic, mock_ai, mock_calendar):
    mock_calendar.find_appointment.return_value = None  # no appointment → ask for ref
    machine = ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)
    session = ConversationSession(
        conversation_id="test-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.IDLE,
    )

    reply = await machine.process(session, "ביטול")

    assert session.state == ConversationState.CANCEL_LOOKUP
    assert "אסמכתא" in reply


@pytest.mark.asyncio
async def test_full_name_collection(demo_clinic, mock_ai, mock_calendar):
    from dataclasses import dataclass
    from unittest.mock import AsyncMock

    @dataclass
    class FakeFields:
        name: str | None = "יוסי כהן"
        service: str | None = None
        date_text: str | None = None
        time_text: str | None = None
        confirmed: bool | None = None

    mock_ai.extract_fields = AsyncMock(return_value=FakeFields())

    machine = ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)
    session = ConversationSession(
        conversation_id="test-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.BOOKING_NAME,
    )

    reply = await machine.process(session, "יוסי כהן")

    assert session.state == ConversationState.BOOKING_SERVICE
    assert session.data.get("name") == "יוסי כהן"
    assert "עיסוי" in reply


@pytest.mark.asyncio
async def test_handoff_keyword_detected(demo_clinic, mock_ai, mock_calendar):
    machine = ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)
    session = ConversationSession(
        conversation_id="test-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.IDLE,
    )

    # Simulate the handoff detection in message_service (state machine checks done there)
    # Direct test: human keyword triggers handoff
    reply = await machine.process(session, "נציג")

    assert session.state == ConversationState.HUMAN_HANDOFF
    assert "נציג" in reply
