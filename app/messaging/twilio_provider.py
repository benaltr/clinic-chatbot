from fastapi import Request

from app.messaging.base import IncomingMessage, MessagingProvider, OutgoingMessage


class TwilioProvider(MessagingProvider):
    """Twilio stub — not the primary provider. Implement when needed."""

    def verify_webhook(self, token: str, challenge: str) -> str:
        raise NotImplementedError("Twilio does not use a verification challenge")

    async def validate_signature(self, request: Request) -> bool:
        raise NotImplementedError

    def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        raise NotImplementedError

    async def send_message(self, message: OutgoingMessage) -> None:
        raise NotImplementedError
