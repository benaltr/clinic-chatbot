from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from app.tenants.models import ClinicConfig, FAQItem


@dataclass
class Intent:
    action: Literal["book", "cancel", "update", "faq", "human", "unknown"]
    faq_query: str = ""
    raw_text: str = ""


@dataclass
class ExtractedFields:
    name: str | None = None
    service: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    confirmed: bool | None = None


class AIProvider(ABC):
    @abstractmethod
    async def classify_intent(self, message: str, clinic: ClinicConfig) -> Intent: ...

    @abstractmethod
    async def answer_faq(self, question: str, faqs: list[FAQItem], clinic_context: str) -> str: ...

    @abstractmethod
    async def extract_fields(self, message: str, current_data: dict) -> ExtractedFields: ...
