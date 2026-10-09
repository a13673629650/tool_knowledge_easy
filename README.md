# 这是一个简单的记忆上下文，
# 根据登陆用户分任务记录问答，
# 流程中有知识库检索和tool简单调用，
# 纯学习使用，主要接口路由在chat这个文件当中，其他文件可以忽略不看
#app/core/embedding_factory.py文件当中相关配置改成自己本地的向量知识库 以及向量模型
#.env_template 复制一份改名 .env填自己的大模型api key和调用地址  DATABASE_URL是自己本地的数据库地址

# 安装相关依赖 
# uvicorn main:app --reload --host 0.0.0.0 --port 8000启动项目
# 对应前端仓库地址https://github.com/a13673629650/essay_react 前端安装依赖跑起来就行了
