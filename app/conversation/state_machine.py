from __future__ import annotations

import logging

from app.ai.base import AIProvider, Intent
from app.calendar.base import CalendarProvider
from app.conversation import handlers
from app.conversation.session import ConversationSession
from app.conversation.states import ConversationState
from app.tenants.models import ClinicConfig

logger = logging.getLogger(__name__)

# Fast keyword shortcuts — checked before calling GPT
_BOOK_KEYWORDS = {"תור", "קביעה", "לקבוע", "להזמין", "הזמנה", "1"}
_CANCEL_KEYWORDS = {"ביטול", "לבטל", "לבטל תור", "2"}
_UPDATE_KEYWORDS = {"שינוי", "עדכון", "לשנות", "לעדכן", "3"}
_HUMAN_KEYWORDS = {"נציג", "אנוש", "עזרה", "5"}


def _quick_intent(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized in _BOOK_KEYWORDS:
        return "book"
    if normalized in _CANCEL_KEYWORDS:
        return "cancel"
    if normalized in _UPDATE_KEYWORDS:
        return "update"
    if normalized in _HUMAN_KEYWORDS:
        return "human"
    return None


class ConversationStateMachine:
    def __init__(self, ai: AIProvider, calendar: CalendarProvider, clinic: ClinicConfig) -> None:
        self._ai = ai
        self._calendar = calendar
        self._clinic = clinic

    async def process(self, session: ConversationSession, message: str) -> str:
        state = session.state

        # ── IDLE / GREETING ──────────────────────────────────────────────────
        if state in (ConversationState.IDLE, ConversationState.GREETING):
            quick = _quick_intent(message)
            if quick:
                action = quick
            else:
                intent: Intent = await self._ai.classify_intent(message, self._clinic)
                action = intent.action

            if action == "book":
                session.state = ConversationState.BOOKING_NAME
                return handlers.ask_name()

            if action == "cancel":
                session.state = ConversationState.CANCEL_LOOKUP
                return handlers.ask_cancel_ref()

            if action == "update":
                session.state = ConversationState.UPDATE_LOOKUP
                return handlers.ask_cancel_ref()

            if action == "human":
                session.state = ConversationState.HUMAN_HANDOFF
                return handlers.human_handoff(self._clinic.handoff.message)

            if action == "faq":
                intent_obj = await self._ai.classify_intent(message, self._clinic)
                answer = await self._ai.answer_faq(
                    intent_obj.faq_query or message,
                    self._clinic.faqs,
                    self._clinic.ai.personality,
                )
                return answer

            return handlers.greeting(self._clinic)

        # ── BOOKING FLOW ──────────────────────────────────────────────────────
        if state == ConversationState.BOOKING_NAME:
            fields = await self._ai.extract_fields(message, {})
            name = fields.name or message.strip()
            session.data["name"] = name
            session.state = ConversationState.BOOKING_SERVICE
            return handlers.ask_service(self._clinic)

        if state == ConversationState.BOOKING_SERVICE:
            service = self._resolve_service(message)
            if not service:
                return handlers.ask_service(self._clinic)
            session.data["service_id"] = service.id
            session.data["service_name"] = service.name_he
            session.state = ConversationState.BOOKING_DATE
            return handlers.ask_date(session.data["name"])

        if state == ConversationState.BOOKING_DATE:
            fields = await self._ai.extract_fields(message, {})
            date_text = fields.date_text or message.strip()
            session.data["date_text"] = date_text
            slots = await self._calendar.get_available_slots_text(date_text, session.data["service_id"])
            session.data["available_slots"] = slots
            session.state = ConversationState.BOOKING_TIME
            return handlers.ask_time(date_text, slots)

        if state == ConversationState.BOOKING_TIME:
            slot = self._pick_slot(message, session.data.get("available_slots", []))
            if not slot:
                return handlers.ask_time(
                    session.data["date_text"], session.data.get("available_slots", [])
                )
            session.data["time_text"] = slot
            session.state = ConversationState.BOOKING_CONFIRM
            return handlers.booking_confirm(
                session.data["name"],
                session.data["service_name"],
                session.data["date_text"],
                slot,
            )

        if state == ConversationState.BOOKING_CONFIRM:
            fields = await self._ai.extract_fields(message, {})
            confirmed = fields.confirmed
            if confirmed is None:
                confirmed = message.strip() in {"כן", "אישור", "בסדר", "yes", "ok", "1"}
            if confirmed:
                appt = await self._calendar.create_appointment_from_session(session)
                session.state = ConversationState.IDLE
                session.data = {}
                return handlers.booking_done(appt.ref_code, appt.date_text, appt.time_text)
            session.state = ConversationState.IDLE
            session.data = {}
            return "בסדר, ביטלנו את ההזמנה. שלח *תור* בכל עת לקביעה חדשה."

        # ── CANCEL FLOW ───────────────────────────────────────────────────────
        if state == ConversationState.CANCEL_LOOKUP:
            appt = await self._calendar.find_appointment(message.strip(), session.phone_number)
            if not appt:
                return handlers.appointment_not_found()
            session.data["cancel_appt_id"] = appt.id
            session.data["cancel_service_name"] = appt.service_name
            session.data["cancel_date_text"] = appt.date_text
            session.data["cancel_time_text"] = appt.time_text
            session.state = ConversationState.CANCEL_CONFIRM
            return handlers.cancel_confirm(appt.service_name, appt.date_text, appt.time_text)

        if state == ConversationState.CANCEL_CONFIRM:
            fields = await self._ai.extract_fields(message, {})
            confirmed = fields.confirmed
            if confirmed is None:
                confirmed = message.strip() in {"כן", "אישור", "בסדר", "yes", "1"}
            if confirmed:
                await self._calendar.cancel_appointment(session.data["cancel_appt_id"])
                session.state = ConversationState.IDLE
                session.data = {}
                return handlers.cancel_done()
            session.state = ConversationState.IDLE
            session.data = {}
            return "בסדר, התור לא בוטל. שלח *עזרה* אם צריך משהו."

        # ── UPDATE FLOW ───────────────────────────────────────────────────────
        if state == ConversationState.UPDATE_LOOKUP:
            appt = await self._calendar.find_appointment(message.strip(), session.phone_number)
            if not appt:
                return handlers.appointment_not_found()
            session.data["update_appt_id"] = appt.id
            session.data["name"] = appt.patient_name
            session.state = ConversationState.UPDATE_FIELD
            return handlers.ask_update_what()

        if state == ConversationState.UPDATE_FIELD:
            session.state = ConversationState.BOOKING_DATE
            return handlers.ask_date(session.data.get("name", ""))

        if state == ConversationState.UPDATE_CONFIRM:
            fields = await self._ai.extract_fields(message, {})
            confirmed = fields.confirmed
            if confirmed is None:
                confirmed = message.strip() in {"כן", "אישור", "1"}
            if confirmed:
                appt = await self._calendar.update_appointment_from_session(session)
                session.state = ConversationState.IDLE
                session.data = {}
                return handlers.update_done(appt.ref_code)
            session.state = ConversationState.IDLE
            session.data = {}
            return "בסדר, העדכון בוטל. התור הישן נשמר."

        # ── FAQ ───────────────────────────────────────────────────────────────
        if state == ConversationState.FAQ:
            answer = await self._ai.answer_faq(message, self._clinic.faqs, self._clinic.ai.personality)
            session.state = ConversationState.IDLE
            return answer

        # ── FALLBACK ──────────────────────────────────────────────────────────
        session.state = ConversationState.IDLE
        session.data = {}
        return handlers.greeting(self._clinic)

    def _resolve_service(self, text: str):
        text_lower = text.strip().lower()
        # Try numeric selection first
        if text_lower.isdigit():
            idx = int(text_lower) - 1
            if 0 <= idx < len(self._clinic.services):
                return self._clinic.services[idx]
        # Try name match
        for service in self._clinic.services:
            if service.id in text_lower or service.name_he in text:
                return service
        # Fuzzy: check if any service keyword is substring
        for service in self._clinic.services:
            if any(word in text for word in service.name_he.split()):
                return service
        return None

    def _pick_slot(self, text: str, slots: list[str]) -> str | None:
        text_stripped = text.strip()
        if text_stripped.isdigit():
            idx = int(text_stripped) - 1
            if 0 <= idx < len(slots):
                return slots[idx]
        # Direct match
        for slot in slots:
            if text_stripped in slot:
                return slot
        return None
