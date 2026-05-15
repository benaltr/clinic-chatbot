from __future__ import annotations

import random
import string
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Appointment, Clinic, Patient, Service


async def get_or_create_patient(
    db: AsyncSession, clinic_id: str, phone_number: str, name: str | None = None
) -> Patient:
    result = await db.execute(
        select(Patient).where(
            Patient.clinic_id == clinic_id,
            Patient.phone_number == phone_number,
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        patient = Patient(clinic_id=clinic_id, phone_number=phone_number, full_name=name)
        db.add(patient)
        await db.flush()
    elif name and not patient.full_name:
        patient.full_name = name
        await db.flush()
    return patient


async def get_service_by_key(db: AsyncSession, clinic_id: str, service_key: str) -> Service | None:
    result = await db.execute(
        select(Service).where(
            Service.clinic_id == clinic_id,
            Service.service_key == service_key,
            Service.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def create_appointment(
    db: AsyncSession,
    clinic_id: str,
    patient_id: str,
    service_id: str,
    start_time: datetime,
    end_time: datetime,
) -> Appointment:
    ref_code = _generate_ref_code(clinic_id)
    appt = Appointment(
        clinic_id=clinic_id,
        patient_id=patient_id,
        service_id=service_id,
        start_time=start_time,
        end_time=end_time,
        ref_code=ref_code,
        status="confirmed",
    )
    db.add(appt)
    await db.flush()
    return appt


async def find_appointment_by_ref(db: AsyncSession, ref_code: str) -> Appointment | None:
    result = await db.execute(
        select(Appointment).where(
            Appointment.ref_code == ref_code.upper(),
            Appointment.status == "confirmed",
        )
    )
    return result.scalar_one_or_none()


async def find_appointments_by_phone(
    db: AsyncSession, clinic_id: str, phone_number: str
) -> list[Appointment]:
    result = await db.execute(
        select(Appointment)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(
            Appointment.clinic_id == clinic_id,
            Patient.phone_number == phone_number,
            Appointment.status == "confirmed",
        )
        .order_by(Appointment.start_time)
    )
    return list(result.scalars().all())


async def cancel_appointment_by_id(db: AsyncSession, appointment_id: str) -> bool:
    result = await db.execute(
        update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(status="cancelled", updated_at=datetime.utcnow())
    )
    return result.rowcount > 0


def _generate_ref_code(clinic_id: str) -> str:
    prefix = clinic_id[:3].upper()
    suffix = "".join(random.choices(string.digits, k=6))
    return f"{prefix}-{suffix}"
