"""Full cancel flow tests — happy path, not-found, and declined cancel."""
import pytest

from app.ai.base import ExtractedFields
from app.conversation.states import ConversationState


# ── IDLE → CANCEL_LOOKUP ──────────────────────────────────────────────────────

async def test_cancel_keyword_to_cancel_lookup(make_machine, make_session, mock_ai):
    session = make_session(ConversationState.IDLE)
    reply = await make_machine.process(session, "ביטול")
    assert session.state == ConversationState.CANCEL_LOOKUP
    mock_ai.classify_intent.assert_not_called()
    assert "אסמכתא" in reply


async def test_cancel_digit_2_to_cancel_lookup(make_machine, make_session, mock_ai):
    session = make_session(ConversationState.IDLE)
    await make_machine.process(session, "2")
    assert session.state == ConversationState.CANCEL_LOOKUP
    mock_ai.classify_intent.assert_not_called()


# ── CANCEL_LOOKUP → CANCEL_CONFIRM ───────────────────────────────────────────

async def test_ref_found_transitions_to_cancel_confirm(
    make_machine, make_session, mock_calendar, fake_appt
):
    mock_calendar.find_appointment.return_value = fake_appt
    session = make_session(ConversationState.CANCEL_LOOKUP, phone="+972541111111")
    reply = await make_machine.process(session, "TES-001")
    assert session.state == ConversationState.CANCEL_CONFIRM
    assert session.data["cancel_appt_id"] == "appt-uuid-001"
    assert session.data["cancel_service_name"] == "עיסוי"
    mock_calendar.find_appointment.assert_awaited_once_with("TES-001", "+972541111111")
    assert "עיסוי" in reply
    assert "23/06/2025" in reply


async def test_appointment_not_found_stays_in_cancel_lookup(
    make_machine, make_session, mock_calendar
):
    mock_calendar.find_appointment.return_value = None
    session = make_session(ConversationState.CANCEL_LOOKUP)
    reply = await make_machine.process(session, "TES-999")
    assert session.state == ConversationState.CANCEL_LOOKUP
    assert "לא מצאתי" in reply


# ── CANCEL_CONFIRM → IDLE ─────────────────────────────────────────────────────

async def test_cancel_confirmed_cancels_appointment_and_resets_to_idle(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    mock_calendar.cancel_appointment.return_value = True
    session = make_session(
        ConversationState.CANCEL_CONFIRM,
        {
            "cancel_appt_id": "appt-uuid-001",
            "cancel_service_name": "עיסוי",
            "cancel_date_text": "23/06/2025",
            "cancel_time_text": "10:00",
        },
    )
    reply = await make_machine.process(session, "כן")
    assert session.state == ConversationState.IDLE
    assert session.data == {}
    mock_calendar.cancel_appointment.assert_awaited_once_with("appt-uuid-001")
    assert "בוטל" in reply


async def test_cancel_declined_does_not_cancel_appointment(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    session = make_session(
        ConversationState.CANCEL_CONFIRM,
        {
            "cancel_appt_id": "appt-uuid-001",
            "cancel_service_name": "עיסוי",
            "cancel_date_text": "23/06/2025",
            "cancel_time_text": "10:00",
        },
    )
    reply = await make_machine.process(session, "לא")
    assert session.state == ConversationState.IDLE
    assert session.data == {}
    mock_calendar.cancel_appointment.assert_not_awaited()
    assert "לא בוטל" in reply


async def test_cancel_lookup_by_phone_number(make_machine, make_session, mock_calendar, fake_appt):
    mock_calendar.find_appointment.return_value = fake_appt
    session = make_session(ConversationState.CANCEL_LOOKUP, phone="+972541111111")
    await make_machine.process(session, "+972541111111")
    mock_calendar.find_appointment.assert_awaited_once_with("+972541111111", "+972541111111")
    assert session.state == ConversationState.CANCEL_CONFIRM
