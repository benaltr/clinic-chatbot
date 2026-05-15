import os
import re
from datetime import time
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env(value: str) -> str:
    """Replace ${VAR_NAME} references with actual environment variable values."""
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        resolved = os.environ.get(var_name, "")
        if not resolved:
            raise ValueError(f"Environment variable '{var_name}' referenced in clinic config is not set")
        return resolved

    return _ENV_PATTERN.sub(replacer, value)


class WhatsAppConfig(BaseModel):
    number: str
    provider: Literal["meta", "twilio"] = "meta"
    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_verify_token: str = ""

    @model_validator(mode="after")
    def resolve_env_vars(self) -> "WhatsAppConfig":
        if self.meta_access_token:
            self.meta_access_token = _resolve_env(self.meta_access_token)
        if self.meta_phone_number_id:
            self.meta_phone_number_id = _resolve_env(self.meta_phone_number_id)
        if self.meta_verify_token:
            self.meta_verify_token = _resolve_env(self.meta_verify_token)
        return self


class AIConfig(BaseModel):
    model: str = "gpt-4o"
    personality: str = "אתה נציג שירות לקוחות מקצועי. ענה תמיד בעברית."
    temperature: float = 0.3
    max_history_messages: int = 10


class CalendarConfig(BaseModel):
    provider: Literal["local_db", "google_calendar", "calendly"] = "local_db"
    slot_duration_minutes: int = 60
    booking_window_days: int = 30
    min_notice_hours: int = 2
    google_calendar_credentials: str = ""
    calendly_token: str = ""


class ServiceConfig(BaseModel):
    id: str
    name_he: str
    name_en: str = ""
    duration_minutes: int = 60


class WorkingDayConfig(BaseModel):
    open: time | None = None
    close: time | None = None

    @field_validator("open", "close", mode="before")
    @classmethod
    def parse_time_string(cls, v: object) -> object:
        if isinstance(v, str):
            h, m = v.split(":")
            return time(int(h), int(m))
        return v


class NotificationsConfig(BaseModel):
    remind_hours_before: int = 24
    send_confirmation: bool = True


class HandoffConfig(BaseModel):
    enabled: bool = True
    trigger_keywords: list[str] = ["אנוש", "נציג", "עזרה דחופה"]
    notify_phone: str = ""
    message: str = "הועברת לנציג שירות. ניצור איתך קשר בהקדם."


class FAQItem(BaseModel):
    id: str
    keywords: list[str] = []
    question_he: str
    answer_he: str


class ClinicConfig(BaseModel):
    clinic_id: str
    name: str
    name_en: str = ""
    timezone: str = "Asia/Jerusalem"
    language: str = "he"
    whatsapp: WhatsAppConfig
    ai: AIConfig = AIConfig()
    calendar: CalendarConfig = CalendarConfig()
    services: list[ServiceConfig] = []
    working_hours: dict[str, WorkingDayConfig | Literal["closed"]] = {}
    notifications: NotificationsConfig = NotificationsConfig()
    handoff: HandoffConfig = HandoffConfig()
    faqs: list[FAQItem] = []
