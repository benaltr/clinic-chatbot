from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class AppointmentResult:
    id: str
    ref_code: str
    patient_name: str
    service_name: str
    date_text: str
    time_text: str
    status: str = "confirmed"


class CalendarProvider(ABC):
    @abstractmethod
    async def get_available_slots_text(self, date_text: str, service_id: str) -> list[str]:
        """Return list of available time slot strings for display (e.g. ['10:00', '11:00'])."""
        ...

    @abstractmethod
    async def create_appointment_from_session(self, session) -> AppointmentResult:
        """Create a new appointment from collected session data."""
        ...

    @abstractmethod
    async def find_appointment(self, ref_or_phone: str, phone_number: str) -> AppointmentResult | None:
        """Find an appointment by ref code or phone number."""
        ...

    @abstractmethod
    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel an appointment by ID."""
        ...

    @abstractmethod
    async def update_appointment_from_session(self, session) -> AppointmentResult:
        """Update an existing appointment using session data."""
        ...
