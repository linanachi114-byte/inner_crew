"""复现"未能表态":跑真实 debate 调用,抓原始输出 + 首行 + parse_stance 结果。
跑: PYTHONPATH=. .venv/bin/python scripts/debug_stance.py
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
import personas, scoring  # noqa: E402

NAME_A, NAME_B = "野心家", "守护者"
DEBATE_TMPL = (
    "刚才 {a} 主张：{sa}\n{b} 主张：{sb}\n"
    "用户的自陈——拥有：{assets}；渴望：{desire}\n"
    "你必须明确表态，第一行只能是这三者之一：【支持{a}】/【支持{b}】/【第三条路】。"
    "然后另起一行，用不超过80字陈述理由，可引用用户自陈，可点名呛上一位发言者。"
    "禁止和稀泥，禁止“两边都有道理”。"
)
USER = DEBATE_TMPL.format(
    a=NAME_A, b=NAME_B,
    sa="机会不等人，现在不冲就晚了。", sb="先把退路铺好，别拿命去赌。",
    assets="一些积蓄和后端技术", desire="想做出自己的产品",
)


async def probe(pid):
    try:
        _, text = await personas.run_persona(pid, user=USER, max_tokens=220, timeout=25)
        exc = None
    except Exception as e:
        text, exc = "", f"{type(e).__name__}: {e}"
    stripped = (text or "").strip()
    first = stripped.splitlines()[0] if stripped else "(空内容)"
    st = scoring.parse_stance(text, NAME_A, NAME_B)
    print(f"\n===== {pid}  →  parse_stance = {st}  {'❌未能表态' if st is None else '✓'}")
    if exc:
        print("  异常:", exc)
    print("  首行:", repr(first))
    print("  全文:", repr(stripped[:500]))


async def main():
    print("### 真实 debate 调用复现 ###")
    for pid in ["empath", "selfcore", "dreamer", "guardian"]:
        await probe(pid)
        await asyncio.sleep(7)  # RPM=10,留间隔

    print("\n### parse_stance 对常见格式变体的鲁棒性 ###")
    cases = [
        "【支持野心家】\n机会难得。",          # 标准
        "支持野心家\n理由……",                 # 无括号
        "支持 野心家\n理由……",                # 支持与名字间有空格
        "我选择支持野心家阵营。\n因为……",      # 内联
        "理由是机会难得。\n【支持野心家】",      # 表态在第二行
        "**【支持野心家】**\n理由……",          # markdown 包裹
        "支持的是野心家。\n……",               # "支持的是X"
        "野心家说得对，我站他。\n……",          # 不含"支持X"字样
    ]
    for c in cases:
        print(f"  parse={scoring.parse_stance(c, NAME_A, NAME_B)!s:<6} <- {c.splitlines()[0]!r}")


asyncio.run(main())
