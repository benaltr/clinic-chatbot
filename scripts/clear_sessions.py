"""
Clear all conversation sessions from the database (resets stuck users).
Usage: python -m scripts.clear_sessions
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Conversation
from app.conversation.states import ConversationState


async def clear_sessions() -> None:
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(
            update(Conversation).values(
                state=ConversationState.IDLE,
                state_data={},
            )
        )
        await db.commit()
        print(f"Reset {result.rowcount} conversation(s) to IDLE.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_sessions())
