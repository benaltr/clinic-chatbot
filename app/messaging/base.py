from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from fastapi import Request


@dataclass
class IncomingMessage:
    from_number: str
    to_number: str
    body: str
    message_id: str
    provider: str
    raw_payload: dict = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    to_number: str
    body: str


class MessagingProvider(ABC):
    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> None: ...

    @abstractmethod
    def verify_webhook(self, token: str, challenge: str) -> str:
        """Handle the GET webhook verification handshake. Returns the challenge string."""
        ...

    @abstractmethod
    async def validate_signature(self, request: Request) -> bool:
        """Validate the X-Hub-Signature-256 header on incoming POST payloads."""
        ...

    @abstractmethod
    def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        """Parse raw webhook JSON → IncomingMessage. Returns None for non-message events."""
        ...
