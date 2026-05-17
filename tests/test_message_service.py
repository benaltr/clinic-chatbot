"""Integration tests for message_service.handle_incoming.

Strategy: patch get_or_create_session / save_session / append_message to skip
the DB entirely. Patch _ai_provider and get_calendar_provider for business logic.
Patch MetaProvider.send_message to capture outgoing messages.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.conversation.session import ConversationSession
from app.conversation.states import ConversationState
from app.messaging.base import IncomingMessage


def _make_incoming(body: str, from_number: str = "+972541111111") -> IncomingMessage:
    return IncomingMessage(
        from_number=from_number,
        to_number="+972501111111",
        body=body,
        message_id="msg-001",
        provider="meta",
    )


def _idle_session() -> ConversationSession:
    return ConversationSession(
        conversation_id="test-conv-id",
        clinic_id="test_wellness",
        phone_number="+972541111111",
        state=ConversationState.IDLE,
        data={},
    )


@pytest.fixture
def patched_service(mock_ai, mock_calendar):
    """Patch all external dependencies of message_service."""
    session = _idle_session()
    with (
        patch("app.services.message_service._ai_provider", mock_ai),
        patch("app.services.message_service.get_calendar_provider", return_value=mock_calendar),
        patch("app.services.message_service.get_or_create_session", new=AsyncMock(return_value=session)),
        patch("app.services.message_service.save_session", new=AsyncMock()),
        patch("app.services.message_service.append_message", new=AsyncMock()),
        patch("app.messaging.meta_provider.MetaProvider.send_message", new=AsyncMock()),
    ):
        yield session


async def test_handoff_keyword_bypasses_state_machine(patched_service, demo_clinic):
    from app.services import message_service

    sent_messages = []

    async def capture_send(self, msg):
        sent_messages.append(msg)

    with patch("app.messaging.meta_provider.MetaProvider.send_message", capture_send):
        with patch(
            "app.conversation.state_machine.ConversationStateMachine.process",
            new=AsyncMock(side_effect=AssertionError("should not be called")),
        ):
            db = AsyncMock()
            # Override session fixture to use handoff session
            with patch(
                "app.services.message_service.get_or_create_session",
                new=AsyncMock(return_value=_idle_session()),
            ):
                await message_service.handle_incoming(
                    _make_incoming("נציג"), demo_clinic, db
                )

    assert len(sent_messages) == 1
    assert sent_messages[0].body == "הועברת לנציג."


async def test_normal_message_sends_reply(patched_service, demo_clinic):
    from app.services import message_service

    sent_messages = []

    async def capture_send(self, msg):
        sent_messages.append(msg)

    with patch("app.messaging.meta_provider.MetaProvider.send_message", capture_send):
        db = AsyncMock()
        with patch(
            "app.services.message_service.get_or_create_session",
            new=AsyncMock(return_value=_idle_session()),
        ):
            await message_service.handle_incoming(_make_incoming("תור"), demo_clinic, db)

    assert len(sent_messages) == 1
    assert sent_messages[0].body  # some non-empty reply


async def test_state_machine_exception_sends_error_message(demo_clinic):
    from app.services import message_service

    sent_messages = []

    async def capture_send(self, msg):
        sent_messages.append(msg)

    with (
        patch("app.services.message_service._ai_provider", AsyncMock()),
        patch("app.services.message_service.get_calendar_provider", return_value=AsyncMock()),
        patch(
            "app.services.message_service.get_or_create_session",
            new=AsyncMock(return_value=_idle_session()),
        ),
        patch("app.services.message_service.save_session", new=AsyncMock()),
        patch("app.services.message_service.append_message", new=AsyncMock()),
        patch(
            "app.conversation.state_machine.ConversationStateMachine.process",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch("app.messaging.meta_provider.MetaProvider.send_message", capture_send),
    ):
        db = AsyncMock()
        await message_service.handle_incoming(_make_incoming("תור"), demo_clinic, db)

    assert len(sent_messages) == 1
    assert "טכנית" in sent_messages[0].body


async def test_session_and_messages_are_persisted(demo_clinic):
    from app.services import message_service

    save_session_mock = AsyncMock()
    append_message_mock = AsyncMock()

    with (
        patch("app.services.message_service._ai_provider", AsyncMock()),
        patch("app.services.message_service.get_calendar_provider", return_value=AsyncMock()),
        patch(
            "app.services.message_service.get_or_create_session",
            new=AsyncMock(return_value=_idle_session()),
        ),
        patch("app.services.message_service.save_session", save_session_mock),
        patch("app.services.message_service.append_message", append_message_mock),
        patch("app.messaging.meta_provider.MetaProvider.send_message", new=AsyncMock()),
        patch(
            "app.conversation.state_machine.ConversationStateMachine.process",
            new=AsyncMock(return_value="תשובה"),
        ),
    ):
        db = AsyncMock()
        await message_service.handle_incoming(_make_incoming("תור"), demo_clinic, db)

    save_session_mock.assert_awaited_once()
    assert append_message_mock.await_count == 2  # user + assistant


async def test_session_data_cleared_on_handoff(demo_clinic):
    from app.services import message_service

    session = _idle_session()
    session.data = {"name": "שרה", "service_id": "massage"}

    with (
        patch(
            "app.services.message_service.get_or_create_session",
            new=AsyncMock(return_value=session),
        ),
        patch("app.services.message_service.save_session", new=AsyncMock()),
        patch("app.services.message_service.append_message", new=AsyncMock()),
        patch("app.messaging.meta_provider.MetaProvider.send_message", new=AsyncMock()),
    ):
        db = AsyncMock()
        await message_service.handle_incoming(_make_incoming("נציג"), demo_clinic, db)

    assert session.data == {}
