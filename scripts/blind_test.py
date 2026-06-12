"""步骤 6 人格盲测：六人格同场景出话 → 匿名打乱 → 独立判官模型对号 → 算准确率。

判官只拿到「人格名 + 一句话人设」，不给完整 system prompt，避免靠原文照抄作弊。
"""
import asyncio
import json

import constants
import personas
from models import stepfun_client, DEFAULT_MODEL

# 判官能看到的线索：仅一句话人设（取自总计划人格表）
PERSONA_HINTS = {
    "ambition": "野心家：脑内的征服者，命令式，蔑视“够用就好”",
    "guardian": "守护者：风险清单的化身，总在反问“如果……怎么办”",
    "empath": "共情者：替相关的人感受，先人后己，总提到具体的某个人",
    "selfcore": "本我：只关心“你真正想要什么”，直白刻薄，对义务过敏",
    "logician": "计算师：把一切翻译成成本收益和概率，数据腔，爱列条目",
    "dreamer": "造梦师：用十年后的画面说话，诗意腔，描述画面而非论证",
}

SCENES = [
    "要不要离开稳定的国企，去一家没把握的创业公司。",
    "拿到一笔意外的钱，是还房贷求安心，还是投进一个看好的项目。",
]


async def run_with_retry(pid, user, tries=4):
    for _ in range(tries):
        try:
            _, text = await personas.run_persona(
                pid, user=f"议题：{user}",
                suffix="用你的性格就这件事说一句话（不超过40字），给出明确建议。",
                max_tokens=200, timeout=20)
            if text:
                return text
        except Exception:
            await asyncio.sleep(0.3)
    return "(生成失败)"


async def judge(samples):
    """samples: [(idx, text)]，返回 {idx: persona_id}。判官独立模型一次性对号。"""
    hint_lines = "\n".join(f"- {pid}：{h}" for pid, h in PERSONA_HINTS.items())
    quote_lines = "\n".join(f"[{i}] {t}" for i, t in samples)
    sys = (
        "下面是用户脑内六个人格，每个一句话人设：\n" + hint_lines +
        "\n\n现在给你若干条匿名发言，每条恰好出自其中一个人格。"
        "请把每条发言对应到唯一的人格 id。只输出 JSON："
        '{"assign": {"0": "ambition", "1": "...", ...}}，不要其它内容。'
    )
    resp = await stepfun_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": sys},
                  {"role": "user", "content": quote_lines}],
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)["assign"]


async def main():
    truth = []      # [(persona_id, text)]
    for scene in SCENES:
        outs = await asyncio.gather(*(run_with_retry(pid, scene) for pid in constants.PERSONAS))
        for pid, text in zip(constants.PERSONAS, outs):
            truth.append((pid, text))

    # 固定洗牌（无随机依赖）：按文本哈希排序打乱标签顺序
    order = sorted(range(len(truth)), key=lambda i: hash(truth[i][1]))
    samples = [(new_i, truth[old_i][1]) for new_i, old_i in enumerate(order)]
    gold = {str(new_i): truth[old_i][0] for new_i, old_i in enumerate(order)}

    assign = await judge(samples)

    correct = 0
    print(f"{'判官猜':<10}{'真相':<10}{'对?':<5}发言")
    for i_str in sorted(gold, key=int):
        guess = assign.get(i_str, "?")
        real = gold[i_str]
        ok = guess == real
        correct += ok
        text = dict((str(i), t) for i, t in samples)[i_str]
        gn = personas.PERSONA_NAMES.get(guess, guess)
        rn = personas.PERSONA_NAMES.get(real, real)
        print(f"{gn:<11}{rn:<11}{'✓' if ok else '✗':<5}{text}")
    n = len(gold)
    print(f"\n准确率：{correct}/{n} = {correct/n*100:.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
