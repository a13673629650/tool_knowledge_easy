from pydantic_settings import BaseSettings

class Settings(BaseSettings):
      DATABASE_URL: str =None  #sql地址
      SECRET_KEY: str ="xxxx-xxx-key"  #token 依据key
      ALGORITHM: str ='HS256'    #token模式
      ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  #token过期时间
      DEEPSEEK_API_KEY:str=None
      DEEPSEEK_BASE_URL:str=None
      LANGCHAIN_TRACING_V2: bool = False
      LANGSMITH_API_KEY: str | None = None
      LANGSMITH_PROJECT: str = "fastPro"
      HTTP_PROXY: str | None = None
      HTTPS_PROXY:str |None = None
      LANGCHAIN_CLIENT_VERIFY_SSL: bool = False
      LANGCHAIN_CLIENT_TIMEOUT:int = 60
      class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings  =  Settings()