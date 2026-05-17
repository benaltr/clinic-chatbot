"""Unit tests for Hebrew response templates in handlers.py."""
from app.conversation import handlers


def test_greeting_contains_clinic_name(demo_clinic):
    result = handlers.greeting(demo_clinic)
    assert "קליניקת טסט" in result


def test_greeting_has_all_menu_options(demo_clinic):
    result = handlers.greeting(demo_clinic)
    assert "קביעת תור" in result
    assert "ביטול תור" in result
    assert "שינוי" in result
    assert "שאלה" in result
    assert "נציג" in result


def test_greeting_has_numbered_emoji_items(demo_clinic):
    result = handlers.greeting(demo_clinic)
    assert "1️⃣" in result
    assert "5️⃣" in result


def test_ask_name_contains_prompt():
    result = handlers.ask_name()
    assert "שמך" in result


def test_ask_service_lists_all_services(demo_clinic):
    result = handlers.ask_service(demo_clinic)
    assert "עיסוי" in result
    assert "רפלקסולוגיה" in result
    assert "1️⃣" in result
    assert "2️⃣" in result


def test_ask_date_contains_patient_name():
    result = handlers.ask_date("שרה")
    assert "שרה" in result
    assert "תאריך" in result


def test_ask_time_with_slots_shows_numbered_list():
    result = handlers.ask_time("מחר", ["10:00", "11:00", "12:00"])
    assert "10:00" in result
    assert "11:00" in result
    assert "1️⃣" in result
    assert "מחר" in result


def test_ask_time_empty_slots_shows_apology():
    result = handlers.ask_time("שבת", [])
    assert "מצטערים" in result
    assert "אין שעות פנויות" in result
    assert "שבת" in result


def test_booking_confirm_contains_all_booking_details():
    result = handlers.booking_confirm("שרה כהן", "עיסוי", "23/06/2025", "10:00")
    assert "שרה כהן" in result
    assert "עיסוי" in result
    assert "23/06/2025" in result
    assert "10:00" in result
    assert "סיכום" in result
    assert "כן" in result


def test_booking_done_contains_ref_code():
    result = handlers.booking_done("TES-001", "23/06/2025", "10:00")
    assert "TES-001" in result
    assert "תורך נקבע" in result


def test_ask_cancel_ref_has_ref_and_phone_option():
    result = handlers.ask_cancel_ref()
    assert "אסמכתא" in result
    assert "טלפון" in result


def test_cancel_confirm_contains_appointment_details():
    result = handlers.cancel_confirm("עיסוי", "23/06/2025", "10:00")
    assert "עיסוי" in result
    assert "23/06/2025" in result
    assert "10:00" in result


def test_cancel_done_contains_success_word():
    result = handlers.cancel_done()
    assert "בוטל" in result


def test_appointment_not_found_apologizes():
    result = handlers.appointment_not_found()
    assert "לא מצאתי" in result


def test_ask_update_what_lists_options():
    result = handlers.ask_update_what()
    assert "תאריך" in result
    assert "1️⃣" in result


def test_update_done_contains_ref_code():
    result = handlers.update_done("TES-002")
    assert "TES-002" in result


def test_human_handoff_returns_message_verbatim():
    assert handlers.human_handoff("הועברת לנציג.") == "הועברת לנציג."


def test_error_message_mentions_technical_issue():
    result = handlers.error_message()
    assert "טכנית" in result
    assert "נציג" in result


def test_unknown_input_shows_common_options():
    result = handlers.unknown_input()
    assert "תור" in result
    assert "ביטול" in result
