import os

from  dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model

def get_model():
    model = init_chat_model(
        model="deepseek-ai/DeepSeek-V4-Flash",
        model_provider="openai",
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0.4
    )
    return model