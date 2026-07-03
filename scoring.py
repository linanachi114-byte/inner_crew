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
    """解析表态：返回 'a' / 'b' / 'third'；解析失败返回 None。

    放宽以扛 flash 格式漂移：扫前 3 行（表态偶尔落第二行）、去空白/括号/星号、
    容"支持(的是)名字"。仅看头部避免正文里的提及误判。
    """
    import re

    raw = (text or "").strip()
    if not raw:
        return None
    head = "\n".join(raw.splitlines()[:3])
    head = re.sub(r"[\s【】\[\]「」（）()*_·\-—\"'`]+", "", head)  # 去包裹符与空白
    if re.search(rf"支持(?:的是)?{re.escape(name_a)}", head):
        return "a"
    if re.search(rf"支持(?:的是)?{re.escape(name_b)}", head):
        return "b"
    if "第三条路" in head:
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
    """卡片结算（纯函数零 LLM）：trigger 命中取多张；都没中发保底卡；按 effect 更新 weights。

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

    selected = triggered[:4]
    if len(selected) < 4:
        selected_ids = {c["id"] for c in selected}
        generic_by_persona = {
            "ambition": "generic_ambition",
            "guardian": "generic_guardian",
            "empath": "generic_empath",
            "selfcore": "generic_selfcore",
            "logician": "generic_logician",
            "dreamer": "generic_dreamer",
        }
        ranked = sorted(
            constants.PERSONAS,
            key=lambda p: es["scores"].get(p, 0) + (state.get("weights") or {}).get(p, 0),
            reverse=True,
        )
        for pid in ranked:
            cid = generic_by_persona.get(pid)
            card = next((c for c in constants.CARDS if c["id"] == cid), None)
            if card and cid not in selected_ids:
                selected.append(card)
                selected_ids.add(cid)
            if len(selected) >= 4:
                break

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
        {
            "id": c["id"],
            "title": c["title"],
            "text": c["text"],
            "effect": c["effect"],
            "reason": _card_reason(c, es),
        }
        for c in selected
    ]
    return new_state, shown


def _card_reason(card: dict, state: dict) -> str:
    """给掉落卡片找一条可解释的试炼依据。"""
    import constants

    choices = state.get("choices") or []
    if not choices:
        return "获取理由：这张卡来自你整段试炼里反复出现的倾向。"

    id_to_hint = {
        "act_first": ("node1", "A"),
        "perfectionism": ("node1", "B"),
        "others_first": ("node2", "A"),
        "naked_want": ("node2", "B"),
        "the_ledger": ("node2", "C"),
        "chasing_light": ("node3", "A"),
        "all_in": ("node3", "C"),
        "the_hesitant": ("node3", "B"),
    }

    target = id_to_hint.get(card.get("id"))
    if target and any(c[0] == target[0] and c[1] == target[1] for c in choices):
        node_id, cid = target
    else:
        effect_people = set((card.get("effect") or {}).keys())
        top = top_persona(state.get("scores") or {})
        node_id, cid = choices[-1][0], choices[-1][1]
        best = None
        for item in choices:
            n_id, c_id = item[0], item[1]
            node = constants.NODES.get(n_id)
            if not node or c_id not in node["choices"]:
                continue
            delta = node["choices"][c_id].get("delta") or {}
            score = sum(abs(delta.get(p, 0)) for p in effect_people)
            if top in delta:
                score += 2
            if best is None or score > best[0]:
                best = (score, n_id, c_id)
        if best:
            _, node_id, cid = best

    node = constants.NODES.get(node_id)
    if not node or cid not in node["choices"]:
        return "获取理由：这张卡来自你整段试炼里反复出现的倾向。"
    return f"获取理由：你在「{node['place']}」的情况下选择了「{node['choices'][cid]['text']}」。"
