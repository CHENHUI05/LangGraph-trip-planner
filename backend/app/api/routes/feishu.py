"""飞书消息回调路由"""

from fastapi import APIRouter, Request, BackgroundTasks
from ...config import get_settings

router = APIRouter(prefix="/feishu", tags=["飞书集成"])

# 确保文件顶部有这两行导入
from ...services.feishu_service import get_feishu_service
from ...agents.langgraph_trip_planner import get_langgraph_trip_planner
from .trip import save_plan_to_disk  # 引入我们刚才写的保存函数


async def process_agent_in_background(open_id: str, user_text: str):
    """在后台运行 LangGraph Agent，增加详细的打印日志"""
    print(f"\n========== 后台任务启动 ==========")
    print(f"🎯 接收到用户 Open ID: {open_id}")
    print(f"💬 用户发送的内容: {user_text}")

    if not open_id:
        print("❌ 致命错误：Open ID 为空，无法发送回复！")
        return

    feishu = get_feishu_service()
    planner = get_langgraph_trip_planner()

    try:
        print("🔄 [步骤 1] 尝试向用户发送'收到指令'的提示词...")
        await feishu.send_text_message(
            open_id,
            "🤖 收到指令！正在召唤多位专家为您规划行程，大约需要 30-60 秒，请稍候..."
        )

        print("🔄 [步骤 2] 正在调用大模型解析自然语言...")
        # 🚨 就是这里！这行代码生成了 req，千万不能删！
        req = await feishu.parse_natural_language_to_request(user_text)
        print(f"   解析成功: 目的地={req.city}, 交通={req.transportation}")

        await feishu.send_text_message(
            open_id,
            f"📍 提取到目的地：{req.city}\n📅 日期：{req.start_date} 至 {req.end_date}\n正在生成详细报告..."
        )

        print("🔄 [步骤 3] 正在启动 LangGraph 多智能体规划...")
        plan = await planner.plan_trip_async(req)
        print("   规划完成！准备发送最终报告...")

        # 💥 将生成的行程存入本地，并拿到唯一 ID
        plan_id = save_plan_to_disk(plan)

        # 💥 你的前端服务地址 (开发阶段填 localhost，上线后换成实际域名)
        detail_link = f"{feishu.frontend_url}/result?id={plan_id}"

        # 组装回复 (在结尾加上精美的网页链接)
        reply_text = f"🎉 **{plan.city} {len(plan.days)}日游规划完成！**\n\n"
        for day in plan.days:
            reply_text += f"📅 **{day.description}** ({day.date})\n"
            reply_text += f"🏨 住宿：{day.hotel.name if day.hotel else '暂无'}\n"
            reply_text += f"🚶 游览景点：{', '.join([a.name for a in day.attractions])}\n\n"

        reply_text += f"💰 预估总预算：{plan.budget.total if plan.budget else '未知'} 元\n\n"
        reply_text += f"✨ [👉 点击此处，查看带地图和图片的详细精美行程单]({detail_link})"

        print("🔄 [步骤 4] 正在发送最终报告到飞书...")
        res2 = await feishu.send_text_message(open_id, reply_text)
        print(f"   最终发信结果: {res2}")
        print("========== 后台任务圆满结束 ==========\n")

    except Exception as e:
        print(f"\n❌ 后台处理飞书消息发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        await feishu.send_text_message(open_id, f"⚠️ 抱歉，系统开小差了：{str(e)}")


@router.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    settings = get_settings()

    # 处理 Challenge
    if "challenge" in data:
        return {"challenge": data["challenge"]}

    # 解析 Event
    event_info = data.get("event", {})
    header = data.get("header", {})

    # 打印飞书发来的完整包，看看结构对不对
    print(f"\n📩 收到飞书 Webhook 事件，类型: {header.get('event_type')}")

    if header.get("event_type") == "im.message.receive_v1":
        sender_id = event_info.get("sender", {}).get("sender_id", {}).get("open_id")
        message_info = event_info.get("message", {})

        if message_info.get("message_type") == "text":
            import json
            content = json.loads(message_info.get("content", "{}"))
            user_text = content.get("text", "").strip()

            # 将任务丢进后台
            background_tasks.add_task(process_agent_in_background, sender_id, user_text)

    return {"msg": "success"}