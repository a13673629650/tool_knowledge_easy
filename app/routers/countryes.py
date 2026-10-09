from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Country
from app.dependencies import get_async_db
from app.schemas.countryes_schemas import CountriesSchema

router = APIRouter(prefix="/api/countries", tags=["英雄"])

@router.get("/")
async def get_hero(db: AsyncSession = Depends(get_async_db)):
    data = await db.execute(
               select(Country)
         )
    data = data.scalars().all()

    return data