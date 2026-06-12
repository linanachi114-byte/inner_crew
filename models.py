"""StepFun 模型与客户端配置。模型名集中此处 + .env，后期改这里即可。

默认全用非推理的 step-2-16k；仅 verdict 可选 flash + reasoning_effort。
勿用 -flash 系做短发言（推理会吃光 max_tokens 返空）。
"""
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

load_dotenv()  # 读项目根 .env

BASE_URL = os.getenv("STEPFUN_BASE_URL", "https://api.stepfun.com/v1")
API_KEY = os.getenv("STEPFUN_API_KEY", "")

DEFAULT_MODEL = os.getenv("STEPFUN_MODEL", "step-2-16k")
# 想给决策建议书用深推理，就在 .env 设 STEPFUN_MODEL_VERDICT=step-3.7-flash
VERDICT_MODEL = os.getenv("STEPFUN_MODEL_VERDICT", DEFAULT_MODEL)
# 计算师工具循环用推理模型（flash 在复杂提示下能可靠决定调工具；step-2-16k 不行）
LOGICIAN_TOOL_MODEL = os.getenv("STEPFUN_TOOL_MODEL", "step-3.7-flash")
# 结构化 JSON 输出（verdict 建议书 / ask 两问）用非推理模型：flash 的 response_format=json_object
# 会产出乱码键（实测 `{": ":`），step-2-16k 的 JSON 干净可靠。这俩是幕后总结器、非人格。
JSON_MODEL = os.getenv("STEPFUN_JSON_MODEL", "step-2-16k")

stepfun_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


def make_model(model_name: str) -> OpenAIChatCompletionsModel:
    """把模型名包成 Agents SDK 的 model 对象，共用同一个 StepFun 客户端。"""
    return OpenAIChatCompletionsModel(model=model_name, openai_client=stepfun_client)


def pick_model(endpoint: str) -> str:
    return VERDICT_MODEL if endpoint == "verdict" else DEFAULT_MODEL


def is_rate_limit(exc) -> bool:
    """是否 StepFun 限流（RPM=10 超了报 429 rate_limited）。"""
    s = str(exc).lower()
    return "rate_limit" in s or "429" in s or "rpm" in s


# 推理强度：flash 系吃 reasoning_effort（low/medium/high）；非推理模型（step-2-16k）忽略，无害。
REASONING_EFFORT = os.getenv("STEPFUN_REASONING", "low")


def reasoning_extra() -> dict:
    """传给 chat.completions 的 extra_body（或 ModelSettings.extra_body）。"""
    return {"reasoning_effort": REASONING_EFFORT}

