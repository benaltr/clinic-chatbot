import hashlib
import hmac
import logging

import httpx
from fastapi import Request

from app.messaging.base import IncomingMessage, MessagingProvider, OutgoingMessage

logger = logging.getLogger(__name__)


class MetaProvider(MessagingProvider):
    def __init__(self, access_token: str, phone_number_id: str, verify_token: str, api_version: str = "v21.0"):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.api_version = api_version
        self._base_url = f"https://graph.facebook.com/{api_version}"

    def verify_webhook(self, token: str, challenge: str) -> str:
        if token != self.verify_token:
            raise ValueError("Webhook verify token mismatch")
        return challenge

    async def validate_signature(self, request: Request) -> bool:
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header.startswith("sha256="):
            return False
        body = await request.body()
        app_secret = self.access_token  # In production, use a dedicated app_secret
        expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature_header)

    def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages")
            if not messages:
                return None
            msg = messages[0]
            if msg.get("type") != "text":
                return None
            metadata = value.get("metadata", {})
            return IncomingMessage(
                from_number=msg["from"],
                to_number=metadata.get("display_phone_number", ""),
                body=msg["text"]["body"].strip(),
                message_id=msg["id"],
                provider="meta",
                raw_payload=payload,
            )
        except (KeyError, IndexError, TypeError):
            logger.warning("Failed to parse Meta webhook payload", exc_info=True)
            return None

    async def send_message(self, message: OutgoingMessage) -> None:
        url = f"{self._base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": message.to_number,
            "type": "text",
            "text": {"body": message.body},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code != 200:
                logger.error("Meta API error %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
