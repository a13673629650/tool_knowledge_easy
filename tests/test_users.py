import sys
from pathlib import Path
import pytest
# 正确导入，没有2
from httpx import AsyncClient, ASGITransport


# 将项目根目录加入模块搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app

# 声明测试函数为异步，指定 asyncio 测试标记
@pytest.mark.asyncio
async def test_index():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/users/", json={"username": "8888订单", "password": "11222"})
        print(response)
        assert response.status_code == 200
