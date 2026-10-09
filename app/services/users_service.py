
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import User
from app.exceptions import BusinessException
from app.schemas.users_schemas import UsersCreate

async def register(body: UsersCreate, db: AsyncSession):
    data = await db.scalar(select(User).where(User.username == body.username).limit(1))
    print(data)
    if data:
        raise BusinessException(
            code='USERNAME_EXIST',
            message='User with that username already exists.',
            status_code=409
        )

    print('-----------------')
    hashed_password = hash_password(body.password)
    obj = User(username=body.username, password=hashed_password)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj