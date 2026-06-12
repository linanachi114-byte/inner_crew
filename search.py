"""计算师的检索：Tavily 搜索（检索增强 RAG，非 agentic 工具循环）。

为什么不用 Agents SDK 的工具循环：实测 step-2-16k 在复杂提示下不认 tool_choice、
宁可编数据也不调工具（连原始 API 的 tool_choice=required 都被忽略）。所以改为
确定性地"先检索、把真实数据注入 prompt 再发言"，保证真数据、可靠、可彩排。

降级铁律：SEARCH_ENABLED=0 / 无 key / 超时 / 异常 → 返回降级串，绝不抛。
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TAVILY_URL = "https://api.tavily.com/search"
SEARCH_TIMEOUT = 6.0  # 秒；计入会议 90s 预算，超时即降级


def _enabled() -> bool:
    return os.getenv("SEARCH_ENABLED", "1") == "1" and bool(os.getenv("TAVILY_API_KEY"))


async def do_search(query: str, timeout: float = SEARCH_TIMEOUT) -> str:
    """实际检索逻辑（可单测）：返回要点文本；任何问题都返回降级串。"""
    if not _enabled():
        return "（检索已关闭或未配置 key，无数据）"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(TAVILY_URL, json={
                "api_key": os.getenv("TAVILY_API_KEY", ""),
                "query": query, "max_results": 3, "include_answer": True,
            })
            r.raise_for_status()
            d = r.json()
    except Exception:
        return "（检索失败或超时，无数据）"

    parts = []
    if d.get("answer"):
        parts.append("数据摘要：" + d["answer"])
    for it in (d.get("results") or [])[:3]:
        parts.append(f"- {it.get('title', '')}：{(it.get('content') or '')[:160]}")
    return "\n".join(parts) if parts else "（无检索结果）"


def is_degraded(data: str) -> bool:
    """检索结果是否为降级串（无有效数据）。"""
    return (not data) or any(x in data for x in ("无数据", "检索失败", "检索已关闭", "无检索结果"))
