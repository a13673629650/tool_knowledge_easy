import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.exceptions import BusinessException
from app.core.security import get_current_user, prompt_chain
from app.db.models import DBUser, DBDialogueSession, DBDialogueItem
from app.dependencies import get_async_db
from app.schemas.chat_schemas import ChatStreamReq

chain = prompt_chain()
# 仅用于 Swagger 文档展示 OAuth2 密码流，不参与实际鉴权（鉴权走 get_current_user）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

router = APIRouter(
    prefix="/api/chat",
    tags=["知识问答"],
)


def _truncate(text: str, max_len: int = 255) -> str:
    return text if len(text) <= max_len else text[:max_len]


def _extract_text(chunk) -> str:
    """LangChain astream 返回的不一定是纯字符串，可能是 AIMessageChunk / dict / [(type,text)]，统一抽成字符串。"""
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    if hasattr(chunk, "content"):
        content = chunk.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # 部分模型 content 是 [{type:'text', text:...}]
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content)
    if isinstance(chunk, dict):
        return chunk.get("content") or chunk.get("text") or ""
    return str(chunk)


def _sse(payload: dict) -> str:
    """统一 SSE 输出：所有数据 JSON 序列化，彻底避免 chunk 里的换行/特殊字符破坏协议。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
        req: ChatStreamReq,
        request: Request,
        current_user: DBUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    user_input = (req.user_input or "").strip()
    print(user_input,'66行')
    if not user_input:

        raise BusinessException(status_code=400, message="提问内容不能为空", code="400")

    # -------------------- 第一步：处理会话（新建/复用），拿到 session_id --------------------
    new_session_flag = False
    target_session = None
    if not req.session_id:
        new_session_flag = True
        new_session = DBDialogueSession(
            user_id=current_user.id,
            first_message=_truncate(user_input),
        )
        db.add(new_session)
        await db.flush()
        session_id = new_session.id
    else:
        result = await db.execute(
            select(DBDialogueSession).where(
                DBDialogueSession.id == req.session_id,
                DBDialogueSession.user_id == current_user.id,
            )
        )
        target_session = result.scalar_one_or_none()
        print(target_session,'91行')
        if not target_session:
            raise BusinessException(status_code=400, message="无效会话ID", code="400")
        session_id = req.session_id

    # -------------------- 第二步：先落库 user 消息并拿到自增 id --------------------
    user_msg = DBDialogueItem(
        session_id=session_id,
        role="user",
        content=user_input,
    )
    db.add(user_msg)
    await db.flush()
    user_msg_id = user_msg.id  # flush 后已分配，无需再 refresh

    # -------------------- 第三步：用 user_msg_id 过滤，取最近 20 条历史（≈10轮，保留长上下文，不含当前这条） --------------------
    history_raw = await db.execute(
        select(DBDialogueItem)
        .where(DBDialogueItem.session_id == session_id)
        .where(DBDialogueItem.id < user_msg_id)
        .order_by(DBDialogueItem.create_time.desc())
        .limit(20)
    )
    history_messages = history_raw.scalars().all()

    chat_history: list[BaseMessage] = []
    for msg in reversed(history_messages):
        if msg.role == "user":
            chat_history.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            chat_history.append(AIMessage(content=msg.content))

    # -------------------- 流式生成器 --------------------
    async def generate_ai_response() -> AsyncGenerator[str, None]:
        full_ai_content = ""
        completed = False
        try:
            async for chunk in chain.astream({
                "options": user_input,
                "history": chat_history,
            }):
                print('正在思考----检索数据中', '132行')
                text = _extract_text(chunk)
                if not text:
                    continue
                full_ai_content += text
                yield _sse({"type": "content", "data": text})

                # 客户端断开则提前结束，避免无意义地继续占用模型
                if await request.is_disconnected():
                    break

            completed = True
            yield _sse({"type": "done"})

        except ValueError as e:
            # clear_options 抛出的空提问等可预期错误
            await db.rollback()
            yield _sse({"type": "error", "data": str(e)})
        except Exception as e:
            await db.rollback()
            yield _sse({"type": "error", "data": f"大模型生成出错：{str(e)}"})
        finally:
            # 仅在正常完成时提交，保证 user + ai 原子写入；异常/断连则回滚，不留脏数据
            if completed:
                try:
                    if full_ai_content:
                        db.add(DBDialogueItem(
                            session_id=session_id,
                            role="ai",
                            content=full_ai_content,
                        ))
                    if not new_session_flag and target_session is not None:
                        target_session.update_time = datetime.now()
                    await db.commit()
                except Exception:
                    await db.rollback()
                    yield _sse({"type": "error", "data": "对话保存失败，请稍后重试"})
            else:
                # 断连或未正常完成：回滚本次未提交的写入
                await db.rollback()

    return StreamingResponse(
        generate_ai_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "x-session-id": str(session_id),
        },
    )


# 获取用户所有会话列表
@router.get("/history/sessions")
async def get_sessions(
        current_user: DBUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(DBDialogueSession)
        .where(DBDialogueSession.user_id == current_user.id)
        .order_by(DBDialogueSession.update_time.desc())
    )
    return [
        {
            "session_id": s.id,
            "first_message": s.first_message,
            "create_time": s.create_time.isoformat() if s.create_time else None,
            "update_time": s.update_time.isoformat() if s.update_time else None,
        }
        for s in result.scalars().all()
    ]


# 获取单个会话完整对话
@router.get("/history/sessions/{session_id}")
async def get_chat_history(
        session_id: int,
        current_user: DBUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(DBDialogueSession).where(
            DBDialogueSession.id == session_id,
            DBDialogueSession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise BusinessException(status_code=401, message="对话不存在", code="401")

    items_raw = await db.execute(
        select(DBDialogueItem)
        .where(DBDialogueItem.session_id == session_id)
        .order_by(DBDialogueItem.create_time.asc())
    )
    items = items_raw.scalars().all()
    # 关键修复：必须返回可 JSON 序列化的 dict，不能直接返回 ORM 对象
    return {
        "code": 200,
        "data": [
            {
                "id": it.id,
                "role": it.role,
                "content": it.content,
                "create_time": it.create_time.isoformat() if it.create_time else None,
            }
            for it in items
        ],
    }


# 删除会话（多任务管理）：items 通过 cascade 自动清理
@router.delete("/history/{session_id}")
async def delete_session(
        session_id: int,
        current_user: DBUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(DBDialogueSession).where(
            DBDialogueSession.id == session_id,
            DBDialogueSession.user_id == current_user.id,
        )
    )
    target_session = result.scalar_one_or_none()
    if not target_session:
        raise BusinessException(status_code=404, message="会话不存在", code="404")
    await db.delete(target_session)
    await db.commit()
    return {"code": 200, "message": "已删除"}
