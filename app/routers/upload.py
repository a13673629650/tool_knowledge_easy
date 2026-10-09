from datetime   import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

from app.exceptions import BusinessException
from app.services.upload_service import write_log

router = APIRouter(prefix="/api/file",tags=["file"])


FILE_TYPE={
    "image/jpeg",
    "image/png",
    "image/bmp",
    "video/mp4",
    "video/webm",
    "audio/mpeg"
}
FILE_SIZE= 2*1024*1024
UPLOAD_ROOT = Path("upload_files")
UPLOAD_ROOT.mkdir(exist_ok=True, parents=True)
@router.post("/upload/single")
async def upload_file_one( file: UploadFile = File(...)):
    if file.content_type not in FILE_TYPE:
        raise BusinessException(code='content_type',message='格式不匹配',status_code=400)
    if file.size > FILE_SIZE:
        raise BusinessException(code="size > 2*1024*1024",message="File too large",status_code=400)

    suffix =Path(file.filename).suffix #文件后缀
    # 完整安全写法
    new_filename =F"{uuid4().hex}{suffix}"
    upload_files = Path("upload_files").resolve()
    path = (upload_files / new_filename).resolve()
    # 强制校验生成的路径绝对不能跳出upload_files目录
    # 如果用户恶意提交../../etc/passwd作为文件名，这个校验会直接拦截异常路径，避免把文件写入服务器系统目录。
    if not path.is_relative_to(upload_files):
        raise PermissionError("非法文件名，禁止路径遍历")

    data = await file.read()
    with open(path,"wb") as f:
        f.write(data)
    return {"url":f"/static/{new_filename}"}


@router.post("/upload/batch")
async def upload_file_all(background_task:BackgroundTasks,files:List[UploadFile]  = File(...,description="选择多个文件上传")):
    result = []
    for file in files:
        if file.content_type not in FILE_TYPE:
            raise BusinessException(code='content_type', message='格式不匹配', status_code=400)
        if file.size > FILE_SIZE:
            raise BusinessException(code="size>2MB", message=f"{file.filename}文件过大", status_code=400)
        suffix = Path(file.filename).suffix  # 文件后缀
        # 完整安全写法
        new_filename = F"{uuid4().hex}{suffix}"
        upload_files = Path("upload_files").resolve()
        path = (upload_files / new_filename).resolve()
        # 强制校验生成的路径绝对不能跳出upload_files目录
        # 如果用户恶意提交../../etc/passwd作为文件名，这个校验会直接拦截异常路径，避免把文件写入服务器系统目录。
        if not path.is_relative_to(upload_files):
            raise PermissionError("非法文件名，禁止路径遍历")

        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
        result.append({
            "filename": file.filename,
            "new_filename":new_filename,
            "url":f"/static/{new_filename}"
        })
        background_task.add_task(write_log,content=f'{datetime.now()}-{file.filename}-{new_filename}')
    return result
