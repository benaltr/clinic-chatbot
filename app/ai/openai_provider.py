import json
import logging

from openai import AsyncOpenAI

from app.ai.base import AIProvider, ExtractedFields, Intent
from app.ai.prompt_builder import build_extract_system_prompt, build_faq_system_prompt, build_intent_system_prompt
from app.ai.tool_definitions import EXTRACT_FIELDS_TOOLS, INTENT_TOOLS
from app.tenants.models import ClinicConfig, FAQItem

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
