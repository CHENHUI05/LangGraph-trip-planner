"""飞书服务封装"""

import json
import httpx
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_settings
from ..models.schemas import TripRequest
from ..services.llm_service import get_langchain_llm


class FeishuService:
    def __init__(self):
        self.settings = get_settings()
        self.frontend_url = getattr(self.settings, 'frontend_url', 'http://localhost:5173')
        self.app_id = getattr(self.settings, 'feishu_app_id', '')
        self.app_secret = getattr(self.settings, 'feishu_app_secret', '')
        self.tenant_access_token = ""

    async def get_tenant_access_token(self) -> str:
        """获取飞书接口调用凭证 (Tenant Access Token)"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if data.get("code") == 0:
                self.tenant_access_token = data.get("tenant_access_token")
                return self.tenant_access_token
            else:
                raise Exception(f"获取飞书 Token 失败: {data}")

    async def send_text_message(self, receive_id: str, content: str, receive_id_type: str = "open_id"):
        """向用户发送文本消息"""
        await self.get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        import json
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()

    async def parse_natural_language_to_request(self, text: str) -> TripRequest:
        """稳定版：自然语言 → TripRequest（无 JSON 崩溃）"""

        llm = get_langchain_llm()

        today = datetime.now()
        default_start = today + timedelta(days=7)

        # =========================
        # 1️⃣ 强约束 Prompt
        # =========================
        sys_msg = SystemMessage(content=f"""
    你是一个旅行参数提取器。

    请从用户输入中提取信息，并严格输出 JSON（禁止任何多余文本）。

    JSON格式如下：
    {{
        "city": "城市名称",
        "travel_days": 天数（整数）
    }}

    规则：
    - travel_days 必须是整数（例如 3，不是“3天”）
    - 如果没有城市，默认“北京”
    - 如果没有天数，默认 2
    - 不允许输出任何解释或多余文字

    今天日期：{today.strftime('%Y-%m-%d')}
    默认出发日期：{default_start.strftime('%Y-%m-%d')}
    """)

        user_msg = HumanMessage(content=text)

        try:
            # =========================
            # 2️⃣ 调用 LLM
            # =========================
            response = await llm.ainvoke([sys_msg, user_msg])

            raw_text = response.content
            print("🧠 LLM原始输出:", raw_text)

            # =========================
            # 3️⃣ 安全解析 JSON（不用 regex）
            # =========================
            data = json.loads(raw_text)

            city = data.get("city", "北京")
            travel_days = int(data.get("travel_days", 2))

            # =========================
            # 4️⃣ 自动补全日期（关键修复）
            # =========================
            start_date = default_start
            end_date = start_date + timedelta(days=travel_days)

            # =========================
            # 5️⃣ 构造 TripRequest
            # =========================
            trip_request = TripRequest(
                city=city,
                travel_days=travel_days,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),   # ✅ 修复点
                transportation="公共交通",
                accommodation="经济型酒店",
                preferences=[]
            )

            return trip_request

        except Exception as e:
            print(f"❌ 自然语言解析失败: {e}")

            # =========================
            # 6️⃣ 兜底方案（永不崩）
            # =========================
            start_date = default_start
            end_date = start_date + timedelta(days=2)

            return TripRequest(
                city="北京",
                travel_days=2,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                transportation="公共交通",
                accommodation="经济型酒店",
                preferences=[]
            )

    # async def parse_natural_language_to_request(self, text: str) -> TripRequest:
    #     """【神级功能】将用户的自然语言(如'去武汉玩2天')转换为 TripRequest 对象"""
    #     llm = get_langchain_llm()
    #     structured_llm = llm.with_structured_output(TripRequest)

    #     today = datetime.now()
    #     default_start = today + timedelta(days=7)  # 默认下周出发

        
    #     sys_msg = SystemMessage(content=f"""
    #     你是一个参数提取器。请从用户的自然语言中提取旅行请求信息。
    #     今天日期是：{today.strftime('%Y-%m-%d')}。
    #     如果用户没有指明具体日期，请默认设置为 {default_start.strftime('%Y-%m-%d')} 出发。
    #     如果没指明天数，默认为 2 天。交通默认"公共交通"，住宿默认"经济型酒店"。
    #     """)

    #     user_msg = HumanMessage(content=text)

    #     try:
    #         # 利用大模型强大的结构化提取能力，直接生成请求对象！
    #         trip_request = await structured_llm.ainvoke([sys_msg, user_msg])
    #         return trip_request
    #     except Exception as e:
    #         print(f"❌ 自然语言解析失败: {e}")
    #         raise ValueError("无法解析您的旅行需求，请使用更规范的格式，例如：帮我规划去北京的3天行程。")


# 单例
_feishu_service = None


def get_feishu_service():
    global _feishu_service
    if _feishu_service is None:
        _feishu_service = FeishuService()
    return _feishu_service