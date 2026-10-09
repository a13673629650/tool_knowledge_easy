from typing import Optional

from pydantic import BaseModel, Field


#用户注册请求体
class UsersCreate(BaseModel):
    username: str= Field(...,max_length=20,min_length=3)
    password: str= Field(...,max_length=20,min_length=5)

class Token(BaseModel):
    access_token: str
    token_type: str

class UserRegisterForm(BaseModel):
    username: str
    password: str
class ChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
