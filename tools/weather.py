"""天气工具 - Mock 实现，模拟查询天气"""

import json
import os
import random
from agent.tool_registry import Tool

_WEATHER_FILE = os.path.join(os.path.dirname(__file__), "..", "weather_data.json")
_DEFAULT_DATA: dict[str, str] = {
    "北京": "晴，25°C，湿度 40%，南风 2 级",
    "上海": "多云，28°C，湿度 65%，东南风 3 级",
    "广州": "阵雨，30°C，湿度 80%，南风 3 级",
    "深圳": "多云转阴，29°C，湿度 75%，南风 2 级",
    "成都": "阴，22°C，湿度 70%，北风 1 级",
    "杭州": "晴，27°C，湿度 55%，东风 2 级",
    "武汉": "小雨，24°C，湿度 85%，北风 3 级",
    "南京": "多云，26°C，湿度 60%，东风 2 级",
    "重庆": "晴，31°C，湿度 50%，西南风 2 级",
    "西安": "晴，23°C，湿度 35%，西北风 3 级",
    "Tokyo": "Clear, 22°C, Humidity 50%, Light breeze",
    "New York": "Partly cloudy, 24°C, Humidity 55%, West wind 3",
    "London": "Overcast, 18°C, Humidity 70%, Light rain",
    "Paris": "Sunny, 23°C, Humidity 45%, South wind 2",
}

# 从文件加载扩展数据
if os.path.exists(_WEATHER_FILE):
    try:
        with open(_WEATHER_FILE, "r", encoding="utf-8") as f:
            extra = json.load(f)
            if isinstance(extra, dict):
                _DEFAULT_DATA.update(extra)
    except Exception:
        pass


def weather_fn(city: str) -> str:
    """查询指定城市的天气"""
    # 精确匹配
    for name, weather in _DEFAULT_DATA.items():
        if name.lower() == city.lower().strip():
            return f"{name}天气: {weather}"

    # 模糊匹配
    for name, weather in _DEFAULT_DATA.items():
        if city.strip() in name or name in city.strip():
            return f"{name}天气: {weather}"

    # 未找到时模拟生成
    temp = random.randint(15, 35)
    conditions = ["晴", "多云", "阴", "小雨", "晴"]
    condition = random.choice(conditions)
    humidity = random.randint(30, 85)
    return (
        f"{city}天气（模拟数据）: {condition}，{temp}°C，湿度 {humidity}%，"
        f"数据仅供参考，未找到精确匹配。"
    )


WeatherTool = Tool(
    name="weather",
    description="查询城市天气。支持中英文城市名",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，例如: 北京, 上海, Tokyo, London",
            }
        },
        "required": ["city"],
    },
    fn=weather_fn,
)
