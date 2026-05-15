import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    ai.extract_fields.return_value = MagicMock(
        name=None, service=None, date_text=None, time_text=None, confirmed=None
    )
    return ai


@pytest.fixture
def mock_calendar():
    calendar = AsyncMock()
    calendar.get_available_slots_text.return_value = ["10:00", "11:00", "12:00"]
    return calendar
