import os

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
        creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "")
        if not creds_json or not calendar_id:
            raise ValueError(
                "Google Calendar provider requires GOOGLE_CALENDAR_CREDENTIALS and GOOGLE_CALENDAR_ID env vars"
            )
        return GoogleCalendarProvider(creds_json, calendar_id, clinic)
    if provider == "calendly":
        from app.calendar.calendly_provider import CalendlyProvider
        return CalendlyProvider()
    raise ValueError(f"Unknown calendar provider: {provider}")
