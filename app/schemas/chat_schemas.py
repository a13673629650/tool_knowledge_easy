from typing import Optional

from pydantic import BaseModel, Field


class TokenResp(BaseModel):
    access_token: str
    token_type: str

class RegisterReq(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=6)

class ChatStreamReq(BaseModel):
    user_input: str
    session_id: Optional[int] = None

class SessionItemResp(BaseModel):
    session_id: int = Field(alias="id")
    first_message: str

    class Config:
        populate_by_name = True

class MessageItemResp(BaseModel):
    role: str
    content: str