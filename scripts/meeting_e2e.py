"""阶段2步骤9：整场会议端到端（duel→debate→verdict，7 次调用）。

in-process 直接驱动端点内部生成器，验证：串联不崩、transcript 累积、verdict 五字段、计时。
"""
import asyncio
import json
import time

import main
import scoring


def _sse(chunk: str):
    return json.loads(chunk[len("data: "):].strip())


async def run():
    state = {
        "topic": "要不要离开稳定工作去创业",
        "assets": "六个月生活费、五年后端经验",
        "desire": "想证明自己不止是螺丝钉",
        "scores": {"ambition": 6, "guardian": 5, "logician": 3, "empath": 2, "dreamer": 2, "selfcore": 1},
        "weights": {},
    }
    t0 = time.perf_counter()

    # —— 第一幕 duel ——
    duelists = list(scoring.pick_duelists(state))
    statements = {}
    async for chunk in main.duel_stream(state):
        o = _sse(chunk)
        if o.get("event") == "end":
            statements[o["persona"]] = o["text"]
            state = scoring.append_speech(state, o["persona"], o["stance"], o["text"])
    t_duel = time.perf_counter()

    # —— 第二幕 debate ——
    async for chunk in main.debate_stream(state, duelists, statements):
        o = _sse(chunk)
        if o.get("done"):
            continue
        state = scoring.append_speech(state, o["persona"], o["stance"], o["text"])
    t_debate = time.perf_counter()

    # —— 第三幕 verdict ——（裁决听野心家 + 补充）
    user = main._build_verdict_user(state, duelists, "a", "先把六个月缓冲留足")
    verdict = await main._run_verdict(user)
    t1 = time.perf_counter()

    # —— 报告 ——
    tr = state["transcript"]
    print(f"对峙对: {duelists}")
    print(f"transcript 条数: {len(tr)} (应 6)  阵营: {scoring.tally_camps(tr)}")
    need = ["verdict_summary", "persona_positions", "action_steps", "risk_notes", "dissent"]
    ok = verdict is not None and all(k in verdict for k in need)
    print(f"verdict 五字段齐全: {ok}")
    if verdict:
        print(f"  方向: {verdict.get('verdict_summary')}")
        print(f"  dissent: {verdict.get('dissent')}")
    print(f"\n计时: 第一幕 {t_duel-t0:.1f}s | 第二幕 {t_debate-t_duel:.1f}s | "
          f"第三幕 {t1-t_debate:.1f}s | 总计 {t1-t0:.1f}s (红线 ≤90s)")
    assert len(tr) == 6 and ok, "整场会议结构校验失败"
    print("✓ 整场会议端到端跑通、结构完整、未崩")


if __name__ == "__main__":
    asyncio.run(run())
