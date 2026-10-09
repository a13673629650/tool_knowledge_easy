"""
封装Embedding 模型    2026年9月28日
"""
import os

from langchain_chroma import Chroma

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HOME"] = r"D:\huggingface_cache"  # 在电脑上配置环境变量，后边就不用写了，向量模型自动从该目录获取
COLLECTION_NAME = "company_knowledge" #向量数据表名
CHROMA_DB  = r'D:\code\langchain-course-demo\chapter928\chroma_db' #数据库地址

from langchain_huggingface import HuggingFaceEmbeddings
#HuggingFaceEmbeddings 封装好了模型加载、文本分块批量向量化、错误重试的完整逻辑，
# 不用自己手动写transformers的底层加载代码，直接传参数就能生成向量。
def get_embedding_model()->HuggingFaceEmbeddings:
    return  HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",#指定用国内开源最好用的轻量中文向量化模型
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},#开启向量归一化处理，所有输出向量的长度固定为
)
def search_knowledge():
    embedding_model = get_embedding_model()
    store = Chroma(
        embedding_function = embedding_model,
        persist_directory = CHROMA_DB,
        collection_name = COLLECTION_NAME
    )
    results =store.as_retriever(search_kwargs={"k": 4})
    return results
#文档上下文拼接
def embedding_documents(documents):
    return "\n\n".join([doc.page_content for doc in documents])