"""模型与客户端配置。模型名集中此处 + .env，后期改这里即可。

默认支持 DeepSeek（OpenAI 兼容端点）与 StepFun。StepFun 的 flash 系模型
需要 reasoning_effort + 更大的 token 地板；DeepSeek 的 flash 命名不走这套参数。
"""
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

load_dotenv()  # 读项目根 .env

PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "deepseek" if os.getenv("DEEPSEEK_API_KEY") else "stepfun",
).strip().lower()

if PROVIDER == "deepseek":
    BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", "")
    DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL") or os.getenv("LLM_MODEL", "deepseek-v4-flash")
    VERDICT_MODEL = os.getenv("DEEPSEEK_MODEL_VERDICT", DEFAULT_MODEL)
    LOGICIAN_TOOL_MODEL = os.getenv("DEEPSEEK_TOOL_MODEL", DEFAULT_MODEL)
    JSON_MODEL = os.getenv("DEEPSEEK_JSON_MODEL", DEFAULT_MODEL)
    DEEPSEEK_THINKING = os.getenv("DEEPSEEK_THINKING", "disabled").strip().lower()
else:
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
    DEEPSEEK_THINKING = "disabled"

stepfun_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


def make_model(model_name: str) -> OpenAIChatCompletionsModel:
    """把模型名包成 Agents SDK 的 model 对象，共用同一个 OpenAI 兼容客户端。"""
    return OpenAIChatCompletionsModel(model=model_name, openai_client=stepfun_client)


def pick_model(endpoint: str) -> str:
    return VERDICT_MODEL if endpoint == "verdict" else DEFAULT_MODEL


def is_rate_limit(exc) -> bool:
    """是否模型服务限流。"""
    s = str(exc).lower()
    return "rate_limit" in s or "429" in s or "rpm" in s


# 推理强度：flash 系吃 reasoning_effort（low/medium/high）；非推理模型（step-2-16k）忽略，无害。
REASONING_EFFORT = os.getenv("STEPFUN_REASONING", "low")


def uses_stepfun_reasoning(model_name: str | None = None) -> bool:
    """StepFun flash 才需要 reasoning_effort 与大 token 地板。"""
    return PROVIDER == "stepfun" and "flash" in (model_name or DEFAULT_MODEL)


def uses_deepseek_reasoning(model_name: str | None = None) -> bool:
    """DeepSeek V4 thinking mode 会消耗 reasoning tokens。"""
    return PROVIDER == "deepseek" and DEEPSEEK_THINKING == "enabled"


def needs_reasoning_budget(model_name: str | None = None) -> bool:
    """会消耗 reasoning tokens 的模型需要更大的 max_tokens，避免正文返空。"""
    return uses_stepfun_reasoning(model_name) or uses_deepseek_reasoning(model_name)


def reasoning_token_floor(model_name: str | None = None) -> int:
    """不同提供商的短发言 token 地板。"""
    return 2500 if uses_stepfun_reasoning(model_name) else 1000


def reasoning_extra(model_name: str | None = None) -> dict:
    """传给 chat.completions 的 extra_body（或 ModelSettings.extra_body）。"""
    if uses_stepfun_reasoning(model_name):
        return {"reasoning_effort": REASONING_EFFORT}
    if PROVIDER == "deepseek" and DEEPSEEK_THINKING in {"enabled", "disabled"}:
        return {"thinking": {"type": DEEPSEEK_THINKING}}
    return {}

