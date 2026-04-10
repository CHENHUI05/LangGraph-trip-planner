import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 加载环境变量
load_dotenv(dotenv_path="backend/.env")

async def test_mcp():
    amap_key = os.getenv("AMAP_API_KEY")
    if not amap_key:
        print("❌ 错误: 未在 backend/.env 中找到 AMAP_API_KEY")
        return

    print(f"🚀 正在启动 MCP 客户端...")
    print(f"📍 使用 API Key: {amap_key[:5]}...{amap_key[-5:]}")

    # 配置 MCP 服务器参数 (使用 uvx 启动 amap-mcp-server)
    server_params = StdioServerParameters(
        command="uvx",
        args=["amap-mcp-server"],
        env={
            "AMAP_MAPS_API_KEY": amap_key,
            "PATH": os.environ.get("PATH", "") # 确保 uvx 能被找到
        }
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. 初始化会话
                print("🔄 正在初始化 MCP 会话...")
                await session.initialize()
                print("✅ 会话初始化成功！")

                # 2. 列出所有工具
                print("\n核心工具列表:")
                print("-" * 50)
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    print(f"🛠️  工具名称: {tool.name}")
                    print(f"📝 描述: {tool.description}")
                    # print(f"输入参数: {tool.inputSchema}")
                    print("-" * 30)

                # 3. 尝试调用一个工具 (查询荆州天气)
                print("\n正在测试工具调用: maps_weather (查询荆州)...")
                try:
                    result = await session.call_tool(
                        "maps_weather", 
                        arguments={"city": "荆州"}
                    )
                    print("📥 调用结果:")
                    for content in result.content:
                        if content.type == "text":
                            print(content.text)
                except Exception as e:
                    print(f"❌ 工具调用失败: {str(e)}")

    except Exception as e:
        print(f"❌ 连接 MCP 服务器失败: {str(e)}")
        print("\n提示: 请确保已安装 uv (pip install uv) 并且网络可以访问 GitHub/PyPI。")

if __name__ == "__main__":
    asyncio.run(test_mcp())
