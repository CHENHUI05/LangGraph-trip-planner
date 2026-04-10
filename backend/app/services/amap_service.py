"""面向 LangChain 的高德地图 MCP 服务封装"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession

from ..config import get_settings
from ..models.schemas import MapSearchInput, WeatherInput


class AmapLangchainService:
    """高德地图 MCP 服务 (LangChain 工具版)"""

    def __init__(self):
        self.settings = get_settings()
        self.mcp_server_params = self._build_mcp_server_params()
        print("✅ Amap LangChain MCP 服务初始化完成")

    def _build_mcp_server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "amap_mcp_server"],
            env={
                "AMAP_MAPS_API_KEY": self.settings.amap_api_key,
                "PATH": os.environ.get("PATH", ""),
            },
        )

    # ================= 工具注册 =================

    def get_langchain_tools(self) -> Dict[str, StructuredTool]:
        """获取所有已封装为 LangChain 标准的工具"""

        async def amap_search(keywords: str, city: str) -> str:
            """搜索指定城市的景点、酒店、餐厅等POI信息"""
            raw_text = await self._mcp_call_tool("maps_text_search", {"keywords": keywords, "city": city})
            return self._format_poi_search_result(raw_text)

        async def amap_weather(city: str) -> str:
            """查询指定城市的实时天气和预报"""
            raw_text = await self._mcp_call_tool("maps_weather", {"city": city})
            return self._format_weather_result(raw_text)

        search_tool = StructuredTool.from_function(
            coroutine=amap_search,
            name="amap_search",
            description="高德地图搜索工具：搜索指定城市的景点、酒店、餐厅等位置及详细信息",
            args_schema=MapSearchInput
        )

        weather_tool = StructuredTool.from_function(
            coroutine=amap_weather,
            name="amap_weather",
            description="高德地图天气工具：查询指定城市的实时天气状况和未来天气预报",
            args_schema=WeatherInput
        )

        return {"search": search_tool, "weather": weather_tool}

    # ================= MCP 底层调用 =================

    async def _mcp_call_tool_async(self, name: str, arguments: Dict[str, Any]) -> str:
        print(f"🧩 🔧 Agent 触发底层 MCP 工具: {name}({arguments})")
        async with stdio_client(self.mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments=arguments)
                parts: List[str] = [c.text for c in result.content if getattr(c, "type", None) == "text"]
                return "\n".join(parts).strip()

    def _mcp_call_tool_sync(self, name: str, arguments: Dict[str, Any]) -> str:
        old_policy = asyncio.get_event_loop_policy()
        if sys.platform.startswith("win"):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        try:
            return asyncio.run(self._mcp_call_tool_async(name, arguments))
        finally:
            try:
                asyncio.set_event_loop_policy(old_policy)
            except Exception:
                pass

    async def _mcp_call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        return await asyncio.to_thread(self._mcp_call_tool_sync, name, arguments)

    # ================= 数据清洗与格式化 =================

    @staticmethod
    def _extract_json_str(content: str) -> str:
        if "```json" in content:
            return content.split("```json")[1].split("```")[0].strip()
        if "```" in content:
            return content.split("```")[1].split("```")[0].strip()
        return content.strip()

    @staticmethod
    def _safe_json_loads(text: str) -> Any:
        try:
            return json.loads(text)
        except Exception:
            pass
        s = AmapLangchainService._extract_json_str(text)
        try:
            return json.loads(s)
        except Exception:
            pass
        left = s.find("{")
        right = s.rfind("}")
        if left != -1 and right != -1 and right > left:
            try:
                return json.loads(s[left: right + 1])
            except Exception:
                pass
        left = s.find("[")
        right = s.rfind("]")
        if left != -1 and right != -1 and right > left:
            try:
                return json.loads(s[left: right + 1])
            except Exception:
                pass
        return {"raw_text": text}

    @staticmethod
    def _format_poi_search_result(raw_text: str, top_k: int = 10) -> str:
        data = AmapLangchainService._safe_json_loads(raw_text)
        if isinstance(data, dict) and data.get("error"):
            return raw_text
        pois = None
        if isinstance(data, dict):
            for key in ("pois", "data", "results", "result", "items"):
                val = data.get(key)
                if isinstance(val, list):
                    pois = val
                    break
            if pois is None and isinstance(data.get("pois"), str):
                return raw_text
        elif isinstance(data, list):
            pois = data
        if not pois:
            return raw_text
        lines: List[str] = []
        for i, poi in enumerate(pois[:top_k], start=1):
            if not isinstance(poi, dict):
                continue
            name = poi.get("name") or poi.get("title") or poi.get("poi_name") or poi.get("poiName")
            address = poi.get("address") or poi.get("addr") or poi.get("adname") or poi.get("pname")
            location = poi.get("location") or poi.get("loc")
            if isinstance(location, dict):
                lng = location.get("longitude")
                lat = location.get("latitude")
                location = f"{lng},{lat}" if lng is not None and lat is not None else None
            if name and address and location:
                lines.append(f"{i}. {name}｜{address}｜{location}")
            elif name and address:
                lines.append(f"{i}. {name}｜{address}")
            elif name:
                lines.append(f"{i}. {name}")
        return "\n".join(lines) if lines else raw_text

    # ================= 供普通 API 路由直接调用的方法 =================

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """获取 POI 详情 (供 poi.py 等前端路由获取图片使用)"""
        try:
            # 直接复用我们封装好的同步 MCP 调用方法
            result = self._mcp_call_tool_sync("maps_search_detail", {"id": poi_id})

            import json
            import re

            # 从返回结果中提取 JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"raw": result}

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}
    @staticmethod
    def _format_weather_result(raw_text: str) -> str:
        data = AmapLangchainService._safe_json_loads(raw_text)
        if isinstance(data, dict) and data.get("error"):
            return raw_text
        if isinstance(data, dict):
            lives = data.get("lives")
            if isinstance(lives, list) and lives and isinstance(lives[0], dict):
                x = lives[0]
                city = x.get("city")
                weather = x.get("weather")
                temperature = x.get("temperature")
                winddirection = x.get("winddirection")
                windpower = x.get("windpower")
                reporttime = x.get("reporttime")
                parts = []
                if city: parts.append(str(city))
                if weather: parts.append(str(weather))
                if temperature: parts.append(f"{temperature}℃")
                if winddirection or windpower: parts.append(f"{winddirection or ''}{windpower or ''}".strip())
                if reporttime: parts.append(f"更新时间:{reporttime}")
                return "｜".join(parts) if parts else raw_text
            forecasts = data.get("forecasts")
            if isinstance(forecasts, list) and forecasts and isinstance(forecasts[0], dict):
                f0 = forecasts[0]
                city = f0.get("city")
                casts = f0.get("casts")
                if isinstance(casts, list) and casts and isinstance(casts[0], dict):
                    c0 = casts[0]
                    date = c0.get("date")
                    dayweather = c0.get("dayweather")
                    daytemp = c0.get("daytemp")
                    nightweather = c0.get("nightweather")
                    nighttemp = c0.get("nighttemp")
                    s = []
                    if city: s.append(str(city))
                    if date: s.append(str(date))
                    if dayweather or daytemp: s.append(
                        f"白天:{dayweather or ''}{daytemp and (daytemp + '℃') or ''}".strip())
                    if nightweather or nighttemp: s.append(
                        f"夜间:{nightweather or ''}{nighttemp and (nighttemp + '℃') or ''}".strip())
                    return "｜".join([x for x in s if x]) if s else raw_text
        return raw_text

# 单例模式
_amap_langchain_service = None

def get_amap_langchain_service() -> AmapLangchainService:
    global _amap_langchain_service
    if _amap_langchain_service is None:
        _amap_langchain_service = AmapLangchainService()
    return _amap_langchain_service