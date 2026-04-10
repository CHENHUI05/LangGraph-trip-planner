# -- coding: utf-8 --
import asyncio
import os
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI


# ==========================================
# 1. 定义一个简单的测试工具
# ==========================================
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气情况。必须使用此工具来回答天气问题。"""
    print(f"   [底层工具执行] ⚙️ 正在联网查询 {city} 的天气...")
    # 模拟接口延迟和返回结果
    if "北京" in city:
        return "晴朗，气温 25℃，东北风3级，适合出行。"
    elif "上海" in city:
        return "中雨，气温 18℃，建议带伞。"
    return "未知城市，暂无数据。"


# ==========================================
# 2. 主测试流程
# ==========================================
async def main():
    # ⚠️ 请在这里填入你的 API 配置（建议使用支持 Function Calling 的模型）
    # 如果你使用的是智谱、通义、DeepSeek 等，可以修改 base_url 和 model 名字
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["OPENAI_API_BASE"] = ""

    print("🔄 正在初始化 LLM 和 LangGraph Agent...")

    # 初始化 LLM
    llm = ChatOpenAI(model="Qwen/Qwen3.5-122B-A10B")

    # 使用 LangGraph 内置的预编译 ReAct Agent 组装工具
    agent = create_react_agent(llm, tools=[get_weather])

    # 测试问题
    question = "帮我查一下北京今天天气怎么样？"
    print(f"\n👤 [用户提问]: {question}\n")
    print("-" * 50)

    # ==========================================
    # 3. 使用 astream 流式追踪中间调用 (核心测试点)
    # ==========================================
    inputs = {"messages": [HumanMessage(content=question)]}

    # stream_mode="values" 会在每次状态图更新时吐出完整的 state
    async for state in agent.astream(inputs, stream_mode="values"):
        # 每次状态更新，我们只看列表里最新追加的那条消息
        latest_msg = state["messages"][-1]

        # 判断消息的类型并打印相应的中间状态
        if isinstance(latest_msg, HumanMessage):
            # 用户消息，一开始已经打印过了，这里忽略
            pass

        elif isinstance(latest_msg, AIMessage):
            # 检查 AI 是否触发了工具调用
            if latest_msg.tool_calls:
                print(f"🤖 [Agent 决策]: 认为需要调用工具才能回答。")
                for tc in latest_msg.tool_calls:
                    print(f"   👉 准备调用工具名: '{tc['name']}'")
                    print(f"   👉 传入的参数为: {tc['args']}")

            # 检查 AI 是否生成了最终的自然语言回复
            elif latest_msg.content:
                print(f"\n✨ [Agent 最终总结]:\n{latest_msg.content}")

        elif isinstance(latest_msg, ToolMessage):
            # 工具执行完毕后返回给大模型的结果
            print(f"📥 [工具回调]: '{latest_msg.name}' 执行完毕，返回给大模型的数据是:")
            print(f"   {latest_msg.content}")

    print("\n" + "-" * 50)
    print("✅ 测试结束。")


if __name__ == "__main__":
    # Windows 下可能需要避免 EventLoop 报错，加上这句
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())