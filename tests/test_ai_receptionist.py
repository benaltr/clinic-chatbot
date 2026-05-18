"""Tests for OpenAIProvider.converse() — the AI receptionist tool-call loop."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.openai_provider import OpenAIProvider
from app.calendar.base import AppointmentResult
from app.conversation.session import ConversationSession
from app.conversation.states import ConversationState


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_text_response(text: str):
    """Simulate an OpenAI response that returns plain text (no tools)."""
    msg = SimpleNamespace(content=text, tool_calls=None)
    choice = SimpleNamespace(finish_reason="stop", message=msg)
    return SimpleNamespace(choices=[choice])


def _make_tool_response(tool_name: str, args: dict, call_id: str = "call-001"):
    """Simulate an OpenAI response that calls a single tool."""
    tc = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=tool_name, arguments=json.dumps(args)),
    )
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    choice = SimpleNamespace(finish_reason="tool_calls", message=msg)
    return SimpleNamespace(choices=[choice])


def _fake_session() -> ConversationSession:
    return ConversationSession(
        conversation_id="test-conv",
        clinic_id="test_wellness",
        phone_number="+972541111111",
    )


def _fake_appt(**kwargs) -> AppointmentResult:
    defaults = dict(
        id="appt-001",
        ref_code="TES-001",
        patient_name="שרה כהן",
        service_name="עיסוי",
        date_text="25/06/2025",
        time_text="10:00",
    )
    defaults.update(kwargs)
    return AppointmentResult(**defaults)


# ── converse() — plain text path ───────────────────────────────────────────────

async def test_converse_plain_text_returned(demo_clinic):
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()

    with patch.object(provider._client.chat.completions, "create", new=AsyncMock(
        return_value=_make_text_response("שלום! איך אוכל לעזור?")
    )):
        reply = await provider.converse("שלום", [], session, demo_clinic, calendar)

    assert reply == "שלום! איך אוכל לעזור?"


async def test_converse_history_included_in_messages(demo_clinic):
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    history = [{"role": "user", "content": "שלום"}, {"role": "assistant", "content": "היי!"}]

    captured_calls = []

    async def mock_create(**kwargs):
        captured_calls.append(kwargs["messages"])
        return _make_text_response("ok")

    with patch.object(provider._client.chat.completions, "create", new=mock_create):
        await provider.converse("רוצה לקבוע תור", history, session, demo_clinic, calendar)

    messages = captured_calls[0]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "שלום"}
    assert messages[2] == {"role": "assistant", "content": "היי!"}
    assert messages[-1]["content"] == "רוצה לקבוע תור"


# ── converse() — tool call paths ──────────────────────────────────────────────

async def test_converse_find_appointment_then_text(demo_clinic):
    """GPT calls find_patient_appointment → gets result → returns text."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.find_appointment.return_value = _fake_appt()

    responses = [
        _make_tool_response("find_patient_appointment", {}),
        _make_text_response("מצאתי את התור שלך לעיסוי ב-25/06 בשעה 10:00. לבטל?"),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("לא אגיע היום", [], session, demo_clinic, calendar)

    assert "עיסוי" in reply or "10:00" in reply or "לבטל" in reply
    calendar.find_appointment.assert_awaited_once_with("+972541111111", "+972541111111")


async def test_converse_cancel_appointment(demo_clinic):
    """GPT calls cancel_appointment → calendar.cancel_appointment invoked."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.cancel_appointment.return_value = True

    responses = [
        _make_tool_response("cancel_appointment", {"appointment_id": "appt-001"}),
        _make_text_response("התור בוטל בהצלחה!"),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("כן, בטל", [], session, demo_clinic, calendar)

    calendar.cancel_appointment.assert_awaited_once_with("appt-001")
    assert "בוטל" in reply


async def test_converse_book_appointment(demo_clinic):
    """GPT calls book_appointment → calendar.create_appointment_from_session invoked."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.create_appointment_from_session.return_value = _fake_appt()

    responses = [
        _make_tool_response("book_appointment", {
            "patient_name": "שרה כהן",
            "service_id": "massage",
            "date": "מחר",
            "time": "10:00",
        }),
        _make_text_response("התור נקבע! מספר אסמכתא: TES-001"),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("כן, קבעי", [], session, demo_clinic, calendar)

    calendar.create_appointment_from_session.assert_awaited_once()
    # Verify the temp session passed to provider has correct data
    call_arg = calendar.create_appointment_from_session.call_args[0][0]
    assert call_arg.data["name"] == "שרה כהן"
    assert call_arg.data["service_id"] == "massage"
    assert call_arg.data["date_text"] == "מחר"
    assert call_arg.data["time_text"] == "10:00"


async def test_converse_update_appointment(demo_clinic):
    """GPT calls update_appointment → calendar.update_appointment_from_session invoked."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.update_appointment_from_session.return_value = _fake_appt(time_text="14:00")

    responses = [
        _make_tool_response("update_appointment", {
            "appointment_id": "appt-001",
            "patient_name": "שרה כהן",
            "service_id": "massage",
            "new_date": "מחר",
            "new_time": "14:00",
        }),
        _make_text_response("התור עודכן!"),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("שנה לי למחר ב-14:00", [], session, demo_clinic, calendar)

    calendar.update_appointment_from_session.assert_awaited_once()
    call_arg = calendar.update_appointment_from_session.call_args[0][0]
    assert call_arg.data["update_appt_id"] == "appt-001"
    assert call_arg.data["date_text"] == "מחר"
    assert call_arg.data["time_text"] == "14:00"


async def test_converse_transfer_to_human_sets_state(demo_clinic):
    """GPT calls transfer_to_human → session.state = HUMAN_HANDOFF, handoff message returned."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()

    responses = [
        _make_tool_response("transfer_to_human", {"reason": "בקשת לקוח"}),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("נציג", [], session, demo_clinic, calendar)

    assert session.state == ConversationState.HUMAN_HANDOFF
    assert reply == demo_clinic.handoff.message


async def test_converse_get_available_slots(demo_clinic):
    """GPT calls get_available_slots → calendar.get_available_slots_text invoked."""
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.get_available_slots_text.return_value = ["10:00", "11:00"]

    responses = [
        _make_tool_response("get_available_slots", {"date": "מחר", "service_id": "massage"}),
        _make_text_response("השעות הפנויות מחר: 10:00 ו-11:00"),
    ]

    with patch.object(provider._client.chat.completions, "create",
                      new=AsyncMock(side_effect=responses)):
        reply = await provider.converse("מתי יש מקום מחר?", [], session, demo_clinic, calendar)

    calendar.get_available_slots_text.assert_awaited_once_with("מחר", "massage")


# ── _execute_receptionist_tool unit tests ─────────────────────────────────────

async def test_execute_find_not_found(demo_clinic):
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.find_appointment.return_value = None

    result = await provider._execute_receptionist_tool(
        "find_patient_appointment", {}, session, demo_clinic, calendar
    )
    assert result["found"] is False


async def test_execute_find_resolves_service_id(demo_clinic):
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.find_appointment.return_value = _fake_appt(service_name="עיסוי")

    result = await provider._execute_receptionist_tool(
        "find_patient_appointment", {}, session, demo_clinic, calendar
    )
    assert result["found"] is True
    assert result["service_id"] == "massage"  # resolved from service_name "עיסוי"


async def test_execute_get_slots_empty(demo_clinic):
    provider = OpenAIProvider(api_key="test")
    session = _fake_session()
    calendar = AsyncMock()
    calendar.get_available_slots_text.return_value = []

    result = await provider._execute_receptionist_tool(
        "get_available_slots", {"date": "שבת"}, session, demo_clinic, calendar
    )
    assert result["slots"] == []
    assert "message" in result
