from fastapi import APIRouter
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.db.models import DBUser
from app.dependencies import get_async_db
from app.exceptions import BusinessException
from app.schemas.users_schemas import UsersCreate, UserRegisterForm
from app.services.users_service import register
router = APIRouter(prefix="/api/users",tags=["users"])

@router.post("/")
async def create_user(request: UsersCreate, db: AsyncSession = Depends(get_async_db)):
        print("请求进入业务逻辑，username是：", request.username)
        data = await register(request,db)
        return data


# 用户注册
@router.post("/register")
async def register(form: UserRegisterForm, db: AsyncSession = Depends(get_async_db)):
        exist_user = await db.execute(select(DBUser).where(DBUser.username == form.username))
        if exist_user.scalar_one_or_none():
                raise BusinessException(status_code=400, message="用户名已存在",code='user_exist')

        new_user = DBUser(
                username=form.username,
                hashed_password=hash_password(form.password)
        )
        db.add(new_user)
        await db.commit()
        return {"code": 200, "msg": "注册成功"}


# 用户登录
@router.post("/login")
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_async_db)
):
        user = await db.execute(select(DBUser).where(DBUser.username == form_data.username))
        user = user.scalar_one_or_none()
        if not user or not verify_password(form_data.password, user.hashed_password):
                raise BusinessException(status_code=401, message="用户名或密码错误",code='user_exist password')
        token = create_access_token({"user_id":user.id})
        return {"access_token": token, "token_type": "bearer"}
