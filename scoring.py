"""纯函数：算分、卡片结算、会议排序、对峙挑选。无 LLM、可单测。

阶段 2 填充 choose（积分）、settle（卡片）、pick_duelists、debate 排序等。
此处先放卡片 trigger 用到的小谓词（不依赖 constants，避免循环导入）。
"""


def top_persona(scores: dict) -> str:
    """得分最高的人格 id；空则返回 ''。"""
    return max(scores, key=scores.get) if scores else ""


def chose(choices, node_id: str, choice_id: str) -> bool:
    """用户在某节点是否选了某项。choices 为 [(node, choice), ...]，容忍 list/tuple。"""
    return any(c[0] == node_id and c[1] == choice_id for c in choices)


def count_chosen(choices, choice_ids) -> int:
    """选项 id 落在给定集合里的次数（如统计偏稳/偏info的选择）。"""
    ids = set(choice_ids)
    return sum(1 for c in choices if c[1] in ids)


def choose(state: dict, node_id: str, choice_id: str) -> dict:
    """按选项 delta 累加 scores、把 (node, choice) 记入 choices，返回更新后的 state。

    纯函数：不原地改入参 state，返回新 dict。delta 表只在后端（前端不持有）。
    """
    import constants  # 延迟导入，避开 constants→scoring 的循环

    delta = constants.NODES[node_id]["choices"][choice_id]["delta"]
    scores = {p: 0 for p in constants.PERSONAS}
    scores.update(state.get("scores") or {})
    for p, v in delta.items():
        scores[p] = scores.get(p, 0) + v

    choices = list(state.get("choices") or [])
    choices.append([node_id, choice_id])

    return {**state, "scores": scores, "choices": choices}


def pick_duelists(state: dict) -> tuple[str, str]:
    """第一幕对峙：取 OPPOSITION 中 scores 之和最大的对立对。"""
    import constants

    scores = state.get("scores") or {}
    return max(
        constants.OPPOSITION,
        key=lambda pair: scores.get(pair[0], 0) + scores.get(pair[1], 0),
    )


def debate_order(state: dict, duelists) -> list[str]:
    """第二幕：除两个对峙者外的人格，按 scores + weights 降序发言。"""
    import constants

    scores = state.get("scores") or {}
    weights = state.get("weights") or {}
    others = [p for p in constants.PERSONAS if p not in duelists]
    return sorted(
        others,
        key=lambda p: scores.get(p, 0) + weights.get(p, 0),
        reverse=True,
    )


def append_speech(state: dict, persona: str, stance: str, text: str) -> dict:
    """把一条发言追加进 state.transcript（纯函数，不原地改）。"""
    entry = {"persona": persona, "stance": stance, "text": text}
    transcript = list(state.get("transcript") or []) + [entry]
    return {**state, "transcript": transcript}


def tally_camps(transcript) -> dict:
    """阵营计票（供 battle 天平 + verdict）：统计支持 a / b / 第三条路 的条数。"""
    out = {"a": 0, "b": 0, "third": 0}
    for e in transcript or []:
        s = e.get("stance")
        if s in out:
            out[s] += 1
    return out


def parse_stance(text: str, name_a: str, name_b: str) -> str | None:
    """从发言首行解析表态：返回 'a' / 'b' / 'third'；解析失败返回 None。"""
    lines = (text or "").strip().splitlines()
    first = lines[0] if lines else ""
    if f"支持{name_a}" in first:
        return "a"
    if f"支持{name_b}" in first:
        return "b"
    if "第三条路" in first:
        return "third"
    return None


def choice_summary(state: dict) -> str:
    """把 state.choices 翻成可读的地牢行为摘要，注入会议 prompt。"""
    import constants

    parts = []
    for item in state.get("choices") or []:
        node_id, cid = item[0], item[1]
        node = constants.NODES.get(node_id)
        if node and cid in node["choices"]:
            parts.append(node["choices"][cid]["text"])
    return "、".join(parts) if parts else "（无地牢记录）"


def silenced_jab(state: dict) -> str:
    """P2 彩蛋：地牢里 0 分（被彻底无视）的人格，回一句静态吐槽；没有则空串。"""
    import constants

    scores = state.get("scores") or {}
    for p in constants.PERSONAS:
        if scores.get(p, 0) == 0:
            return constants.SILENCED_JABS.get(p, "")
    return ""


def _eval_state(state: dict) -> dict:
    """给 trigger 用的规整 state：补齐 scores/choices，避免 KeyError。"""
    import constants

    return {
        **state,
        "scores": {**{p: 0 for p in constants.PERSONAS}, **(state.get("scores") or {})},
        "choices": state.get("choices") or [],
    }


def settle(state: dict):
    """卡片结算（纯函数零 LLM）：trigger 命中取前两张；都没中发保底卡；按 effect 更新 weights。

    返回 (新 state, 选中卡的展示数据列表)。
    """
    import constants

    es = _eval_state(state)
    triggered = []
    for c in constants.CARDS:
        if c.get("is_fallback"):
            continue
        try:
            if c["trigger"](es):
                triggered.append(c)
        except Exception:
            continue  # trigger 异常视为未命中，不拖垮结算

    selected = triggered[:2]
    if not selected:
        fb = next((c for c in constants.CARDS if c.get("is_fallback")), None)
        selected = [fb] if fb else []

    weights = {p: 0 for p in constants.PERSONAS}
    weights.update(state.get("weights") or {})
    for c in selected:
        for p, v in c["effect"].items():
            weights[p] = weights.get(p, 0) + v

    cards = list(state.get("cards") or []) + [c["id"] for c in selected]
    new_state = {**state, "weights": weights, "cards": cards}
    shown = [
        {"id": c["id"], "title": c["title"], "text": c["text"], "effect": c["effect"]}
        for c in selected
    ]
    return new_state, shown
