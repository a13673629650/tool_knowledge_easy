from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.db.database import async_engine
from app.exceptions import BusinessException
from app.exceptions_handlers import exception_unify,validation_exception_unify
from app.middlewares import log_middleware
from app.routers import users, upload, heros, countryes, chat


#只做启动探活和退出资源清理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【启动阶段】仅保留数据库连接探活，完全删掉之前的自动建表逻辑
    # 验证数据库连接配置正常，避免服务启动后直接一堆接口报数据库连接错误
    async with async_engine.connect():
        print("✅ 数据库连接探活成功，服务启动正常")
    yield # 这里开始正式对外提供接口服务

    # 【关闭阶段】保留你的核心逻辑，安全销毁整个异步引擎，彻底释放所有数据库连接
    # 避免服务重启后MySQL残留大量sleep状态的无效连接，占满数据库连接数
    await async_engine.dispose()
    print("✅ 数据库连接池已全部安全销毁，服务正常退出")


app = FastAPI(
    title="库存管理系统后端接口",
    version="v1.0",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory="upload_files"), name="static")
app.middleware("http")(log_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-session-id"],  # 允许前端读取后端返回的新会话ID响应头
)

#常规异常拦截
app.add_exception_handler(BusinessException,exception_unify)
#422异常
app.add_exception_handler(RequestValidationError,validation_exception_unify)

app.include_router(users.router)
app.include_router(upload.router)
app.include_router(heros.router)
app.include_router(countryes.router)

app.include_router(chat.router)

