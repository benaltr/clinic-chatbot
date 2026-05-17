"""Full update flow tests.

Note: UPDATE_FIELD transitions to BOOKING_DATE, which then flows through the
normal booking sub-flow (BOOKING_TIME → BOOKING_CONFIRM). At BOOKING_CONFIRM,
create_appointment_from_session is called (not update_appointment_from_session).
UPDATE_CONFIRM is dead code and is not tested here.
"""
import pytest

from app.ai.base import ExtractedFields
from app.conversation.states import ConversationState


# ── IDLE → auto-lookup by phone ───────────────────────────────────────────────

async def test_update_keyword_auto_lookup_found_asks_date(
    make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    """Phone lookup finds appointment, no date pre-extracted → ask for new date."""
    mock_calendar.find_appointment.return_value = fake_appt
    mock_ai.extract_fields.return_value = ExtractedFields()  # no date_text
    session = make_session(ConversationState.IDLE, phone="+972541111111")
    reply = await make_machine.process(session, "שינוי")
    assert session.state == ConversationState.BOOKING_DATE
    assert session.data["update_appt_id"] == "appt-uuid-001"
    assert session.data["name"] == "שרה כהן"
    mock_ai.classify_intent.assert_not_called()
    assert "תאריך" in reply


async def test_update_with_date_in_message_goes_to_booking_time(
    make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    """AI extracts date from initial message → fetch slots and go to BOOKING_TIME."""
    from app.ai.base import Intent
    mock_calendar.find_appointment.return_value = fake_appt
    mock_calendar.get_available_slots_text.return_value = ["14:00", "15:00"]
    mock_ai.classify_intent.return_value = Intent(action="update")
    mock_ai.extract_fields.return_value = ExtractedFields(date_text="מחר")
    session = make_session(ConversationState.IDLE, phone="+972541111111")
    reply = await make_machine.process(session, "רוצה לשנות את התור למחר")
    assert session.state == ConversationState.BOOKING_TIME
    assert session.data["date_text"] == "מחר"
    assert "14:00" in reply


async def test_update_with_date_and_time_skips_to_confirm(
    make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    """AI extracts both date and time → skip straight to BOOKING_CONFIRM."""
    from app.ai.base import Intent
    mock_calendar.find_appointment.return_value = fake_appt
    mock_calendar.get_available_slots_text.return_value = ["14:00", "15:00"]
    mock_ai.classify_intent.return_value = Intent(action="update")
    mock_ai.extract_fields.return_value = ExtractedFields(date_text="מחר", time_text="14:00")
    session = make_session(ConversationState.IDLE, phone="+972541111111")
    reply = await make_machine.process(session, "שנה לי למחר בשתיים")
    assert session.state == ConversationState.BOOKING_CONFIRM
    assert session.data["time_text"] == "14:00"
    assert "סיכום" in reply


async def test_update_keyword_auto_lookup_not_found_falls_back(
    make_machine, make_session, mock_ai, mock_calendar
):
    """No appointment found by phone → ask for ref code."""
    mock_calendar.find_appointment.return_value = None
    session = make_session(ConversationState.IDLE)
    reply = await make_machine.process(session, "שינוי")
    assert session.state == ConversationState.UPDATE_LOOKUP
    mock_ai.classify_intent.assert_not_called()
    assert "אסמכתא" in reply


@pytest.mark.parametrize("kw", ["עדכון", "לשנות", "לעדכן", "3"])
async def test_update_keyword_variants_fallback(kw, make_machine, make_session, mock_ai, mock_calendar):
    """All update keywords fall back to UPDATE_LOOKUP when no appointment found."""
    mock_calendar.find_appointment.return_value = None
    session = make_session(ConversationState.IDLE)
    await make_machine.process(session, kw)
    assert session.state == ConversationState.UPDATE_LOOKUP
    mock_ai.classify_intent.assert_not_called()


# ── UPDATE_LOOKUP → UPDATE_FIELD ─────────────────────────────────────────────

async def test_ref_found_transitions_to_update_field(
    make_machine, make_session, mock_calendar, fake_appt
):
    mock_calendar.find_appointment.return_value = fake_appt
    session = make_session(ConversationState.UPDATE_LOOKUP, phone="+972541111111")
    reply = await make_machine.process(session, "TES-001")
    assert session.state == ConversationState.UPDATE_FIELD
    assert session.data["update_appt_id"] == "appt-uuid-001"
    assert session.data["name"] == "שרה כהן"
    mock_calendar.find_appointment.assert_awaited_once_with("TES-001", "+972541111111")


async def test_ref_found_with_prefilled_date_and_time_skips_to_confirm(
    make_machine, make_session, mock_calendar, mock_ai, fake_appt
):
    mock_calendar.find_appointment.return_value = fake_appt
    mock_calendar.get_available_slots_text.return_value = ["14:00", "15:00"]
    session = make_session(
        ConversationState.UPDATE_LOOKUP,
        data={"prefilled_date": "מחר", "prefilled_time": "14:00"},
        phone="+972541111111",
    )
    reply = await make_machine.process(session, "TES-001")
    assert session.state == ConversationState.BOOKING_CONFIRM
    assert session.data["time_text"] == "14:00"
    assert "סיכום" in reply


async def test_ref_found_with_prefilled_date_only_goes_to_booking_time(
    make_machine, make_session, mock_calendar, fake_appt
):
    mock_calendar.find_appointment.return_value = fake_appt
    mock_calendar.get_available_slots_text.return_value = ["14:00", "15:00"]
    session = make_session(
        ConversationState.UPDATE_LOOKUP,
        data={"prefilled_date": "מחר"},
        phone="+972541111111",
    )
    reply = await make_machine.process(session, "TES-001")
    assert session.state == ConversationState.BOOKING_TIME
    assert "14:00" in reply


async def test_ref_not_found_stays_in_update_lookup(make_machine, make_session, mock_calendar):
    mock_calendar.find_appointment.return_value = None
    session = make_session(ConversationState.UPDATE_LOOKUP)
    reply = await make_machine.process(session, "TES-999")
    assert session.state == ConversationState.UPDATE_LOOKUP
    assert "לא מצאתי" in reply


# ── UPDATE_FIELD → BOOKING_DATE ──────────────────────────────────────────────

async def test_update_field_transitions_to_booking_date(make_machine, make_session):
    session = make_session(
        ConversationState.UPDATE_FIELD,
        {"update_appt_id": "appt-uuid-001", "name": "שרה כהן"},
    )
    reply = await make_machine.process(session, "1")
    assert session.state == ConversationState.BOOKING_DATE
    assert "תאריך" in reply


# ── BOOKING_DATE → BOOKING_TIME (in update context) ──────────────────────────

async def test_update_new_date_fetches_slots(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields(date_text="מחר")
    mock_calendar.get_available_slots_text.return_value = ["09:00", "10:00"]
    # service_id may be missing in update flow — test that it still works
    session = make_session(
        ConversationState.BOOKING_DATE,
        {
            "update_appt_id": "appt-uuid-001",
            "name": "שרה כהן",
        },
    )
    reply = await make_machine.process(session, "מחר")
    assert session.state == ConversationState.BOOKING_TIME
    assert session.data["available_slots"] == ["09:00", "10:00"]
    assert "09:00" in reply


# ── BOOKING_TIME → BOOKING_CONFIRM (in update context) ───────────────────────

async def test_update_new_time_transitions_to_confirm(make_machine, make_session):
    session = make_session(
        ConversationState.BOOKING_TIME,
        {
            "update_appt_id": "appt-uuid-001",
            "name": "שרה כהן",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "available_slots": ["09:00", "10:00"],
        },
    )
    reply = await make_machine.process(session, "10:00")
    assert session.state == ConversationState.BOOKING_CONFIRM
    assert "סיכום" in reply


# ── BOOKING_CONFIRM → IDLE (in update context) ───────────────────────────────

async def test_update_confirmation_yes_calls_create_appointment(
    make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    mock_calendar.create_appointment_from_session.return_value = fake_appt
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
            "update_appt_id": "appt-uuid-001",
            "name": "שרה כהן",
            "service_id": "massage",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "time_text": "10:00",
        },
    )
    reply = await make_machine.process(session, "כן")
    assert session.state == ConversationState.IDLE
    assert session.data == {}
    mock_calendar.create_appointment_from_session.assert_awaited_once()
    assert "TES-001" in reply


async def test_update_confirmation_no_resets_without_calendar_call(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
            "update_appt_id": "appt-uuid-001",
            "name": "שרה כהן",
            "service_id": "massage",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "time_text": "10:00",
        },
    )
    await make_machine.process(session, "לא")
    assert session.state == ConversationState.IDLE
    assert session.data == {}
    mock_calendar.create_appointment_from_session.assert_not_awaited()
    mock_calendar.update_appointment_from_session.assert_not_awaited()
