from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.calendar.base import AppointmentResult, CalendarProvider
from app.conversation.session import ConversationSession
from app.tenants.models import ClinicConfig

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarProvider(CalendarProvider):
    def __init__(self, credentials_json: str, calendar_id: str, clinic: ClinicConfig) -> None:
        self._clinic = clinic
        self._calendar_id = calendar_id
        self._service = None

        try:
            creds_dict = json.loads(credentials_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            self._service = build("calendar", "v3", credentials=creds)
        except Exception as exc:
            logger.error("Failed to initialize Google Calendar: %s", exc)
            raise

    async def get_available_slots_text(self, date_text: str, service_id: str) -> list[str]:
        """Return available time slots for the requested date by checking calendar events."""
        try:
            target_date = self._parse_date(date_text)
            if target_date is None:
                return []

            service = next((s for s in self._clinic.services if s.id == service_id), None)
            duration = service.duration_minutes if service else self._clinic.calendar.slot_duration_minutes

            # Get day working hours
            day_name = self._weekday_to_he(target_date.weekday())
            hours_config = self._clinic.working_hours.get(day_name)
            if not hours_config or hours_config == "closed":
                return []

            # Build timezone-aware datetimes (required by Google Calendar API)
            tz = ZoneInfo(self._clinic.timezone)
            start_of_day = datetime.combine(target_date, hours_config.open, tzinfo=tz)
            end_of_day = datetime.combine(target_date, hours_config.close, tzinfo=tz)

            events_result = self._service.events().list(
                calendarId=self._calendar_id,
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            booked_times = set()
            for event in events_result.get("items", []):
                event_start_str = event["start"].get("dateTime")
                if event_start_str:
                    event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                    booked_times.add(event_start.astimezone(tz).strftime("%H:%M"))

            # Generate available slots
            slots = []
            current = start_of_day
            while current + timedelta(minutes=duration) <= end_of_day:
                slot_time = current.strftime("%H:%M")
                if slot_time not in booked_times:
                    slots.append(slot_time)
                current += timedelta(minutes=duration)

            return slots[:8]
        except HttpError as e:
            logger.error("Google Calendar API error: %s", e)
            return []

    async def create_appointment_from_session(self, session: ConversationSession) -> AppointmentResult:
        """Create an event in Google Calendar."""
        data = session.data
        start_time = self._parse_datetime(data.get("date_text", ""), data.get("time_text", ""))
        service = next((s for s in self._clinic.services if s.id == data["service_id"]), None)
        duration = service.duration_minutes if service else 60
        end_time = start_time + timedelta(minutes=duration)

        event = {
            "summary": f"{data.get('service_name', 'Appointment')} - {data.get('name', 'Guest')}",
            "description": f"Patient: {data.get('name', 'N/A')}\nService: {data.get('service_name', 'N/A')}\nPhone: {session.phone_number}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": self._clinic.timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": self._clinic.timezone},
        }

        try:
            event_result = self._service.events().insert(calendarId=self._calendar_id, body=event).execute()
            event_id = event_result["id"]

            # Generate a reference code for tracking
            ref_code = f"{self._clinic.clinic_id[:3].upper()}-{event_id[:8].upper()}"

            return AppointmentResult(
                id=event_id,
                ref_code=ref_code,
                patient_name=data.get("name", ""),
                service_name=data.get("service_name", ""),
                date_text=data.get("date_text", ""),
                time_text=data.get("time_text", ""),
            )
        except HttpError as e:
            logger.error("Failed to create Google Calendar event: %s", e)
            raise

    async def find_appointment(self, ref_or_phone: str, phone_number: str) -> AppointmentResult | None:
        """Find appointment by reference code or phone number."""
        try:
            # Search by description (contains phone number)
            events_result = self._service.events().list(
                calendarId=self._calendar_id,
                q=phone_number,
                maxResults=10,
            ).execute()

            for event in events_result.get("items", []):
                if "description" in event and phone_number in event["description"]:
                    return self._event_to_result(event)

            return None
        except HttpError:
            logger.exception("Failed to find appointment")
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Delete an event from Google Calendar."""
        try:
            self._service.events().delete(calendarId=self._calendar_id, eventId=appointment_id).execute()
            return True
        except HttpError as e:
            logger.error("Failed to delete event: %s", e)
            return False

    async def update_appointment_from_session(self, session: ConversationSession) -> AppointmentResult:
        """Cancel the old appointment and create a new one."""
        old_id = session.data.get("update_appt_id")
        if old_id:
            await self.cancel_appointment(old_id)
        return await self.create_appointment_from_session(session)

    def _event_to_result(self, event: dict) -> AppointmentResult:
        start = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
        return AppointmentResult(
            id=event["id"],
            ref_code=f"{self._clinic.clinic_id[:3].upper()}-{event['id'][:8].upper()}",
            patient_name=event.get("summary", "").split(" - ")[-1],
            service_name=event.get("summary", "").split(" - ")[0],
            date_text=start.strftime("%d/%m/%Y"),
            time_text=start.strftime("%H:%M"),
        )

    def _parse_date(self, date_text: str):
        from datetime import date

        today = datetime.today()

        if date_text in ("מחר", "tomorrow"):
            return (today + timedelta(days=1)).date()
        if date_text in ("היום", "today"):
            return today.date()

        # dd/mm format
        import re

        match = re.search(r"(\d{1,2})[/\-\.](\d{1,2})", date_text)
        if match:
            day, month = int(match.group(1)), int(match.group(2))
            year = today.year
            try:
                d = date(year, month, day)
                if d < today.date():
                    d = date(year + 1, month, day)
                return d
            except ValueError:
                pass

        # Hebrew day names
        he_days = {
            "ראשון": 6,
            "שני": 0,
            "שלישי": 1,
            "רביעי": 2,
            "חמישי": 3,
            "שישי": 4,
            "שבת": 5,
        }
        for he_day, weekday in he_days.items():
            if he_day in date_text:
                days_ahead = (weekday - today.weekday()) % 7 or 7
                return (today + timedelta(days=days_ahead)).date()

        return None

    def _parse_datetime(self, date_text: str, time_text: str) -> datetime:
        import re

        d = self._parse_date(date_text)
        if d is None:
            d = (datetime.today() + timedelta(days=1)).date()

        match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            hour, minute = 10, 0

        tz = ZoneInfo(self._clinic.timezone)
        return datetime.combine(d, datetime.min.time().replace(hour=hour, minute=minute), tzinfo=tz)

    def _weekday_to_he(self, weekday: int) -> str:
        mapping = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
        return mapping.get(weekday, "sunday")
