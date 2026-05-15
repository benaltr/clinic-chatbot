import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jerusalem")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patients: Mapped[list["Patient"]] = relationship(back_populates="clinic")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="clinic")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="clinic")
    working_hours: Mapped[list["WorkingHours"]] = relationship(back_populates="clinic")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    clinic_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("clinics.id"), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="he")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    clinic: Mapped["Clinic"] = relationship(back_populates="patients")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="patient")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    clinic_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("clinics.id"), nullable=False)
    service_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name_he: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="service")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    clinic_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    service_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("services.id"), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="confirmed")
    ref_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    clinic: Mapped["Clinic"] = relationship(back_populates="appointments")
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    clinic_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"))
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="idle")
    state_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    clinic: Mapped["Clinic"] = relationship(back_populates="conversations")
    patient: Mapped["Patient"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    clinic_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("clinics.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    clinic: Mapped["Clinic"] = relationship(back_populates="working_hours")
