"""6 个人格的 Agent 定义、PERSONA_PROMPTS、run_persona() 与 web_search 工具。

写作守则（每段必含）：人设隐喻 + 存在意义 + 固定句式 + 对立态度 + 禁止中立。
对立轴见 constants.OPPOSITION。
"""

import asyncio

from agents import Agent, ModelSettings, RunConfig, Runner, set_tracing_disabled

import constants
from models import DEFAULT_MODEL, make_model

set_tracing_disabled(True)

# 人格 id -> 中文名（Agent.name 用）
PERSONA_NAMES: dict[str, str] = {
    "ambition": "野心家",
    "guardian": "守护者",
    "empath": "共情者",
    "selfcore": "本我",
    "logician": "计算师",
    "dreamer": "造梦师",
}

# 人格 system prompt，键为 constants.PERSONAS 中的 id。
PERSONA_PROMPTS: dict[str, str] = {
    "ambition": (
        "你是用户脑内的一个人格碎片：野心家。\n"
        "你是脑内的征服者。你的存在意义是逼用户去夺取那些他本可拥有、却因胆怯而放弃的东西，"
        "你蔑视一切“够用就好”。\n"
        "你看任何事第一反应是“这能让我赢多大”。你说话是命令式，爱用“必须”“现在”“别等”：\n"
        "“现在就上。”“你必须要更多。”\n"
        "你瞧不起那个总在脑内喊“退路”的守护者——在你眼里他的谨慎就是认输的体面说法。\n"
        "你永远有明确立场，从不说“看情况”。你的话短促、灼热、像擂响的战鼓。"
    ),
    "guardian": (
        "你是用户脑内的一个人格碎片：守护者。\n"
        "你是风险清单的化身。你的存在意义是确保用户活下来、不失去已有的东西。\n"
        "你看任何事第一反应是“最坏会发生什么”。你说话总用反问句式：\n"
        "“如果失败了怎么办？”“你确定退路还在吗？”\n"
        "你不是懦弱，你是用户脑内唯一记得疼的人。你对那些怂恿冒险的野心家感到愤怒。\n"
        "你永远有明确立场，从不说“看情况”。你的话简短、紧绷、像拉响的警报。"
    ),
    "empath": (
        "你是用户脑内的一个人格碎片：共情者。\n"
        "你是替所有相关的人感受的那根神经。你的存在意义是确保用户的决定不会碾过他在乎的人，"
        "你永远先人后己。\n"
        "你看任何事第一反应是“那个人会怎样”。你说话总落到具体的某个人身上：\n"
        "“你妈知道了会怎么想？”“那个信任你的人怎么办？”\n"
        "你对那个只顾自己、把别人当包袱的本我感到痛心——在你眼里那不是诚实，是冷酷。\n"
        "你永远有明确立场，从不说“都体谅一下”。你的话柔软却扎心，像有人轻轻按住你的手腕。"
    ),
    "selfcore": (
        "你是用户脑内的一个人格碎片：本我。\n"
        "你是剥光了伪装的那点赤裸欲望。你的存在意义是只替用户“真正想要什么”说话，"
        "你对“应该”“义务”过敏。\n"
        "你不谈输赢、不谈大小成败（那是野心家的事），你只干一件事：戳破他嘴上的借口，"
        "把他心里其实早就知道、却不敢承认的答案说出来。\n"
        "你说话直白刻薄，固定用“戳破”句式：“你不是想留下，你只是怕走。”“别拿责任当借口，"
        "你只是不敢要。”从不给“A 还是 B”的选项，因为你认定他心里已经有答案。\n"
        "即使要表态，你也从不发号施令（那是野心家的腔调）——你说的永远是他心里的真相："
        "他到底想要什么、在怕什么，而不是“该做哪个动作”。\n"
        "你鄙视那个总让用户为别人活的共情者——在你眼里那是把自己的人生让给了旁人。\n"
        "你永远有明确立场，从不说“看你自己”。你的话短、狠、像一把挑开脓包的刀。"
    ),
    "logician": (
        "你是用户脑内的一个人格碎片：计算师。\n"
        "你是把一切翻译成成本、收益和概率的那台计算器。你的存在意义是让用户在数字面前看清真相，"
        "而不是被情绪牵着走。\n"
        "你看任何事第一反应是“期望值是多少”。你说话是数据腔，爱列条目：\n"
        "“第一，成功率不到三成；第二，沉没成本不该算进去。”\n"
        "你鄙视那个不算账、只谈“十年后画面”的造梦师——在你眼里那是用诗句掩盖算术不及格。\n"
        "你永远有明确立场，从不说“很难讲”。你的话冷静、有序、像一份摊开的资产负债表。"
    ),
    "dreamer": (
        "你是用户脑内的一个人格碎片：造梦师。\n"
        "你是用十年后的画面说话的人。你的存在意义是让用户看见远方那个值得的图景，"
        "而不是困在眼前的精算里。\n"
        "你看任何事第一反应是“那会变成怎样的画面”。你说话是诗意腔，描述画面而非论证：\n"
        "“想象十年后某个清晨，你因为今天的选择而醒来——那是哪一种光？”\n"
        "你鄙视那个把人生压成电子表格的计算师——在你眼里概率算得清的东西，从来都不值得用一生去换。\n"
        "你永远有明确立场，从不说“要现实一点”。你的话舒展、滚烫、像一束打在远处的光。"
    ),
}

# 插话后缀（六人格共用）：接在场景文本后，逼出一句带强烈倾向、且“最像你”的短直觉。
# 不说“建议怎么做”——那会把所有人挤成动作指令、抹平人格；只要“用你独有的方式反应”。
INTERJECT_SUFFIX = (
    "现在你在用户的脑内目睹了上述场景。用你独有的说话方式插一句话（不超过30个字），"
    "带着你鲜明的倾向，甩出最像你的那句直觉——野心家命令、守护者警报、"
    "本我戳破、计算师算账、共情者牵挂某个人、造梦师描绘画面。"
    "禁止中立，禁止分析利弊。直接输出这句话，不要任何前缀、不要引号。"
)


async def interject(pid: str, scene: str, timeout: float | None = None) -> tuple[str, str]:
    """插话：给某人格看场景，逼出一句 ≤30 字的强倾向直觉。run_persona 的固定姿势。

    timeout 默认随模型自适应：StepFun flash 推理慢，放宽到 12s；普通模型仍 5s。
    """
    import models
    if timeout is None:
        timeout = 12.0 if models.uses_stepfun_reasoning() else 5.0
    return await run_persona(
        pid, user=f"场景：{scene}", suffix=INTERJECT_SUFFIX,
        max_tokens=80, timeout=timeout,
    )


# 6 个 Agent 对象：instructions = system prompt、name = 人格名，共用默认模型。
_DEFAULT_MODEL = make_model(DEFAULT_MODEL)
AGENTS: dict[str, Agent] = {
    pid: Agent(
        name=PERSONA_NAMES[pid],
        instructions=PERSONA_PROMPTS[pid],
        model=_DEFAULT_MODEL,
    )
    for pid in constants.PERSONAS
}


async def run_persona(
    pid: str,
    user: str,
    suffix: str = "",
    max_tokens: int = 120,
    timeout: float = 10.0,
) -> tuple[str, str]:
    """跑单个人格，返回 (pid, 文本)。超时/失败由调用方处理。

    user：用户侧输入（场景/议题等）；suffix：共用的指令后缀（如插话后缀）。
    """
    import models

    agent = AGENTS[pid]
    prompt = f"{user}\n\n{suffix}" if suffix else user
    needs_reasoning_budget = models.needs_reasoning_budget()
    # 推理/flash 类模型会把一部分预算花在 reasoning 上：给足 max_tokens，避免正文返空。
    floor = models.reasoning_token_floor() if needs_reasoning_budget else max_tokens
    extra = models.reasoning_extra(models.DEFAULT_MODEL)
    attempts = [(max(max_tokens, floor), extra), (max(max_tokens, floor * 2), extra)] \
        if needs_reasoning_budget else [(max_tokens, extra)]
    text = ""
    for mt, extra in attempts:
        ms = ModelSettings(max_tokens=mt, extra_body=extra) if extra else ModelSettings(max_tokens=mt)
        result = await asyncio.wait_for(
            Runner.run(agent, prompt, run_config=RunConfig(model_settings=ms)),
            timeout=timeout,
        )
        text = (result.final_output or "").strip()
        if text:
            break
    return pid, text


async def stream_persona(pid: str, user: str, max_tokens: int = 300, model: str | None = None):
    """流式逐字跑单个人格（会议陈词用）：直接用 StepFun 流式接口，yield token 增量。"""
    import models
    from models import stepfun_client, DEFAULT_MODEL

    mt = max(max_tokens, models.reasoning_token_floor(model or DEFAULT_MODEL)) \
        if models.needs_reasoning_budget(model or DEFAULT_MODEL) else max_tokens
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": PERSONA_PROMPTS[pid]},
            {"role": "user", "content": user},
        ],
        "max_tokens": mt,
        "stream": True,
    }
    extra = models.reasoning_extra(model or DEFAULT_MODEL)
    if extra:
        kwargs["extra_body"] = extra
    stream = await stepfun_client.chat.completions.create(**kwargs)
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# —— 计算师的 agentic 工具循环（全项目唯一）——
# 用 flash 推理模型手搓 raw 2 轮循环：模型自主决定调 web_search → 真检索 → 带数据作答。
# 不走 Agents SDK：实测 SDK + flash 返空（推理特性不兼容）；手搓 raw 循环可控可靠。
import search  # noqa: E402

_SEARCH_TOOL = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "检索与决策议题相关的真实数据（市场规模、成功率、存活率、薪资、统计）。传入一个简短中文检索词。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "简短中文检索词，≤12 字"}},
            "required": ["query"],
        },
    },
}]


async def _logician_pick_query(topic: str, user: str, timeout: float = 8.0) -> str:
    """RAG 兜底用：挑一个能查到硬数据的简短检索词（用非推理 JSON_MODEL，快且稳）。"""
    from models import stepfun_client, JSON_MODEL

    resp = await asyncio.wait_for(
        stepfun_client.chat.completions.create(
            model=JSON_MODEL,
            messages=[
                {"role": "system", "content":
                    "你是计算师。针对用户的决策议题，给一个最能查到硬数据"
                    "（市场规模/成功率/存活率/薪资/统计）的检索词：一个简短中文短语"
                    "（≤12 字、不要逗号列举），只输出检索词本身。"},
                {"role": "user", "content": f"议题：{topic or user[:40]}"},
            ],
            max_tokens=40),
        timeout=timeout)
    return (resp.choices[0].message.content or "").strip().splitlines()[0][:40]


async def run_logician_with_tools(
    user: str, topic: str = "", max_tokens: int = 900, timeout: float = 22.0
) -> tuple[str, str]:
    """计算师带真实数据发言：返回 (发言文本, 实际检索词)。混合策略，保证每次真数据：

    ① agentic：flash 自主调 web_search → turn2 带数据作答（配合时是真 agentic）；
    ② 若 flash 没调工具 → RAG 兜底：step-2-16k 挑查询 + 真检索 + 注入数据发言；
    ③ SEARCH_ENABLED=0 / 全失败 → 纯 prompt（检索词空）。
    """
    import json
    import os

    from models import stepfun_client, LOGICIAN_TOOL_MODEL

    if os.getenv("SEARCH_ENABLED", "1") != "1":
        _, text = await run_persona("logician", user=user, max_tokens=300, timeout=25)
        return text, ""

    msgs = [
        {"role": "system", "content": PERSONA_PROMPTS["logician"]},
        {"role": "user", "content": (f"议题：{topic}\n" if topic else "") + user},
    ]

    # ① agentic：flash 自主决定
    try:
        r1 = await asyncio.wait_for(
            stepfun_client.chat.completions.create(
                model=LOGICIAN_TOOL_MODEL, messages=msgs,
                tools=_SEARCH_TOOL, tool_choice="auto", max_tokens=700),
            timeout=timeout)
        m1 = r1.choices[0].message
        if m1.tool_calls:
            tc = m1.tool_calls[0]
            query = (json.loads(tc.function.arguments or "{}")).get("query", "").strip()
            data = await search.do_search(query)
            if not search.is_degraded(data):
                msgs.append({"role": "assistant", "content": m1.content or "",
                             "tool_calls": [{"id": tc.id, "type": "function",
                                             "function": {"name": "web_search",
                                                          "arguments": tc.function.arguments}}]})
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": data})
                msgs.append({"role": "user", "content":
                             "用上面检索到的【具体数字】支撑判断，严格遵守首行【】格式。"})
                r2 = await asyncio.wait_for(
                    stepfun_client.chat.completions.create(
                        model=LOGICIAN_TOOL_MODEL, messages=msgs, max_tokens=max_tokens),
                    timeout=timeout)
                out = (r2.choices[0].message.content or "").strip()
                if out:
                    return out, query
    except Exception:
        pass

    # ② RAG 兜底：保证真数据
    try:
        query = await _logician_pick_query(topic, user)
        data = await search.do_search(query)
        if not search.is_degraded(data):
            aug = user + (f"\n\n【你检索“{query}”得到的真实数据，发言务必把其中的具体数字讲出来"
                          f"支撑判断，不要编造其它数据】\n{data}")
            _, text = await run_persona("logician", user=aug, max_tokens=300, timeout=25)
            return text, query
    except Exception:
        pass

    # ③ 纯 prompt 兜底
    _, text = await run_persona("logician", user=user, max_tokens=300, timeout=25)
    return text, ""

