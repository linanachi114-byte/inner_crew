"""Inner Crew v2 — FastAPI 入口。

阶段 1：骨架 + /api/interject（并行插话 SSE）。流程逻辑（积分/结算/排序）
后续进 scoring.py，人格调用进 personas.py，纯数据进 constants.py。前端保持薄。
"""
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import constants
import models
import personas
import scoring

app = FastAPI(title="Inner Crew v2")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/topic/random")
async def random_topic():
    return {"topic": constants.random_topic()}


class TopicCheckRequest(BaseModel):
    topic: str = ""


@app.post("/api/topic/check")
async def topic_check(req: TopicCheckRequest):
    ok, reason = constants.validate_topic(req.topic)
    return {"ok": ok, "reason": reason}


@app.get("/api/nodes")
async def nodes(topic: str = ""):
    """给前端的本轮试炼：有序题目 + 场景 + 选项文案 + 插话名单。不含 delta。"""
    order = constants.select_trial_order(topic)
    node_map = {
        nid: {
            "place": n["place"],   # 中性地点名；axis 测量轴不下发，避免剧透
            "scene": n["scene"],
            "bridge": n.get("bridge", "几个声音在你脑内争了起来——"),
            "interject": n["interject"],
            "choices": {cid: c["text"] for cid, c in n["choices"].items()},
        }
        for nid, n in constants.NODES.items()
        if nid in order
    }
    return {"order": order, "nodes": node_map}


class InterjectRequest(BaseModel):
    node_id: str
    state: dict = {}  # 前端持有的全局状态，本端点暂不使用，预留


class ChooseRequest(BaseModel):
    node_id: str
    choice_id: str
    state: dict = {}


@app.post("/api/choose")
async def choose(req: ChooseRequest):
    """地牢选择：后端按 delta 算分（积分必在后端），返回更新后的 state。"""
    node = constants.NODES.get(req.node_id)
    if node is None or req.choice_id not in node["choices"]:
        return {"error": f"unknown node/choice: {req.node_id}/{req.choice_id}"}
    new_state = scoring.choose(req.state, req.node_id, req.choice_id)
    return {"state": new_state, "chosen": node["choices"][req.choice_id]["text"]}


class DetailRequest(BaseModel):
    state: dict = {}


@app.post("/api/detail/trials")
async def detail_trials(req: DetailRequest):
    """详细记录页用：解释每次试炼选择如何影响六人格分数。"""
    running = {p: 0 for p in constants.PERSONAS}
    out = []
    for idx, item in enumerate(req.state.get("choices") or [], start=1):
        node_id = item[0] if len(item) > 0 else ""
        choice_id = item[1] if len(item) > 1 else ""
        node = constants.NODES.get(node_id)
        if not node or choice_id not in node["choices"]:
            continue
        choice = node["choices"][choice_id]
        delta = {p: int(choice.get("delta", {}).get(p, 0)) for p in constants.PERSONAS}
        for p, v in delta.items():
            running[p] += v
        out.append({
            "index": idx,
            "node_id": node_id,
            "choice_id": choice_id,
            "place": node["place"],
            "scene": node["scene"],
            "choice": choice["text"],
            "delta": delta,
            "after": dict(running),
        })
    return {
        "choices": out,
        "scores": {p: int((req.state.get("scores") or {}).get(p, 0)) for p in constants.PERSONAS},
        "weights": {p: int((req.state.get("weights") or {}).get(p, 0)) for p in constants.PERSONAS},
    }


class AskRequest(BaseModel):
    topic: str = ""
    state: dict = {}


ASK_SYS = (
    "你要生成两个会前问题，把语义骨架锁死、只改措辞：\n"
    "logician_q = 计算师问“你现实里有什么牌/资源”（资源盘点：存款、技能、人脉、时间、健康、试错的余地……等等）；\n"
    "selfcore_q = 本我问“你到底想要什么”（真实欲望，直白、戳破伪装）。\n"
    "结合用户的议题和他在试炼里的选择行为来改写问法：至少一问要点到他的具体选择"
    "（如“你一路都先观察”），让问题贴着这个人。"
    "每问 ≤40 字。只输出 JSON：{\"logician_q\":\"...\",\"selfcore_q\":\"...\"}。"
)


@app.post("/api/ask")
async def ask(req: AskRequest):
    """会前自陈两问（动态措辞 P1）：按议题+地牢行为改写，超时/坏 JSON 回退静态。

    回答由前端写入 state.assets（计算师问）/ state.desire（本我问）。
    """
    topic = req.topic or req.state.get("topic") or "（未填议题）"
    try:
        user = f"议题：{topic}\n他在试炼中的选择：{scoring.choice_summary(req.state)}"
        kwargs = {
            "model": models.JSON_MODEL,  # 非推理模型出干净 JSON（flash 的 json_object 出乱码）
            "messages": [{"role": "system", "content": ASK_SYS},
                         {"role": "user", "content": user}],
            "max_tokens": max(400, models.reasoning_token_floor(models.JSON_MODEL) + 400)
            if models.needs_reasoning_budget(models.JSON_MODEL) else 400,
            "response_format": {"type": "json_object"},
        }
        extra = models.reasoning_extra(models.JSON_MODEL)
        if extra:
            kwargs["extra_body"] = extra
        resp = await asyncio.wait_for(
            models.stepfun_client.chat.completions.create(**kwargs),
            timeout=18.0,
        )
        d = json.loads(resp.choices[0].message.content)
        if d.get("logician_q") and d.get("selfcore_q"):
            return {"logician_q": d["logician_q"], "selfcore_q": d["selfcore_q"]}
    except Exception:
        pass
    return {  # 回退静态文案
        "logician_q": constants.ASK_FALLBACK["logician_q"],
        "selfcore_q": constants.ASK_FALLBACK["selfcore_q"],
    }


class MeetingRequest(BaseModel):
    state: dict = {}


DUEL_TMPL = (
    "用户的真实议题是：{topic}\n"
    "用户的自陈——拥有的资源：{assets}；真实渴望：{desire}\n"
    "用户在试炼中的表现摘要：{summary}\n"
    "用你的性格就这个议题发言（不超过100字），给出明确建议和一个最有力的理由。"
    "可以引用用户的自陈作为论据。你知道 {opponent} 会反对你，预判并刺它一句。"
    "直接输出发言，不要前缀、不要引号。"
)


def _meeting_ctx(state: dict) -> dict:
    return {
        "topic": state.get("topic") or "（未填议题）",
        "assets": state.get("assets") or "（未填）",
        "desire": state.get("desire") or "（未填）",
        "summary": scoring.choice_summary(state),
    }


async def _stream_speech(pid: str, user: str, max_tokens: int = 320):
    """流式逐字推送某人格陈词；首 token 前失败重试一次，中途失败静默收尾。"""
    for attempt in range(2):
        got = False
        try:
            async for delta in personas.stream_persona(pid, user, max_tokens=max_tokens):
                got = True
                yield delta
            return
        except Exception as e:
            if got or attempt == 1:
                return
            await asyncio.sleep(6 if models.is_rate_limit(e) else 0.5)  # 限流多等，451/瞬时快重试


async def duel_stream(state: dict):
    a, b = scoring.pick_duelists(state)
    ctx = _meeting_ctx(state)
    # 对峙者各自锚定一个阵营：a 方 stance="a"、b 方 stance="b"
    for pid, opp, stance in ((a, b, "a"), (b, a, "b")):  # 串行，避开 RPM
        yield _sse({"persona": pid, "name": personas.PERSONA_NAMES[pid], "event": "start"})
        user = DUEL_TMPL.format(opponent=personas.PERSONA_NAMES[opp], **ctx)
        full = ""
        async for delta in _stream_speech(pid, user):
            full += delta
            yield _sse({"persona": pid, "delta": delta})
        # end 事件带完整发言 + 立场，前端据此 append_speech 进 transcript（与 debate 对齐）
        yield _sse({"persona": pid, "event": "end", "stance": stance, "text": full})
    yield _sse({"duelists": [a, b], "done": True})


@app.post("/api/meeting/duel")
async def meeting_duel(req: MeetingRequest):
    """第一幕对峙：最强对立对依次流式陈词。"""
    return StreamingResponse(
        duel_stream(req.state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


DEBATE_TMPL = (
    "刚才 {name_a} 主张：{stmt_a}\n"
    "{name_b} 主张：{stmt_b}\n"
    "用户的自陈——拥有：{assets}；渴望：{desire}\n"
    "你必须明确表态，第一行只能是这三者之一：【支持{name_a}】/【支持{name_b}】/【第三条路】。"
    "然后另起一行，用不超过80字陈述理由，可引用用户自陈，可点名呛上一位发言者。"
    "禁止和稀泥，禁止“两边都有道理”。"
)


class DebateRequest(BaseModel):
    state: dict = {}
    duelists: list[str]          # [a_pid, b_pid]
    statements: dict = {}        # {pid: 第一幕主张文本}


async def _debate_one(pid: str, user: str, name_a: str, name_b: str, topic: str = ""):
    """跑一个人格表态，解析首行立场；解析失败重试一次，再失败归第三条路。

    计算师走检索增强（run_logician_with_search，先检索再带数据发言），其余 5 人格纯 prompt。
    返回 (stance, text, query)；query 仅计算师非空（供前端标"🔍检索"）。
    """
    is_logician = pid == "logician"
    text, query = "", ""
    for _ in range(3):   # 多给一次重试:451 审查/返空是随机的,flash 重掷常能过(parse 放宽后此循环主扛 451)
        backoff = 0.3
        try:
            if is_logician:
                text, query = await personas.run_logician_with_tools(
                    user, topic, max_tokens=900, timeout=22)
            else:
                _, text = await personas.run_persona(pid, user=user, max_tokens=220, timeout=25)
        except Exception as e:
            text = ""
            backoff = 6 if models.is_rate_limit(e) else 0.3
        stance = scoring.parse_stance(text, name_a, name_b)
        if stance:
            return stance, text, query
        await asyncio.sleep(backoff)
    return "third", (text or "（未能表态）"), query  # 兜底：归第三条路


async def debate_stream(state: dict, duelists: list, statements: dict):
    a, b = duelists[0], duelists[1]
    name_a, name_b = personas.PERSONA_NAMES[a], personas.PERSONA_NAMES[b]
    ctx = _meeting_ctx(state)
    user = DEBATE_TMPL.format(
        name_a=name_a, name_b=name_b,
        stmt_a=statements.get(a, "（见上）"), stmt_b=statements.get(b, "（见上）"),
        assets=ctx["assets"], desire=ctx["desire"],
    )
    for pid in scoring.debate_order(state, duelists):  # 串行，避开 RPM
        stance, text, query = await _debate_one(pid, user, name_a, name_b, topic=ctx["topic"])
        ev = {"persona": pid, "name": personas.PERSONA_NAMES[pid], "stance": stance, "text": text}
        if query:
            ev["query"] = query  # 计算师真实检索词，前端标"🔍检索"
        yield _sse(ev)
    yield _sse({"done": True})


@app.post("/api/meeting/debate")
async def meeting_debate(req: DebateRequest):
    """第二幕选边：其余 4 人格按 scores+weights 依次表态，首行硬格式。"""
    return StreamingResponse(
        debate_stream(req.state, req.duelists, req.statements),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


ROUND_TASKS = {
    2: {
        "phase": "blind_spot",
        "label": "盲点交锋",
        "instruction": (
            "这是第二轮。不要复述自己上一轮观点。你必须点名回应上一轮某个声音，"
            "指出它漏看了什么、误判了什么，或它把用户推向了什么风险。"
            "第一行仍只能是三者之一：【支持{name_a}】/【支持{name_b}】/【第三条路】。"
            "第二行不超过90字。"
        ),
    },
    3: {
        "phase": "bottom_line",
        "label": "底线交换",
        "instruction": (
            "这是最后一轮。不要复述前两轮观点。你要给出你的底线："
            "如果用户不听你，最可能付出的代价是什么；如果听你，你最低能接受什么妥协条件。"
            "第一行仍只能是三者之一：【支持{name_a}】/【支持{name_b}】/【第三条路】。"
            "第二行不超过90字。"
        ),
    },
}


class RoundRequest(BaseModel):
    state: dict = {}
    duelists: list[str]
    round: int = 2


def _transcript_lines(state: dict, duelists: list) -> str:
    name_a = personas.PERSONA_NAMES.get(duelists[0], duelists[0]) if duelists else "甲方"
    name_b = personas.PERSONA_NAMES.get(duelists[1], duelists[1]) if len(duelists) > 1 else "乙方"
    lines = []
    phase_name = {
        "duel": "对峙",
        "stance": "立场",
        "blind_spot": "盲点",
        "bottom_line": "底线",
    }
    for e in state.get("transcript") or []:
        nm = personas.PERSONA_NAMES.get(e.get("persona"), e.get("persona"))
        label = _STANCE_LABEL.get(e.get("stance"), "").format(a=name_a, b=name_b)
        r = e.get("round", 1)
        ph = phase_name.get(e.get("phase"), e.get("phase") or "发言")
        lines.append(f"第{r}轮·{ph}｜{nm}（{label}）：{e.get('text', '')}")
    return "\n".join(lines) if lines else "（无记录）"


def _persona_history(state: dict, pid: str) -> list[str]:
    return [
        e.get("text", "")
        for e in state.get("transcript") or []
        if e.get("persona") == pid and e.get("text")
    ]


def _too_similar(text: str, history: list[str]) -> bool:
    import difflib

    cleaned = (text or "").strip()
    if not cleaned:
        return False
    return any(difflib.SequenceMatcher(None, cleaned, old).ratio() > 0.62 for old in history)


def _round_prompt(state: dict, duelists: list, round_no: int, pid: str, retry: bool = False) -> str:
    a, b = duelists[0], duelists[1]
    name_a, name_b = personas.PERSONA_NAMES[a], personas.PERSONA_NAMES[b]
    ctx = _meeting_ctx(state)
    task = ROUND_TASKS.get(round_no, ROUND_TASKS[2])
    own_history = "\n".join(f"- {t}" for t in _persona_history(state, pid)) or "（你还没有旧发言）"
    retry_line = (
        "\n上一次太像旧观点了。这次必须换一个具体角度、回应另一条发言、不要使用同样的句子。"
        if retry else ""
    )
    return (
        f"用户的真实议题是：{ctx['topic']}\n"
        f"用户的自陈——拥有：{ctx['assets']}；渴望：{ctx['desire']}\n"
        f"用户在试炼中的表现摘要：{ctx['summary']}\n"
        f"会议至今的全部记录：\n{_transcript_lines(state, duelists)}\n\n"
        f"你自己之前说过：\n{own_history}\n\n"
        f"{task['instruction'].format(name_a=name_a, name_b=name_b)}"
        "禁止重复自己之前的话，禁止重新做人格自我介绍，禁止和稀泥。"
        f"{retry_line}"
    )


async def _round_one(pid: str, state: dict, duelists: list, round_no: int):
    task = ROUND_TASKS.get(round_no, ROUND_TASKS[2])
    name_a = personas.PERSONA_NAMES[duelists[0]]
    name_b = personas.PERSONA_NAMES[duelists[1]]
    history = _persona_history(state, pid)
    text, query, stance = "", "", None
    for attempt in range(2):
        user = _round_prompt(state, duelists, round_no, pid, retry=attempt > 0)
        stance, text, query = await _debate_one(pid, user, name_a, name_b, topic=_meeting_ctx(state)["topic"])
        if not _too_similar(text, history):
            break
    return {
        "persona": pid,
        "name": personas.PERSONA_NAMES[pid],
        "stance": stance or "third",
        "text": text or "（这个声音短暂沉默了。）",
        "query": query,
        "round": round_no,
        "phase": task["phase"],
    }


async def round_stream(state: dict, duelists: list, round_no: int):
    order = list(duelists) + scoring.debate_order(state, duelists)
    task = ROUND_TASKS.get(round_no, ROUND_TASKS[2])
    for pid in order:
        ev = await _round_one(pid, state, duelists, round_no)
        if not ev.get("query"):
            ev.pop("query", None)
        yield _sse(ev)
    yield _sse({"done": True, "round": round_no, "phase": task["phase"]})


@app.post("/api/meeting/round")
async def meeting_round(req: RoundRequest):
    """第二/三轮追问：盲点交锋、底线交换。每轮仍让六个人格逐个切入发言。"""
    round_no = max(2, min(3, req.round))
    return StreamingResponse(
        round_stream(req.state, req.duelists, round_no),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


VERDICT_SYS = (
    "你是这场内心会议的书记。用户已经做出最终裁决。"
    "你的任务：把用户的裁决展开成一份结构化、可执行的决策建议书，并附风险与落败方的保留意见。"
    "【铁律】用户的裁决是最终决定——禁止重新论证该不该这样选、禁止夹带你自己的重新权衡，"
    "你只负责把它落地，不负责推翻它。只输出 JSON。"
)

VERDICT_USER_TMPL = (
    "议题：{topic}\n"
    "用户自陈——拥有：{assets}；渴望：{desire}\n"
    "会议记录：\n{transcript}\n"
    "用户的最终裁决：{decision}\n\n"
    "写建议书时：严格依据会议记录和用户裁决；不要重开辩论，不要把未被选择的一侧写成最终建议，"
    "但要在 risk_notes/dissent 中保留它有价值的提醒。\n"
    "输出 JSON，字段：\n"
    "verdict_summary（字符串，以用户裁决为基调的方向总结）、\n"
    "persona_positions（数组，每项 {{\"persona\":人格名,\"stance\":立场,\"key_point\":立场说明}}；"
    "key_point 必须比普通摘要更丰满，写 2 句左右，说明它支持什么、为什么支持，或它真正担心什么；每项约 45-90 字）、\n"
    "action_steps（字符串数组，围绕裁决/补充拆出的可执行步骤）、\n"
    "risk_notes（字符串，守护者视角的风险提示）、\n"
    "dissent（字符串，落败一方人格的一句保留意见）。"
)

_STANCE_LABEL = {"a": "支持{a}", "b": "支持{b}", "third": "第三条路"}


def _build_verdict_user(state: dict, duelists: list, verdict: str, note: str) -> str:
    ctx = _meeting_ctx(state)
    name_a = personas.PERSONA_NAMES.get(duelists[0], duelists[0]) if duelists else "甲方"
    name_b = personas.PERSONA_NAMES.get(duelists[1], duelists[1]) if duelists else "乙方"

    transcript_text = _transcript_lines(state, duelists)

    if verdict == "a":
        decision = f"听从{name_a}的主张"
    elif verdict == "b":
        decision = f"听从{name_b}的主张"
    else:
        decision = "综合各方，自己拿主意"
    if note:
        decision += f"，并补充：{note}"

    return VERDICT_USER_TMPL.format(
        topic=ctx["topic"], assets=ctx["assets"], desire=ctx["desire"],
        transcript=transcript_text, decision=decision,
    )


async def _run_verdict(user: str, tries: int = 2):
    for _ in range(tries):
        try:
            kwargs = {
                "model": models.JSON_MODEL,  # 非推理模型出干净 JSON（flash 的 json_object 出乱码）
                "messages": [{"role": "system", "content": VERDICT_SYS},
                             {"role": "user", "content": user}],
                "max_tokens": max(1900, models.reasoning_token_floor(models.JSON_MODEL) + 1900)
                if models.needs_reasoning_budget(models.JSON_MODEL) else 1900,
                "response_format": {"type": "json_object"},
            }
            extra = models.reasoning_extra(models.JSON_MODEL)
            if extra:
                kwargs["extra_body"] = extra
            resp = await models.stepfun_client.chat.completions.create(
                **kwargs,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            await asyncio.sleep(6 if models.is_rate_limit(e) else 0.5)
    return None


class VerdictRequest(BaseModel):
    state: dict = {}
    duelists: list[str] = []
    verdict: str = "synthesis"   # "a" | "b" | "synthesis"
    note: str = ""               # 用户可选补充


@app.post("/api/meeting/verdict")
async def meeting_verdict(req: VerdictRequest):
    """第三幕裁决：把用户裁决展开为结构化建议书（JSON 五字段），不重新论证。"""
    user = _build_verdict_user(req.state, req.duelists, req.verdict, req.note)
    result = await _run_verdict(user)
    if result is None:
        return {"error": "verdict generation failed",
                "verdict_summary": "（生成失败，请重试）",
                "persona_positions": [], "action_steps": [],
                "risk_notes": "", "dissent": ""}
    return result


class SettleRequest(BaseModel):
    state: dict = {}


@app.post("/api/settle")
async def settle(req: SettleRequest):
    """卡片结算（纯函数零 LLM）：命中取多张、没中发保底，按 effect 更新 weights。"""
    new_state, cards = scoring.settle(req.state)
    return {"state": new_state, "cards": cards, "jab": scoring.silenced_jab(new_state)}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def interject_stream(node: dict):
    """并行发起本节点 2-3 个人格插话，谁先完成谁先推送（乱序更像脑内吵架）。"""
    scene = node["scene"]
    tasks = {
        pid: asyncio.create_task(personas.interject(pid, scene))
        for pid in node["interject"]
    }
    for coro in asyncio.as_completed(tasks.values()):
        try:
            pid, text = await coro
        except Exception:
            continue  # 单条失败（超时/审查误杀）静默跳过，不拖垮整场
        yield _sse({"persona": pid, "name": personas.PERSONA_NAMES[pid], "text": text})
    yield _sse({"done": True})


@app.post("/api/interject")
async def interject(req: InterjectRequest):
    node = constants.NODES.get(req.node_id)
    if node is None:
        return {"error": f"unknown node_id: {req.node_id}"}
    return StreamingResponse(
        interject_stream(node),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# BGM 等音频资源（须在 "/" 兜底挂载之前注册，否则被 catch-all 吃掉）
app.mount("/music", StaticFiles(directory="music"), name="music")
# 人格卡牌插画（会前阵容预演用，同样须在兜底挂载之前注册）
app.mount("/card", StaticFiles(directory="card"), name="card")
# 封面海报（项目首页用，同样须在兜底挂载之前注册）
app.mount("/cover", StaticFiles(directory="cover"), name="cover")
# 静态前端托管在最后挂载（兜底路由），避免吃掉上面的 /api 路由
app.mount("/", StaticFiles(directory="static", html=True), name="static")
