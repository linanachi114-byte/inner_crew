"""轻量盲测：1 场景 × 6 人格 + 1 判官 = 7 次调用，串行 + 429 退避，避开 RPM=10。"""
import asyncio
import json

import constants
import personas
from models import stepfun_client, DEFAULT_MODEL

# 判官能看到的线索：仅一句话人设（不给完整 prompt，避免照抄作弊）
PERSONA_HINTS = {
    "ambition": "野心家：脑内的征服者，命令式，蔑视“够用就好”",
    "guardian": "守护者：风险清单的化身，总在反问“如果……怎么办”",
    "empath": "共情者：替相关的人感受，先人后己，总提到具体的某个人",
    "selfcore": "本我：只关心“你真正想要什么”，直白刻薄，对义务过敏",
    "logician": "计算师：把一切翻译成成本收益和概率，数据腔，爱列条目",
    "dreamer": "造梦师：用十年后的画面说话，诗意腔，描述画面而非论证",
}

SCENE = "前方岔路：左边是走过无数次的旧路，右边是从未踏足、传闻凶险的新道。"


async def with_backoff(coro_factory, tries=4):
    for i in range(tries):
        try:
            return await coro_factory()
        except Exception as e:
            if "rate_limited" in str(e) or "429" in str(e):
                await asyncio.sleep(62)
            else:
                await asyncio.sleep(1)
    return None


async def judge(samples):
    hint_lines = "\n".join(f"- {pid}：{h}" for pid, h in PERSONA_HINTS.items())
    quote_lines = "\n".join(f"[{i}] {t}" for i, t in samples)
    sys = (
        "下面是用户脑内六个人格，每个一句话人设：\n" + hint_lines +
        "\n\n现在给你若干条匿名发言，每条恰好出自其中一个人格。"
        '把每条对应到唯一的人格 id。只输出 JSON：{"assign": {"0": "ambition", ...}}。'
    )
    resp = await stepfun_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": sys},
                  {"role": "user", "content": quote_lines}],
        max_tokens=400, response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)["assign"]


async def main():
    truth = []
    for pid in constants.PERSONAS:  # 串行，避开 RPM
        _, text = await with_backoff(
            lambda pid=pid: personas.run_persona(
                pid, user=f"议题：{SCENE}",
                suffix="用你的性格就这件事说一句话（不超过40字），给出明确建议。",
                max_tokens=200, timeout=20))
        truth.append((pid, text))

    order = sorted(range(len(truth)), key=lambda i: hash(truth[i][1]))
    samples = [(ni, truth[oi][1]) for ni, oi in enumerate(order)]
    gold = {str(ni): truth[oi][0] for ni, oi in enumerate(order)}

    assign = await with_backoff(lambda: judge(samples))

    correct = 0
    for i in sorted(gold, key=int):
        g, r = assign.get(i, "?"), gold[i]
        ok = g == r
        correct += ok
        txt = dict((str(j), t) for j, t in samples)[i]
        print(f"  {'✓' if ok else '✗'} 判[{personas.PERSONA_NAMES.get(g,g)}] 真[{personas.PERSONA_NAMES.get(r,r)}]  {txt}")
    n = len(gold)
    print(f"\n准确率：{correct}/{n} = {correct/n*100:.0f}%")


asyncio.run(main())
