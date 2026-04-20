"""基于 LangGraph 的多智能体旅行规划系统"""

import asyncio
import operator
import sys
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser

# 引入本项目的依赖
from ..services.llm_service import get_langchain_llm
from ..services.amap_service import get_amap_langchain_service
from ..models.schemas import Attraction, DayPlan, Location, Meal, TripPlan, TripRequest


# ============ Agent提示词 ============
ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。
**重要提示:**
1. 必须使用工具 (amap_search) 搜索真实景点，绝不编造！
2. 搜集满足每天2-3个的高质量景点，包含具体名称、地址和经纬度。
3. **最高优先级指令(禁止废话)**：当决定调用工具时，请直接触发工具！**绝对不要**输出诸如“好的”、“我现在为您搜索”、“请稍等”等任何解释性、寒暄性的文字。保持静默，直接行动。
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。
**重要提示:**
1. 必须使用工具 (amap_weather) 查询真实天气，绝不编造！
2. 获取准确的白天/夜间天气、温度、风力等数据。
3. **最高优先级指令(禁止废话)**：当决定调用工具时，请直接触发工具！**绝对不要**输出任何前置文字（如“好的，为您查询”）。保持静默，直接行动。
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。
**重要提示:**
1. 必须使用工具 (amap_search) 搜索真实酒店，绝不编造！
2. 结合用户的住宿偏好进行筛选。
3. **最高优先级指令(禁止废话)**：当决定调用工具时，请直接触发工具！**绝对不要**输出任何解释性或寒暄性的废话。保持静默，直接行动。
"""

# ============ 状态定义 ============
class AgentState(TypedDict):
    request: TripRequest
    attractions_info: str
    weather_info: str
    hotel_info: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    final_plan: TripPlan

# ============ LangGraph Agent ============
class LangGraphTripPlanner:
    """基于 LangGraph 的多智能体旅行规划系统"""

    def __init__(self):
        print("🔄 开始初始化 LangGraph 多智能体架构系统...")
        self.llm = get_langchain_llm()

        # 1. 注入工具服务
        self.tool_service = get_amap_langchain_service()
        self.tools = self.tool_service.get_langchain_tools()

        # 2. 构建各个专业领域的 ReAct 子智能体
        self.attraction_agent = create_react_agent(
            self.llm,
            tools=[self.tools["search"]],
            prompt=ATTRACTION_AGENT_PROMPT
        )
        self.weather_agent = create_react_agent(
            self.llm,
            tools=[self.tools["weather"]],
            prompt=WEATHER_AGENT_PROMPT
        )
        self.hotel_agent = create_react_agent(
            self.llm,
            tools=[self.tools["search"]],
            prompt=HOTEL_AGENT_PROMPT
        )

        # 3. 构建工作流图
        self.graph = self._build_graph()
        print("✅ Multi-Agent 系统初始化成功")

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("search_attractions", self.search_attractions_node)
        workflow.add_node("query_weather", self.query_weather_node)
        workflow.add_node("search_hotels", self.search_hotels_node)
        workflow.add_node("generate_plan", self.generate_plan_node)

        workflow.set_entry_point("search_attractions")
        workflow.add_edge("search_attractions", "query_weather")
        workflow.add_edge("query_weather", "search_hotels")
        workflow.add_edge("search_hotels", "generate_plan")
        workflow.add_edge("generate_plan", END)

        return workflow.compile()

    # =========== 节点实现 ===========

    async def search_attractions_node(self, state: AgentState):
        print(f"\n📍 启动【景点专家Agent】搜索 {state['request'].city} 的景点...")
        request = state["request"]
        keywords = request.preferences[0] if request.preferences else "景点"
        task_msg = f"请搜索 {request.city} 的 {keywords} 相关景点。请调用工具收集足够多的高质量景点信息。"

        agent_state = await self.attraction_agent.ainvoke({"messages": [HumanMessage(content=task_msg)]})
        final_result = agent_state["messages"][-1].content
        print(f"📌 景点专家总结:\n{final_result[:200]}...")

        return {
            "attractions_info": final_result,
            "messages": [HumanMessage(content=f"【景点规划结果】: {final_result}")]
        }

    async def query_weather_node(self, state: AgentState):
        print(f"\n🌤️ 启动【气象专家Agent】查询 {state['request'].city} 天气...")
        request = state["request"]
        task_msg = f"请查询 {request.city} 的天气信息。"

        agent_state = await self.weather_agent.ainvoke({"messages": [HumanMessage(content=task_msg)]})
        final_result = agent_state["messages"][-1].content
        print(f"📌 气象专家总结:\n{final_result[:200]}...")

        return {
            "weather_info": final_result,
            "messages": [HumanMessage(content=f"【气象预报结果】: {final_result}")]
        }

    async def search_hotels_node(self, state: AgentState):
        print(f"\n🏨 启动【酒店管家Agent】搜索 {state['request'].city} 的酒店...")
        request = state["request"]
        task_msg = f"请搜索 {request.city} 的 {request.accommodation} 酒店。"

        agent_state = await self.hotel_agent.ainvoke({"messages": [HumanMessage(content=task_msg)]})
        final_result = agent_state["messages"][-1].content
        print(f"📌 酒店管家总结:\n{final_result[:200]}...")

        return {
            "hotel_info": final_result,
            "messages": [HumanMessage(content=f"【酒店推荐结果】: {final_result}")]
        }

    async def generate_plan_node(self, state: AgentState):
        print("\n📋 启动【首席主控Agent】汇总生成最终行程...")
        request = state["request"]
        attractions = state.get("attractions_info", "暂无景点信息")
        weather = state.get("weather_info", "暂无天气信息")
        hotels = state.get("hotel_info", "暂无酒店信息")

        planner_query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

        **基本信息:**
        - 城市: {request.city}
        - 日期: {request.start_date} 至 {request.end_date}
        - 天数: {request.travel_days}天
        - 交通方式: {request.transportation}
        - 住宿: {request.accommodation}
        - 偏好: {', '.join(request.preferences) if request.preferences else '无'}

        **景点信息:**
        {attractions}

        **天气信息:**
        {weather}

        **酒店信息:**
        {hotels}
        """

        simplified_prompt = SystemMessage(content="""你是行程规划专家。请根据提供的景点、天气和酒店信息，生成合理的旅行计划。
        【最高优先级指令】：
        1. 每天安排2-3个景点，必须包含早中晚三餐。
        2. 优先使用传入的酒店和景点数据。
        3. 📅 日期绝对准确：必须严格按照用户请求的开始日期和结束日期进行排期，绝不能瞎编历史日期！
        4. 🏨 酒店类型必须是中文：`hotel.type` 字段必须是中文（如'经济型酒店'），绝对禁止输出 'hotel' 等英文单词！
        5. 绝对静默，只输出结构化数据。
        """)
        
        parser = PydanticOutputParser(pydantic_object=TripPlan)
        format_instructions = parser.get_format_instructions()

        user_msg = HumanMessage(content=planner_query + "\n\n" + format_instructions)

        try:
            response = await self.llm.ainvoke([simplified_prompt, user_msg])
            final_plan = parser.parse(response.content)
            #structured_llm = self.llm.with_structured_output(TripPlan)
            #final_plan = await structured_llm.ainvoke([simplified_prompt, user_msg])

            # ====================================================
            # 🛠️ 核武级修复 1：算法绝对控制日期与天数
            # ====================================================
            from datetime import datetime, timedelta
            import re

            start_date_obj = datetime.strptime(request.start_date, "%Y-%m-%d")

            for i, day in enumerate(final_plan.days):
                correct_date = start_date_obj + timedelta(days=i)
                day.date = correct_date.strftime("%Y-%m-%d")
                day.day_index = i

                clean_desc = re.sub(r'^(第\s*\d+\s*天|Day\s*\d+)[\s：:\-]*', '', day.description)
                day.description = f"第{i + 1}天：{clean_desc}"

            # ====================================================
            # 🛠️ 核武级修复 2：彻底重算每一分钱的预算
            # ====================================================
            total_attractions = 0
            total_hotels = 0
            total_meals = 0

            for day in final_plan.days:
                if getattr(day, 'hotel', None) and getattr(day.hotel, 'estimated_cost', None):
                    total_hotels += int(day.hotel.estimated_cost)
                for attr in getattr(day, 'attractions', []):
                    if getattr(attr, 'ticket_price', None):
                        total_attractions += int(attr.ticket_price)
                for meal in getattr(day, 'meals', []):
                    if getattr(meal, 'estimated_cost', None):
                        total_meals += int(meal.estimated_cost)

            total_transport = 200
            if getattr(final_plan, 'budget', None) and getattr(final_plan.budget, 'total_transportation', None):
                total_transport = int(final_plan.budget.total_transportation)

            from ..models.schemas import Budget
            final_plan.budget = Budget(
                total_attractions=total_attractions,
                total_hotels=total_hotels,
                total_meals=total_meals,
                total_transportation=total_transport,
                total=total_attractions + total_hotels + total_meals + total_transport
            )
            # ====================================================

            return {"final_plan": final_plan}

        except Exception as e:
            print(f"❌ 主控 Agent 生成计划失败: {str(e)}")
            return {"final_plan": self._create_fallback_plan(request)}


    # =========== 外部调用入口 & 兜底 ===========

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        from datetime import datetime, timedelta
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i + 1}天行程 (主控生成失败备用)",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}著名景点", address=f"{request.city}中心",
                        location=Location(longitude=116.4, latitude=39.9), visit_duration=120,
                        description="这是一个默认景点", category="景点"
                    )
                ],
                meals=[
                    Meal(type="breakfast", name="当地早餐", description="特色早餐"),
                    Meal(type="lunch", name="当地午餐", description="特色午餐"),
                    Meal(type="dinner", name="当地晚餐", description="特色晚餐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city, start_date=request.start_date, end_date=request.end_date,
            days=days, weather_info=[], overall_suggestions="备用兜底计划。"
        )

    async def plan_trip_async(self, request: TripRequest) -> TripPlan:
        """异步执行入口"""
        print(f"\n🚀 开始 LangGraph 多智能体协作规划: {request.city} {request.travel_days}日游...")

        initial_state = {
            "request": request,
            "attractions_info": "",
            "weather_info": "",
            "hotel_info": "",
            "messages": [],
            "final_plan": None
        }

        try:
            final_state = await self.graph.ainvoke(initial_state)
            if not final_state.get("final_plan"):
                raise ValueError("Graph 执行完毕，但没有生成 final_plan")
            return final_state["final_plan"]

        except Exception as e:
            print(f"❌ 图执行过程中发生致命错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def plan_trip(self, request: TripRequest) -> TripPlan:
        """同步执行入口"""
        old_policy = asyncio.get_event_loop_policy()
        if sys.platform.startswith("win"):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass
        try:
            return asyncio.run(self.plan_trip_async(request))
        finally:
            try:
                asyncio.set_event_loop_policy(old_policy)
            except Exception:
                pass

# 全局实例
_langgraph_planner = None

def get_langgraph_trip_planner() -> LangGraphTripPlanner:
    global _langgraph_planner
    if _langgraph_planner is None:
        _langgraph_planner = LangGraphTripPlanner()
    return _langgraph_planner