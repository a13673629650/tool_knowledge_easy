from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal

#会话
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db



