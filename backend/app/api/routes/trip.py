"""旅行规划API路由"""

from fastapi import APIRouter, HTTPException
import uuid
import json
import os
from ...models.schemas import (
    TripRequest,
    TripPlanResponse,
    TripPlan
)
from ...agents.langgraph_trip_planner import get_langgraph_trip_planner

router = APIRouter(prefix="/trip", tags=["旅行规划"])
PLAN_DIR = "saved_plans"
os.makedirs(PLAN_DIR, exist_ok=True)  # 启动时自动创建存储文件夹

@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    生成旅行计划

    Args:
        request: 旅行请求参数

    Returns:
        旅行计划响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 收到旅行规划请求 (LangGraph):")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        # 获取 LangGraph Agent 实例
        print("🔄 获取 LangGraph 多智能体系统实例...")
        agent = get_langgraph_trip_planner()

        # 生成旅行计划
        print("🚀 开始生成旅行计划...")
        trip_plan = await agent.plan_trip_async(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功 (LangGraph)",
            data=trip_plan
        )

    except Exception as e:
        print(f"❌ 生成旅行计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        # 检查 Agent 是否可用
        agent = get_langgraph_trip_planner()
        
        return {
            "status": "healthy",
            "service": "trip-planner",
            "agent_framework": "LangGraph",
            "model": agent.llm.model_name
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )


# ================= 行程存储工具 =================

def save_plan_to_disk(plan: TripPlan) -> str:
    """将生成的计划保存到本地文件，并返回唯一 ID"""
    plan_id = str(uuid.uuid4().hex)  # 生成唯一防猜解的 ID
    file_path = os.path.join(PLAN_DIR, f"{plan_id}.json")

    # 存入本地文件
    with open(file_path, "w", encoding="utf-8") as f:
        # 如果是 Pydantic V2，使用 model_dump
        plan_dict = plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()
        json.dump(plan_dict, f, ensure_ascii=False, indent=2)

    return plan_id


# ================= 新增查询接口 =================
# 假设你的 router 是这么定义的： router = APIRouter(...)
@router.get("/plan/{plan_id}")
async def get_plan_by_id(plan_id: str):
    """前端根据 ID 获取行程单详情"""
    file_path = os.path.join(PLAN_DIR, f"{plan_id}.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="行程不存在或已过期")

    with open(file_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    return {
        "success": True,
        "message": "获取成功",
        "data": plan_data
    }