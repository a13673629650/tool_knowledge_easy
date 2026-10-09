from fastapi import Request


async def log_middleware(request: Request, call_next):
    print('请求前置', f"请求头{request.headers}")
    response = await call_next(request)
    print("请求后置")
    print(f"{request.method}->{request.url}")
    return response