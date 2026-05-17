"""Full booking flow tests — happy path and edge cases."""
import pytest

from app.ai.base import ExtractedFields
from app.conversation.states import ConversationState


# ── IDLE → BOOKING_NAME ──────────────────────────────────────────────────────

async def test_book_keyword_to_booking_name(make_machine, make_session, mock_ai):
    session = make_session(ConversationState.IDLE)
    await make_machine.process(session, "תור")
    assert session.state == ConversationState.BOOKING_NAME
    mock_ai.classify_intent.assert_not_called()


async def test_digit_1_to_booking_name(make_machine, make_session, mock_ai):
    session = make_session(ConversationState.IDLE)
    await make_machine.process(session, "1")
    assert session.state == ConversationState.BOOKING_NAME
    mock_ai.classify_intent.assert_not_called()


async def test_book_keyword_reply_asks_name(make_machine, make_session):
    session = make_session(ConversationState.IDLE)
    reply = await make_machine.process(session, "תור")
    assert "שמך" in reply


# ── BOOKING_NAME → BOOKING_SERVICE ───────────────────────────────────────────

async def test_name_collected_from_extracted_fields(make_machine, make_session, mock_ai):
    mock_ai.extract_fields.return_value = ExtractedFields(name="שרה כהן")
    session = make_session(ConversationState.BOOKING_NAME)
    await make_machine.process(session, "שרה כהן")
    assert session.state == ConversationState.BOOKING_SERVICE
    assert session.data["name"] == "שרה כהן"


async def test_name_fallback_uses_raw_message_when_extract_returns_none(make_machine, make_session, mock_ai):
    mock_ai.extract_fields.return_value = ExtractedFields()  # all None
    session = make_session(ConversationState.BOOKING_NAME)
    await make_machine.process(session, "דנה לוי")
    assert session.data["name"] == "דנה לוי"


async def test_name_reply_lists_services(make_machine, make_session, mock_ai):
    mock_ai.extract_fields.return_value = ExtractedFields(name="שרה")
    session = make_session(ConversationState.BOOKING_NAME)
    reply = await make_machine.process(session, "שרה")
    assert "עיסוי" in reply
    assert "רפלקסולוגיה" in reply


# ── BOOKING_SERVICE → BOOKING_DATE ───────────────────────────────────────────

async def test_service_selected_by_number(make_machine, make_session):
    session = make_session(ConversationState.BOOKING_SERVICE, {"name": "שרה"})
    await make_machine.process(session, "1")
    assert session.state == ConversationState.BOOKING_DATE
    assert session.data["service_id"] == "massage"
    assert session.data["service_name"] == "עיסוי"


async def test_service_selected_by_hebrew_name(make_machine, make_session):
    session = make_session(ConversationState.BOOKING_SERVICE, {"name": "שרה"})
    await make_machine.process(session, "רפלקסולוגיה")
    assert session.state == ConversationState.BOOKING_DATE
    assert session.data["service_id"] == "reflexology"


async def test_invalid_service_stays_in_booking_service(make_machine, make_session):
    session = make_session(ConversationState.BOOKING_SERVICE, {"name": "שרה"})
    reply = await make_machine.process(session, "ספא")
    assert session.state == ConversationState.BOOKING_SERVICE
    assert "עיסוי" in reply  # services re-listed


# ── BOOKING_DATE → BOOKING_TIME ───────────────────────────────────────────────

async def test_date_fetches_slots_and_transitions_to_booking_time(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields(date_text="מחר")
    mock_calendar.get_available_slots_text.return_value = ["10:00", "11:00", "12:00"]
    session = make_session(
        ConversationState.BOOKING_DATE,
        {"name": "שרה", "service_id": "massage", "service_name": "עיסוי"},
    )
    reply = await make_machine.process(session, "מחר")
    assert session.state == ConversationState.BOOKING_TIME
    assert session.data["available_slots"] == ["10:00", "11:00", "12:00"]
    mock_calendar.get_available_slots_text.assert_awaited_once_with("מחר", "massage")
    assert "10:00" in reply


async def test_date_fallback_uses_raw_message(make_machine, make_session, mock_ai, mock_calendar):
    mock_ai.extract_fields.return_value = ExtractedFields()  # date_text=None
    session = make_session(
        ConversationState.BOOKING_DATE,
        {"name": "שרה", "service_id": "massage", "service_name": "עיסוי"},
    )
    await make_machine.process(session, "23/06")
    assert session.data["date_text"] == "23/06"


async def test_no_slots_shows_apology_and_stays_in_booking_date(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields(date_text="שבת")
    mock_calendar.get_available_slots_text.return_value = []
    session = make_session(
        ConversationState.BOOKING_DATE,
        {"name": "שרה", "service_id": "massage", "service_name": "עיסוי"},
    )
    reply = await make_machine.process(session, "שבת")
    assert session.state == ConversationState.BOOKING_DATE  # stays so user can retry
    assert "אין שעות פנויות" in reply


# ── BOOKING_TIME → BOOKING_CONFIRM ────────────────────────────────────────────

async def test_time_selected_by_exact_string(make_machine, make_session):
    session = make_session(
        ConversationState.BOOKING_TIME,
        {
            "name": "שרה",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "available_slots": ["10:00", "11:00", "12:00"],
        },
    )
    reply = await make_machine.process(session, "10:00")
    assert session.state == ConversationState.BOOKING_CONFIRM
    assert session.data["time_text"] == "10:00"
    assert "סיכום" in reply


async def test_time_selected_by_index(make_machine, make_session):
    session = make_session(
        ConversationState.BOOKING_TIME,
        {
            "name": "שרה",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "available_slots": ["10:00", "11:00", "12:00"],
        },
    )
    await make_machine.process(session, "2")
    assert session.data["time_text"] == "11:00"


async def test_invalid_time_stays_in_booking_time(make_machine, make_session):
    session = make_session(
        ConversationState.BOOKING_TIME,
        {
            "name": "שרה",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "available_slots": ["10:00", "11:00"],
        },
    )
    reply = await make_machine.process(session, "99:99")
    assert session.state == ConversationState.BOOKING_TIME
    assert "10:00" in reply  # slots re-shown


# ── BOOKING_CONFIRM → IDLE ────────────────────────────────────────────────────

async def test_confirmation_yes_creates_appointment(make_machine, make_session, mock_ai, mock_calendar, fake_appt):
    mock_ai.extract_fields.return_value = ExtractedFields()  # confirmed=None → raw text check
    mock_calendar.create_appointment_from_session.return_value = fake_appt
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
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


@pytest.mark.parametrize("confirm_word", ["אישור", "בסדר", "yes", "ok", "1"])
async def test_confirmation_keyword_variants_create_appointment(
    confirm_word, make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    mock_calendar.create_appointment_from_session.return_value = fake_appt
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
            "name": "שרה",
            "service_id": "massage",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "time_text": "10:00",
        },
    )
    await make_machine.process(session, confirm_word)
    mock_calendar.create_appointment_from_session.assert_awaited_once()


async def test_confirmation_gpt_extracted_true_creates_appointment(
    make_machine, make_session, mock_ai, mock_calendar, fake_appt
):
    mock_ai.extract_fields.return_value = ExtractedFields(confirmed=True)
    mock_calendar.create_appointment_from_session.return_value = fake_appt
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
            "name": "שרה",
            "service_id": "massage",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "time_text": "10:00",
        },
    )
    await make_machine.process(session, "בהחלט כן בבקשה")
    mock_calendar.create_appointment_from_session.assert_awaited_once()


async def test_confirmation_no_resets_without_creating_appointment(
    make_machine, make_session, mock_ai, mock_calendar
):
    mock_ai.extract_fields.return_value = ExtractedFields()
    session = make_session(
        ConversationState.BOOKING_CONFIRM,
        {
            "name": "שרה",
            "service_id": "massage",
            "service_name": "עיסוי",
            "date_text": "מחר",
            "time_text": "10:00",
        },
    )
    reply = await make_machine.process(session, "לא")
    assert session.state == ConversationState.IDLE
    assert session.data == {}
    mock_calendar.create_appointment_from_session.assert_not_awaited()
    assert "ביטלנו" in reply
