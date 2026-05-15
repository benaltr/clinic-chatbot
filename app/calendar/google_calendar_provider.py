from app.calendar.base import AppointmentResult, CalendarProvider


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar integration — not yet implemented."""

    async def get_available_slots_text(self, date_text: str, service_id: str) -> list[str]:
        raise NotImplementedError("Google Calendar provider not yet implemented")

    async def create_appointment_from_session(self, session) -> AppointmentResult:
        raise NotImplementedError

    async def find_appointment(self, ref_or_phone: str, phone_number: str) -> AppointmentResult | None:
        raise NotImplementedError

    async def cancel_appointment(self, appointment_id: str) -> bool:
        raise NotImplementedError

    async def update_appointment_from_session(self, session) -> AppointmentResult:
        raise NotImplementedError
