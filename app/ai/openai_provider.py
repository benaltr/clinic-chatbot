from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from app.ai.base import AIProvider, ExtractedFields, Intent
from app.ai.prompt_builder import (
    build_extract_system_prompt,
    build_faq_system_prompt,
    build_intent_system_prompt,
    build_receptionist_system_prompt,
)
from app.ai.tool_definitions import EXTRACT_FIELDS_TOOLS, INTENT_TOOLS, RECEPTIONIST_TOOLS
from app.tenants.models import ClinicConfig, FAQItem

if TYPE_CHECKING:
    from app.calendar.base import CalendarProvider
    from app.conversation.session import ConversationSession

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def classify_intent(self, message: str, clinic: ClinicConfig) -> Intent:
        try:
            response = await self._client.chat.completions.create(
                model=clinic.ai.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": build_intent_system_prompt(clinic)},
                    {"role": "user", "content": message},
                ],
                tools=INTENT_TOOLS,
                tool_choice={"type": "function", "function": {"name": "classify_intent"}},
            )
            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            return Intent(
                action=args.get("action", "unknown"),
                faq_query=args.get("faq_query", message),
                raw_text=message,
            )
        except Exception:
            logger.exception("Intent classification failed, defaulting to unknown")
            return Intent(action="unknown", raw_text=message)

    async def answer_faq(self, question: str, faqs: list[FAQItem], clinic_context: str) -> str:
        faq_context = "\n".join(
            f"שאלה: {faq.question_he}\nתשובה: {faq.answer_he}" for faq in faqs
        )
        user_message = f"שאלת המשתמש: {question}\n\nמידע זמין:\n{faq_context}"
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": clinic_context},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content or "מצטערים, לא הצלחנו למצוא תשובה. אנא פנה אלינו ישירות."
        except Exception:
            logger.exception("FAQ answer failed")
            return "מצטערים, נתקלנו בבעיה טכנית. אנא נסה שוב מאוחר יותר."

    async def extract_fields(self, message: str, current_data: dict) -> ExtractedFields:
        service_ids = list(current_data.get("available_services", []))
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                temperature=0,
                messages=[
                    {"role": "system", "content": build_extract_system_prompt(service_ids)},
                    {"role": "user", "content": message},
                ],
                tools=EXTRACT_FIELDS_TOOLS,
                tool_choice={"type": "function", "function": {"name": "extract_appointment_fields"}},
            )
            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            return ExtractedFields(
                name=args.get("name"),
                service=args.get("service"),
                date_text=args.get("date_text"),
                time_text=args.get("time_text"),
                confirmed=args.get("confirmed"),
            )
        except Exception:
            logger.exception("Field extraction failed")
            return ExtractedFields()

    async def converse(
        self,
        message: str,
        history: list[dict],
        session: ConversationSession,
        clinic: ClinicConfig,
        calendar: CalendarProvider,
    ) -> str:
        from app.conversation.states import ConversationState

        messages: list[dict] = [{"role": "system", "content": build_receptionist_system_prompt(clinic)}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        for _ in range(6):
            response = await self._client.chat.completions.create(
                model=clinic.ai.model,
                temperature=0.4,
                messages=messages,
                tools=RECEPTIONIST_TOOLS,
            )
            choice = response.choices[0]

            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                return choice.message.content or "מצטערים, לא הצלחתי להבין. נסה שוב."

            # Append assistant message with tool_calls before executing
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if name == "transfer_to_human":
                    session.state = ConversationState.HUMAN_HANDOFF
                    return clinic.handoff.message

                try:
                    result = await self._execute_receptionist_tool(name, args, session, clinic, calendar)
                except Exception:
                    logger.exception("Tool execution failed: %s", name)
                    result = {"error": "שגיאה בביצוע הפעולה"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return "מצטערים, לא הצלחתי לעזור. אנא פנה אלינו ישירות."

    async def _execute_receptionist_tool(
        self,
        name: str,
        args: dict,
        session: ConversationSession,
        clinic: ClinicConfig,
        calendar: CalendarProvider,
    ) -> dict:
        from app.conversation.session import ConversationSession as CS

        if name == "get_available_slots":
            date = args.get("date", "")
            service_id = args.get("service_id", "")
            slots = await calendar.get_available_slots_text(date, service_id)
            return {"slots": slots} if slots else {"slots": [], "message": "אין שעות פנויות בתאריך זה"}

        if name == "find_patient_appointment":
            appt = await calendar.find_appointment(session.phone_number, session.phone_number)
            if not appt:
                return {"found": False, "message": "לא נמצא תור פעיל"}
            service_id = next(
                (s.id for s in clinic.services if s.name_he == appt.service_name),
                clinic.services[0].id if clinic.services else "",
            )
            return {
                "found": True,
                "id": appt.id,
                "service_name": appt.service_name,
                "service_id": service_id,
                "date": appt.date_text,
                "time": appt.time_text,
                "patient_name": appt.patient_name,
            }

        if name == "book_appointment":
            temp = CS(
                conversation_id=session.conversation_id,
                clinic_id=session.clinic_id,
                phone_number=session.phone_number,
                data={
                    "name": args.get("patient_name", ""),
                    "service_id": args.get("service_id", ""),
                    "service_name": next(
                        (s.name_he for s in clinic.services if s.id == args.get("service_id")), ""
                    ),
                    "date_text": args.get("date", ""),
                    "time_text": args.get("time", ""),
                },
            )
            appt = await calendar.create_appointment_from_session(temp)
            return {"success": True, "ref_code": appt.ref_code, "date": appt.date_text, "time": appt.time_text}

        if name == "cancel_appointment":
            success = await calendar.cancel_appointment(args["appointment_id"])
            return {"success": success}

        if name == "update_appointment":
            service_id = args.get("service_id", "")
            if not service_id:
                # Try to resolve from service_name in args or keep empty (provider uses default duration)
                service_id = ""
            temp = CS(
                conversation_id=session.conversation_id,
                clinic_id=session.clinic_id,
                phone_number=session.phone_number,
                data={
                    "update_appt_id": args["appointment_id"],
                    "name": args.get("patient_name", ""),
                    "service_id": service_id,
                    "service_name": next(
                        (s.name_he for s in clinic.services if s.id == service_id), ""
                    ),
                    "date_text": args["new_date"],
                    "time_text": args["new_time"],
                },
            )
            appt = await calendar.update_appointment_from_session(temp)
            return {"success": True, "ref_code": appt.ref_code, "date": appt.date_text, "time": appt.time_text}

        return {"error": f"unknown tool: {name}"}
