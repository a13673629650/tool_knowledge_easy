from datetime import timedelta, UTC, datetime

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableLambda, RunnablePassthrough  # 把普通函数转可用组件
from passlib.context import CryptContext #密码加密
from sqlalchemy import select #查询方法
from sqlalchemy.ext.asyncio import AsyncSession #数据类型

from app.core.config import settings #.env配置设置
from app.core.embedding_factory import search_knowledge, embedding_documents
from app.core.utils import get_model #大模型
from app.db.models import DBUser #表
from app.dependencies import get_async_db #异步会话
from app.exceptions import BusinessException #自定义错误抛出
from app.core.tools import agent
pwd_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto") #密码加密
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login") #固定写法仅用于接口文档校验
SECRET_KEY = settings.SECRET_KEY #生成依据
ALGORITHM = settings.ALGORITHM  #HS256
ACCESS_TOKEN_EXPIRE_MINUTES = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) #过期时间token
results = search_knowledge() #资料库检索
# model = get_model() #大模型
#加密密码
def hash_password(password: str) -> str:
    return pwd_CONTEXT.hash(password)
#数据库校验密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_CONTEXT.verify(plain_password, hashed_password)

#JWT 生成
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        to_encode.update({"exp": expire})
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#解析token
def decode_access_token(token: str) -> dict:
     try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
     except Exception as e:
         raise e

#根据请求头 获取token查询用户id
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise BusinessException(
                status_code=401,
                message="无效登录凭证1",
                code='401'
            )
    except Exception as e:
        print(f"异常类型：{type(e).__name__}，完整错误信息：{str(e)}")
        raise BusinessException(
            status_code=401,
            message="无效登录凭证2",
            code='401'
        )
        # raise e

    user = await db.execute(select(DBUser).where(DBUser.id == user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise BusinessException(
            status_code=401,
            message="无效登录凭证3",
            code='401'
        )
    return user

# -------------------------- 提示词 --------------------------
#给提示词模板传递参数的函数
def clear_options(ipt: dict) -> dict:
    if not ipt:
        raise ValueError("问题不能为空")
    options = ipt.get("options")
    if not options or not isinstance(options, str):
        raise ValueError("问题不能为空")
    return {
        # 关键修复：必须把 history 透传下去，否则 prompt 里的
        # MessagesPlaceholder("history") 拿不到历史，模型每轮失忆，
        # 出现“上一句说我是张三、下一句问我是谁却答不上来”的现象。
        "options": options.strip(),
        "history": ipt.get("history", []),
        "content": ipt.get("content", "")
    }



def retrieve(question: str) -> str:
    """
    用用户问题去向量库检索，并拼接成【参考资料】文本。
    关键修复：上一版写成 `x.get("options") | results`，而 results 是裸 Retriever 对象，
    `str | Retriever` 在 LangChain 里会抛 TypeError（已实测），导致检索分支直接崩溃、
    content 永远取不到（即大哥说的“content 被吃了”）。
    这里改用显式 results.invoke(question)，行为确定、可正常检索。
    """
    if not question or not isinstance(question, str):
        return ""
    try:
        docs = results.invoke(question)
        return embedding_documents(docs)
    except Exception:
        # 检索失败不要拖垮整轮问答，降级为无参考资料继续回答
        return ""


def build_messages(d: dict) -> list:
    """
    直接构造 messages 列表：把【参考资料】（向量库检索内容）注入 system 消息，
    用户问题作为 human 消息，历史对话夹在中间。
    关键：用字符串拼接构造 SystemMessage，不走 ChatPromptTemplate 的 .format，
    因此知识库文档哪怕含 {} 也不会 KeyError 崩溃；同时满足“content 在 system 里”的需求。
    """
    ctx = (d.get("content") or "").strip()
    question = d.get("options") or ""
    sys_text = (
        "你是一个乐于助人的中文助手，请结合【历史对话】与下方【参考资料】"
        "理解用户意图，保持上下文连贯地回答。若参考资料与问题无关，可忽略。"
    )
    if ctx:
        sys_text += "\n\n【参考资料】\n" + ctx
        messages = [SystemMessage(content=sys_text)]  # 模版预设 角色设定行为 用知识库的情况下
        # messages = []
        agent.system_prompt = sys_text
        print('进入资料检索')
    else:
        agent.system_prompt = """你是一名电商客服助手。回答要礼貌、简洁，不要编造工具返回值中不存在的信息"""
        messages = []  # 模版预设 不用知识库
    for m in (d.get("history") or []):
        messages.append(m)#历史消息拼接
    messages.append(HumanMessage(content=question))
    return messages



#agent结合工具
async def use_agent(lis):
  result =  await agent.ainvoke({
       "messages": lis
   })
  return result["messages"][-1].content

# 已经调通的提示词模板（RAG 增强版，content 注入 system）
def prompt_chain():
    # 全局实例化 Chain，不要在请求里重复创建，避免性能损耗
    # 第一步：用当前问题去向量库检索 -> 拼成 content，与 options/history 一起透传
    chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {
            "options": x.get("options", ""),
            "history": x.get("history", []),
            "content":  retrieve(x.get("options", "")) if "订单" not in x.get("options", "") else "",  # 自定义函数过滤是否调用知识库
        })
        | RunnableLambda(clear_options)        # 校验 + 透传 options/history/content
        | RunnableLambda(build_messages)      # 直接拼 messages，content 进 system
        | RunnableLambda(use_agent)
        # | model
        # | StrOutputParser()
    )

    return chain