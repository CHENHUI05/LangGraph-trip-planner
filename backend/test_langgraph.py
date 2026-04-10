import sys
import os

# 将 backend 目录添加到 python 路径
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.agents.langgraph_trip_planner import get_langgraph_trip_planner
from backend.app.models.schemas import TripRequest

def test():
    request = TripRequest(
        city="北京",
        start_date="2024-05-01",
        end_date="2024-05-03",
        travel_days=3,
        preferences=["历史", "文化"],
        transportation="打车",
        accommodation="高档"
    )
    
    print("🚀 开始测试 LangGraph Agent...")
    planner = get_langgraph_trip_planner()
    plan = planner.plan_trip(request)
    
    print("\n✅ 测试成功!")
    print(f"城市: {plan.city}")
    print(f"天数: {len(plan.days)}")
    print(f"建议: {plan.overall_suggestions}")

if __name__ == "__main__":
    test()
