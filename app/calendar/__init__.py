from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.base import CalendarProvider
from app.tenants.models import ClinicConfig


def get_calendar_provider(clinic: ClinicConfig, db: AsyncSession) -> CalendarProvider:
    provider = clinic.calendar.provider
    if provider == "local_db":
        from app.calendar.local_db_provider import LocalDBProvider
        return LocalDBProvider(db, clinic)
    if provider == "google_calendar":
        from app.calendar.google_calendar_provider import GoogleCalendarProvider
        return GoogleCalendarProvider()
    if provider == "calendly":
        from app.calendar.calendly_provider import CalendlyProvider
        return CalendlyProvider()
    raise ValueError(f"Unknown calendar provider: {provider}")
