
from app.exceptions import BusinessException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
def exception_unify(
        request:Request,
        exception:BusinessException,
):
    return JSONResponse(
        status_code = exception.status_code,
        content = {
            "code" : exception.code,
            "message" : exception.message,
            "path":request.url.path
        }
    )

def validation_exception_unify(
        request:Request,
        exception:RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数异常",
            "path": request.url.path
        }
    )