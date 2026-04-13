# LangGraph智能旅行助手 (飞书版)🌍✈️

基于LangGraph框架构建的智能旅行规划助手,集成高德地图MCP服务和飞书接口,提供个性化的旅行计划生成。

## ✨ 功能特点

- 🤖 **AI驱动的旅行规划**: 基于LangGraph框架的Agent,智能生成详细的多日旅程
- 🗺️ **高德地图集成**: 通过MCP协议接入高德地图服务,支持景点搜索、路线规划、天气查询
- 🧠 **智能工具调用**: Agent自动调用高德地图MCP工具,获取实时POI、路线和天气信息
- 🎨 **现代化前端**: Vue3 + TypeScript + Vite,响应式设计,流畅的用户体验
- 📱 **完整功能**: 包含住宿、交通、餐饮和景点游览时间推荐
- 🗺️ **飞书集成**：集成了飞书机器人应用，可以通过飞书生成对应方案
- 🌐 **全栈公网访问**: 内置完善的 CORS 与环境变量映射设计，支持 Ngrok / ZeroNews等内网穿透工具，轻松实现公网多人访问。

## 🏗️ 技术栈

### 后端
- **框架**: LangGraph 
- **API**: FastAPI
- **MCP工具**: amap-mcp-server (高德地图)
- **LLM**: 推荐使用 **Deepseekv3.2**,兼容 OpenAI 格式接口

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **地图服务**: 高德地图 JavaScript API
- **HTTP客户端**: Axios

## 📁 项目结构

```
LangGraph-trip-planner/
├── backend/                   # 后端服务
│   ├── app/
│   │   ├── agents/            	# Agent实现
│   │   │   └── langgraph_trip_planner.py
│   │   ├── api/               	# FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── feishu.py
│   │   │		├── map.py
│   │   │		├── poi.py
│   │   │       └── trip.py
│   │   ├── services/          	# 服务层
│   │   │   ├── amap_service.py		#高德mcp
│   │   │   ├── feishu_service.py	#飞书函数
│   │   │   └── llm_service.py
│   │   ├── models/            	# 数据模型
│   │   │   └── schemas.py
│   │   └── config.py          # 配置管理
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # Vue组件
│   │   ├── services/          # API服务
│   │   ├── types/             # TypeScript类型
│   │   └── views/             # 页面视图
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

- ## 🚀 快速开始

    ### 前提条件

    - Python 3.10+ & Node.js 18+

    - [高德地图开放平台](https://lbs.amap.com/) Key (Web服务API & Web端JS API)

    - [飞书开放平台](https://open.feishu.cn/) 机器人凭证 (App ID, Secret, Encrypt Key)

    - [硅基流动](https://cloud.siliconflow.cn/i/ckdnC4wD)大模型 API Key (推荐使用Deepseekv3.2),新人有16的抵扣券

### 项目下载

```python
git clone https://github.com/CHENHUI05/LangGraph-trip-planner.git
```

### 后端安装

1. 进入后端目录
```bash
cd backend
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件,填入你的API密钥
```

5. 启动后端服务
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 配置环境变量
```bash
# 创建.env文件, 填入高德地图Web API Key 和 Web端JS API Key
cp .env.example .env
```

4. 启动开发服务器
```bash
npm run dev
```

5. 打开浏览器访问 `http://localhost:5173`

## 📝 使用指南

1. 在首页填写旅行信息:
   - 目的地城市
   - 旅行日期和天数
   - 交通方式偏好
   - 住宿偏好
   - 旅行风格标签
2. 点击"生成旅行计划"按钮
3. 系统将:
   - 调用HelloAgents Agent生成初步计划
   - Agent自动调用高德地图MCP工具搜索景点
   - Agent获取天气信息和路线规划
   - 整合所有信息生成完整行程
4. 查看结果:
   - 每日详细行程
   - 景点信息与地图标记
   - 交通路线规划
   - 天气预报
   - 餐饮推荐

 5.使用飞书机器人直接进行询问

## 🔧 核心实现

### LangGraph Agent集成

```python
from langchain_openai import ChatOpenAI
from app.config import settings  # 引入我们配置好的 Pydantic 设置类

# 1. 创建高德地图 MCP 工具 (安全读取环境变量，杜绝 Key 泄露)
amap_tool = MCPTool(
    name="amap",
    server_command=["uvx", "amap-mcp-server"],
    env={"AMAP_MAPS_API_KEY": settings.amap_api_key}, 
    auto_expand=True
)

# 2. 初始化大模型引擎 (使用环境变量中配置的智谱 GLM)
llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    model=settings.openai_model,
    temperature=0.7
)

# 3. 创建旅行规划 Agent
agent = SimpleAgent(
    name="旅行规划助手",
    llm=llm,
    system_prompt=(
        "你是一个专业的旅行规划助手。你可以自动调用高德地图 MCP 工具来搜索真实景点、"
        "查询天气和规划路线。请根据用户的需求，输出包含精确坐标和图片的结构化行程方案。"
    )
)

# 4. 注册工具
agent.add_tool(amap_tool)
```

### MCP工具调用

Agent可以自动调用以下高德地图MCP工具:
- `maps_text_search`: 搜索景点POI
- `maps_weather`: 查询天气
- `maps_direction_walking_by_address`: 步行路线规划
- `maps_direction_driving_by_address`: 驾车路线规划
- `maps_direction_transit_integrated_by_address`: 公共交通路线规划

## 📄 API文档

启动后端服务后,访问 `http://localhost:8000/docs` 查看完整的API文档。

主要端点:
- `POST /api/trip/plan` - 生成旅行计划
- `GET /api/map/poi` - 搜索POI
- `GET /api/map/weather` - 查询天气
- `POST /api/map/route` - 规划路线
- `POST /api/feishu/webhook` - 飞书接入

## 🤝 贡献指南

欢迎提交Pull Request或Issue!

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents) - 智能体教程
- [HelloAgents框架](https://github.com/jjyaoao/HelloAgents) - 智能体框架
- [高德地图开放平台](https://lbs.amap.com/) - 地图服务
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) - 高德地图MCP服务器

