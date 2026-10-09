

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.core.utils import get_model
from app.db.models import OrderDO
from app.dependencies import get_async_db

# 状态映射
STATUS_MAP = {0: "待付款", 1: "已付款", 2: "已发货", 3: "已完成", 4: "已取消", 5: "售后中"}

ORDER_FMT = (
    "订单编号：{order_no}\n"
    "用户ID：{user_id}\n"
    "订单状态：{status}\n"
    "商品：{goods_name}\n"
    "实付金额：{pay_amount}元\n"
    "下单时间：{create_time}\n"
    "支付时间：{pay_time}\n"
    "发货时间：{delivery_time}\n"
)


def fmt(item: OrderDO) -> str:
    return ORDER_FMT.format(
        order_no=item.order_no,
        user_id=item.user_id,
        status=STATUS_MAP[item.order_status],
        goods_name=item.goods_name,
        pay_amount=item.pay_amount,
        create_time=item.create_time,
        pay_time=item.pay_time if item.pay_time else "未支付",
        delivery_time=item.delivery_time if item.delivery_time else "未发货",
    )


@tool
async def query_order_by_no(order_no: str) -> str:
    """输入订单编号，查询单条订单全部字段，自动翻译数字状态为中文"""
    async for db in get_async_db():
        res = (
            await db.execute(select(OrderDO).where(OrderDO.order_no == order_no))
        ).scalar_one_or_none()
        if not res:
            return "订单不存在"
        return fmt(res)


@tool
async def list_user_orders(user_id: str, status_name: str = None) -> str:
    """查询某用户所有订单，可指定状态过滤，返回订单号、商品、金额、状态"""
    async for db in get_async_db():
        print(type(db))
        stmt = select(OrderDO).where(OrderDO.user_id == user_id)
        if status_name is not None:
            if status_name not in STATUS_MAP.values():
                return "不存在的订单状态"
            status = next(k for k, v in STATUS_MAP.items() if v == status_name)
            stmt = stmt.where(OrderDO.order_status == status)
        data = (await db.execute(stmt)).scalars().all()
        if not data:
            return "用户不存在" if status_name is None else "该状态下无订单"
        return "\n".join(fmt(item) for item in data)


@tool
async def count_order_stat(user_id: str = None) -> str:
    """统计指定用户 / 全部用户下，各状态订单数量、总消费金额"""
    async for db in get_async_db():
        stmt = select(OrderDO)
        if user_id:
            stmt = stmt.where(OrderDO.user_id == user_id)
        data = (await db.execute(stmt)).scalars().all()
        if not data:
            return "无订单数据"
        cnt = defaultdict(int)
        total = 0.0
        for item in data:
            cnt[STATUS_MAP[item.order_status]] += 1
            total += float(item.pay_amount or 0)
        summary = "\n".join(f"{k}：{v} 单" for k, v in cnt.items())
        return f"订单状态统计：\n{summary}\n总消费金额：{total:.2f}元（共 {len(data)} 单）"


@tool
async def update_order_status(order_no: str, target_status: str) -> str:
    """根据订单号更新订单状态，同步更新发货 / 支付时间"""
    async for db in get_async_db():
        data = (
            await db.execute(select(OrderDO).where(OrderDO.order_no == order_no))
        ).scalar_one_or_none()
        if not data:
            return "不存在的订单"
        if target_status not in STATUS_MAP.values():
            return "不存在的状态"
        status = next(k for k, v in STATUS_MAP.items() if v == target_status)
        setattr(data, "order_status", status)
        await db.commit()
        await db.refresh(data)
        return f"修改{order_no}状态已变更{target_status}"

from langchain.agents import create_agent
model = get_model()
agent = create_agent(
        model=model,
        tools=[query_order_by_no, list_user_orders, count_order_stat, update_order_status],
        )
async def main():
    while True:
        options = input("用户：")
        if not options:
            continue
        if options == "exit":
            break
        # 关键：工具是 async def，必须用异步 ainvoke，否则触发
        # NotImplementedError: StructuredTool does not support sync invocation
        result = await agent.ainvoke({"messages": [HumanMessage(content=options)]})
        print(result["messages"][-1].content)

if __name__ == "__main__":
    import asyncio

    # from langchain.agents import create_agent
    #
    # model = get_model()
    # agent = create_agent(
    #     model=model,
    #     tools=[query_order_by_no, list_user_orders, count_order_stat, update_order_status],
    #     system_prompt="你是一名电商客服助手。回答要礼貌、简洁，不要编造工具返回值中不存在的信息。",
    # )

    # async def main() -> None:
    #     while True:
    #         options = input("用户：")
    #         if not options:
    #             continue
    #         if options == "exit":
    #             break
    #         # 关键：工具是 async def，必须用异步 ainvoke，否则触发
    #         # NotImplementedError: StructuredTool does not support sync invocation
    #         result = await agent.ainvoke({"messages": [HumanMessage(content=options)]})
    #         print(result["messages"][-1].content)
    agent.system_prompt="""你是一名电商客服助手。回答要礼貌、简洁，不要编造工具返回值中不存在的信息。"""
    asyncio.run(main())
