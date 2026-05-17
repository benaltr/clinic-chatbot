import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.ai.base import ExtractedFields
from app.calendar.base import AppointmentResult
from app.conversation.session import ConversationSession
from app.conversation.state_machine import ConversationStateMachine
from app.conversation.states import ConversationState
from app.tenants.models import (
    AIConfig,
    CalendarConfig,
    ClinicConfig,
    FAQItem,
    HandoffConfig,
    NotificationsConfig,
    ServiceConfig,
    WhatsAppConfig,
    WorkingDayConfig,
)


@pytest.fixture
def demo_clinic() -> ClinicConfig:
    return ClinicConfig(
        clinic_id="test_wellness",
        name="קליניקת טסט",
        timezone="Asia/Jerusalem",
        language="he",
        whatsapp=WhatsAppConfig(
            number="+972501111111",
            provider="meta",
            meta_access_token="test_token",
            meta_phone_number_id="111222333",
            meta_verify_token="test_verify",
        ),
        ai=AIConfig(personality="אתה בוט טסט.", temperature=0.0),
        calendar=CalendarConfig(provider="local_db"),
        services=[
            ServiceConfig(id="massage", name_he="עיסוי", duration_minutes=60),
            ServiceConfig(id="reflexology", name_he="רפלקסולוגיה", duration_minutes=45),
        ],
        working_hours={
            "sunday": WorkingDayConfig(open="09:00", close="18:00"),
            "monday": WorkingDayConfig(open="09:00", close="18:00"),
            "tuesday": WorkingDayConfig(open="09:00", close="18:00"),
            "wednesday": WorkingDayConfig(open="09:00", close="18:00"),
            "thursday": WorkingDayConfig(open="09:00", close="18:00"),
            "friday": WorkingDayConfig(open="09:00", close="14:00"),
            "saturday": "closed",
        },
        faqs=[
            FAQItem(
                id="parking",
                keywords=["חניה"],
                question_he="האם יש חניה?",
                answer_he="יש חניה חינמית.",
            )
        ],
        notifications=NotificationsConfig(),
        handoff=HandoffConfig(trigger_keywords=["נציג"], message="הועברת לנציג."),
    )


@pytest.fixture
def meta_payload():
    fixture_path = Path(__file__).parent / "fixtures" / "meta_incoming.json"
    with fixture_path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_ai():
    from app.ai.base import Intent
    ai = AsyncMock()
    ai.classify_intent.return_value = Intent(action="unknown")
    ai.answer_faq.return_value = "תשובה לטסט"
    ai.extract_fields.return_value = ExtractedFields()
    return ai


@pytest.fixture
def mock_calendar():
    calendar = AsyncMock()
    calendar.get_available_slots_text.return_value = ["10:00", "11:00", "12:00"]
    return calendar


@pytest.fixture
def make_session():
    def _factory(state=ConversationState.IDLE, data=None, phone="+972541111111"):
        return ConversationSession(
            conversation_id="test-conv-id",
            clinic_id="test_wellness",
            phone_number=phone,
            state=state,
            data=data or {},
        )
    return _factory


@pytest.fixture
def make_machine(mock_ai, mock_calendar, demo_clinic):
    return ConversationStateMachine(ai=mock_ai, calendar=mock_calendar, clinic=demo_clinic)


@pytest.fixture
def fake_appt():
    return AppointmentResult(
        id="appt-uuid-001",
        ref_code="TES-001",
        patient_name="שרה כהן",
        service_name="עיסוי",
        date_text="23/06/2025",
        time_text="10:00",
    )


@pytest.fixture
def make_fields():
    def _factory(**kwargs):
        return ExtractedFields(**kwargs)
    return _factory
