from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.base import AppointmentResult, CalendarProvider
from app.conversation.session import ConversationSession
from app.db import crud
from app.tenants.models import ClinicConfig

logger = logging.getLogger(__name__)

# Map Hebrew day names to weekday numbers (0=Monday Python convention, but we display)
_HE_DAYS = {
    "ראשון": 6,  # Sunday
    "שני": 0,   # Monday
    "שלישי": 1,
    "רביעי": 2,
    "חמישי": 3,
    "שישי": 4,
    "שבת": 5,
}


class LocalDBProvider(CalendarProvider):
    def __init__(self, db: AsyncSession, clinic: ClinicConfig) -> None:
        self._db = db
        self._clinic = clinic

    async def get_available_slots_text(self, date_text: str, service_id: str) -> list[str]:
        """Return simple list of available hour strings for the requested date."""
        target_date = self._parse_date(date_text)
        if target_date is None:
            return []

        day_name = self._weekday_to_he(target_date.weekday())
        hours_config = self._clinic.working_hours.get(day_name)
        if not hours_config or hours_config == "closed":
            return []

        # Get service duration
        service = next((s for s in self._clinic.services if s.id == service_id), None)
        duration = service.duration_minutes if service else self._clinic.calendar.slot_duration_minutes

        slots = []
        current = datetime.combine(target_date, hours_config.open)
        close = datetime.combine(target_date, hours_config.close)
        while current + timedelta(minutes=duration) <= close:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=duration)

        return slots[:8]  # Return max 8 slots to keep WhatsApp messages short

    async def create_appointment_from_session(self, session: ConversationSession) -> AppointmentResult:
        data = session.data
        patient = await crud.get_or_create_patient(
            self._db, session.clinic_id, session.phone_number, data.get("name")
        )
        db_service = await crud.get_service_by_key(self._db, session.clinic_id, data["service_id"])

        start_time = self._parse_datetime(data.get("date_text", ""), data.get("time_text", ""))
        service = next((s for s in self._clinic.services if s.id == data["service_id"]), None)
        duration = service.duration_minutes if service else 60
        end_time = start_time + timedelta(minutes=duration)

        appt = await crud.create_appointment(
            self._db,
            clinic_id=session.clinic_id,
            patient_id=patient.id,
            service_id=db_service.id if db_service else data["service_id"],
            start_time=start_time,
            end_time=end_time,
        )
        await self._db.commit()

        return AppointmentResult(
            id=appt.id,
            ref_code=appt.ref_code,
            patient_name=data.get("name", ""),
            service_name=data.get("service_name", ""),
            date_text=data.get("date_text", ""),
            time_text=data.get("time_text", ""),
        )

    async def find_appointment(self, ref_or_phone: str, phone_number: str) -> AppointmentResult | None:
        # Try ref code first
        appt = await crud.find_appointment_by_ref(self._db, ref_or_phone)
        if appt:
            return await self._appt_to_result(appt)

        # Fall back to phone lookup — return most recent upcoming appointment
        appointments = await crud.find_appointments_by_phone(
            self._db, self._clinic.clinic_id, phone_number
        )
        if appointments:
            return await self._appt_to_result(appointments[0])

        return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        cancelled = await crud.cancel_appointment_by_id(self._db, appointment_id)
        await self._db.commit()
        return cancelled

    async def update_appointment_from_session(self, session: ConversationSession) -> AppointmentResult:
        data = session.data
        appt_id = data.get("update_appt_id")
        if not appt_id:
            raise ValueError("No appointment ID in session for update")

        await crud.cancel_appointment_by_id(self._db, appt_id)
        return await self.create_appointment_from_session(session)

    async def _appt_to_result(self, appt) -> AppointmentResult:
        from sqlalchemy import select
        from app.db.models import Patient, Service

        patient_result = await self._db.execute(
            select(Patient).where(Patient.id == appt.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        service_result = await self._db.execute(
            select(Service).where(Service.id == appt.service_id)
        )
        service = service_result.scalar_one_or_none()

        return AppointmentResult(
            id=appt.id,
            ref_code=appt.ref_code,
            patient_name=patient.full_name if patient else "",
            service_name=service.name_he if service else "",
            date_text=appt.start_time.strftime("%d/%m/%Y"),
            time_text=appt.start_time.strftime("%H:%M"),
            status=appt.status,
        )

    def _parse_date(self, date_text: str):
        from datetime import date
        today = datetime.today()

        if date_text in ("מחר", "tomorrow"):
            return (today + timedelta(days=1)).date()
        if date_text in ("היום", "today"):
            return today.date()

        # dd/mm format
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

        # Hebrew day name
        for he_day, weekday in _HE_DAYS.items():
            if he_day in date_text:
                days_ahead = (weekday - today.weekday()) % 7 or 7
                return (today + timedelta(days=days_ahead)).date()

        return None

    def _parse_datetime(self, date_text: str, time_text: str) -> datetime:
        d = self._parse_date(date_text)
        if d is None:
            d = (datetime.today() + timedelta(days=1)).date()

        match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            hour, minute = 10, 0

        return datetime.combine(d, datetime.min.time().replace(hour=hour, minute=minute))

    def _weekday_to_he(self, weekday: int) -> str:
        mapping = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
        return mapping.get(weekday, "sunday")
