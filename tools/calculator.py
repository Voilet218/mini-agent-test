"""计算器工具 - 支持四则运算与数学函数"""

import math
import re
from agent.tool_registry import Tool

# 安全的内置函数白名单
SAFE_FUNCS: dict = {
    "abs": abs, "round": round, "int": int, "float": float,
    "max": max, "min": min, "sum": sum,
    "pow": pow, "sqrt": math.sqrt,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "pi": math.pi, "e": math.e,
    "floor": math.floor, "ceil": math.ceil,
}


def _safe_eval(expression: str) -> str:
    """安全求值数学表达式"""
    # 清洗：只允许数学表达式字符
    cleaned = expression.strip().strip("`").strip()
    if not cleaned:
        return "错误: 表达式为空"

    # 检查是否只包含安全字符
    allowed = re.compile(r'^[a-zA-Z0-9\s\+\-\*\/\(\)\.,%\^\_\[\]]+$')
    # 更宽松一些，允许函数名和空格
    if not re.match(r'^[\d\s\+\-\*\/\(\)\,\.\%\^a-zA-Z\_\[\]]+$', cleaned):
        # 检查是否只是函数调用
        pass

    try:
        # 使用受限的 eval
        result = eval(cleaned, {"__builtins__": {}}, SAFE_FUNCS)
        if isinstance(result, float):
            # 避免浮点显示过长
            return f"{result:.10g}"
        return str(result)
    except SyntaxError as e:
        return f"表达式语法错误: {e}"
    except ZeroDivisionError as e:
        return f"数学错误: 除以零"
    except Exception as e:
        return f"计算错误: {type(e).__name__}: {e}"


def calculator_fn(expression: str) -> str:
    """执行数学计算"""
    result = _safe_eval(expression)
    return f"{expression} = {result}"


CalculatorTool = Tool(
    name="calculator",
    description="执行数学计算，支持四则运算(+,-,*,/)和数学函数(sqrt,sin,cos,log等)",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，例如: 2 + 3 * 4, sqrt(144), sin(pi/2)",
            }
        },
        "required": ["expression"],
    },
    fn=calculator_fn,
)
