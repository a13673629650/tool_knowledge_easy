from fastapi import APIRouter, Depends
from httpx2 import query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Hero, Country
from app.dependencies import get_async_db
from app.exceptions import BusinessException
from app.schemas.heros_schemas import CreateHeroes, UpdateHeroes

router = APIRouter(prefix="/api/heroes", tags=["英雄"])
#/api/heroes?keyword=关
@router.get("/")
async def get_hero(keyword:str='',db: AsyncSession = Depends(get_async_db)):
    query = select(
        Hero.id,
        Hero.name,
        Hero.power,
        Hero.countryId,
        Country.name.label("countryName"),
    ).join(
        Country, Hero.countryId == Country.id,
        isouter=True
    )
    if keyword:
        query= query.where(Hero.name.ilike(f"%{keyword}%"))
    data = await db.execute(
        query
    )
    data = data.mappings().all()
    return data



#POST /api/heroes`
@router.post("/")
async def create_heroes(body:CreateHeroes,db: AsyncSession = Depends(get_async_db)):
     if not body.name:
         raise BusinessException(
             code="name is not null",
             message="缺少参数",
             status_code=400
         )
     if not body.power:
         raise BusinessException(
             code="power is not null",
             message="缺少参数",
             status_code=400
         )
     if not body.countryId:
         raise BusinessException(
             code="countryId is not null",
             message="缺少参数",
             status_code=400
         )
     data  = Hero(
         name=body.name,
         power=body.power,
         countryId=body.countryId
     )
     db.add(data)
     await db.commit()
     await db.refresh(data)
     return {
              "message": "成功"
            }

#PUT /api/heroes/{id}`
@router.put("/{item_id}")
async  def update_heroes(item_id:int,body:UpdateHeroes,  db: AsyncSession = Depends(get_async_db)):
    data = await db.scalar(
        select(Hero).where(Hero.id == item_id)
    )
    if not data:
        raise BusinessException(
            code="id is not null",
            message="修改数据不存在",
            status_code = 400
        )
    body_copy  = body.model_dump(exclude_unset=True)
    for key, value in body_copy.items():
        setattr(data, key, value)
    await db.commit()
    await db.refresh(data)
    return {
              "message": "成功"
            }

# `DELETE /api/heroes/{id}`
@router.delete("/{item_id}")
async def delete_heroes(item_id:int,db: AsyncSession = Depends(get_async_db)):
    data = await db.scalar(
        select(Hero).where(Hero.id == item_id)
    )
    if not data:
        raise BusinessException(
            code="id is not null",
            message="删除英雄不存在",
            status_code = 400
        )
    await db.delete(data)
    await db.commit()
    return {
        "message": "成功"
    }
@router.get("/{item_id}")
async def get_hero_item(item_id:int,db: AsyncSession = Depends(get_async_db)):
    query = select(Hero).where(Hero.id == item_id)
    data = await db.execute(query)
    data = data.scalar_one_or_none()
    res  = await db.scalar(
       select(Country).where(Hero.countryId == Country.id)
    )

    return{
          "id": data.id,
          "name": data.name,
          "power": data.power,
          "countryId": data.countryId,
          "countryName": res.name
        }