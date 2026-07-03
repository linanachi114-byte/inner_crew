"""纯数据：人格清单、对立轴、试炼题库、想法卡片。无 LLM。"""

import random

from scoring import chose, top_persona  # 卡片 trigger 用到的纯谓词

PERSONAS = ["ambition", "guardian", "empath", "selfcore", "logician", "dreamer"]

OPPOSITION = [("ambition", "guardian"), ("empath", "selfcore"), ("logician", "dreamer")]

TOPIC_SUGGESTIONS = [
    "要不要裸辞，去做自己一直想做的事",
    "该不该离开稳定工作，加入一家早期创业公司",
    "要不要读研，还是先进入职场积累经验",
    "该不该接受外地 offer，离开现在熟悉的生活",
    "是结束这段关系，还是认真修复一次",
    "该不该把存款投入一个高风险但很想做的项目",
    "要不要换到收入更高但压力更大的岗位",
    "该不该为了家人的期待留在本地，还是去远方发展",
    "要不要把副业变成主业，还是继续稳住现在的工作",
    "该不该和朋友合伙创业，还是保持关系简单",
    "要不要为了喜欢的城市降低收入预期",
    "该不该继续坚持这个方向，还是及时止损换赛道",
    "是留在熟悉的行业深耕，还是转去一个全新的方向",
    "要不要接受一份更稳定但不太喜欢的工作",
    "该不该为了更高收入牺牲一部分个人时间",
    "是继续租房保持自由，还是开始认真考虑买房",
    "要不要搬去另一个城市，重新开始自己的生活节奏",
    "该不该主动争取升职，还是维持现在的平衡",
    "是继续等待更好的机会，还是先接住眼前这个选择",
    "要不要把一段暧昧关系说清楚",
    "该不该向家人坦白自己的真实计划",
    "是继续独立完成项目，还是找人合作分担风险",
    "要不要离开让自己消耗很大的团队",
    "该不该把兴趣投入到专业训练里",
    "是接受对方的道歉，还是给自己一个明确的边界",
    "要不要为了长期目标暂时降低生活质量",
    "该不该把钱花在一次重要旅行上",
    "是继续备考一年，还是先去工作积累经验",
    "要不要放弃一个看起来体面但让你麻木的机会",
    "该不该把真实想法告诉上司",
    "是继续照顾所有人的期待，还是优先照顾自己的状态",
    "要不要在还没有完全准备好时先开始行动",
    "该不该退出一个已经投入很多成本的计划",
    "是选择更安全的方案，还是选择更让自己兴奋的方案",
    "要不要和过去的朋友重新建立联系",
    "该不该为了伴侣改变原本的人生安排",
    "是继续修补家庭关系，还是先保持距离保护自己",
    "要不要公开自己的作品，接受真实反馈",
    "该不该从大公司离开，去更小但更有主动权的团队",
    "是接受现实中的妥协，还是再为理想争取一次",
    "要不要把现在的计划推迟，先处理身体和情绪状态",
    "该不该对一个重要承诺说不",
]


def random_topic() -> str:
    return random.SystemRandom().choice(TOPIC_SUGGESTIONS)


def validate_topic(topic: str) -> tuple[bool, str]:
    """判断用户议题是否适合开会：最好是 A/B 类型的真实决策。"""
    t = (topic or "").strip()
    if len(t) < 6:
        return False, "这个议题太短了。试着写成“要不要…… / 该不该…… / A 还是 B”。"
    if len(t) > 120:
        return False, "这个议题有点太长了。先压成一句核心选择：你到底在两个什么方向之间摇摆？"

    decision_markers = [
        "要不要", "该不该", "是否", "能不能", "应不应该", "值不值得",
        "还是", "或者", "不如", "继续", "放弃", "接受", "拒绝",
        "离开", "留下", "辞", "换", "分手", "结婚", "读研", "创业", "offer",
    ]
    question_markers = ["怎么", "如何", "为什么", "是什么", "有哪些", "多少", "哪里", "谁"]

    has_decision = any(x in t for x in decision_markers)
    looks_like_info_question = any(x in t for x in question_markers) and not has_decision
    if looks_like_info_question:
        return False, "这更像是在问信息，不像一个需要你拍板的选择。试着改成“我要不要……”。"
    if not has_decision:
        return False, "这还不像 A/B 型选择。试着写成“要不要做 X，还是继续 Y”。"
    return True, ""

TRIAL_STAGE_SEQUENCE = ["open", "relation", "vision", "pressure", "close"]


def select_trial_order(topic: str = "", count: int = 5) -> list[str]:
    """从题库按叙事阶段抽一组试炼题；保持顺序感，但每次不固定。"""
    rng = random.SystemRandom()
    picked = []
    used_axes = set()
    for stage in TRIAL_STAGE_SEQUENCE[:count]:
        candidates = [
            nid for nid, node in NODES.items()
            if node.get("stage") == stage and nid not in picked
        ]
        fresh_axis = [nid for nid in candidates if NODES[nid].get("axis") not in used_axes]
        pool = fresh_axis or candidates
        if not pool:
            continue
        nid = rng.choice(pool)
        picked.append(nid)
        used_axes.add(NODES[nid].get("axis"))

    if len(picked) < count:
        rest = [nid for nid in NODES if nid not in picked]
        rng.shuffle(rest)
        picked.extend(rest[:count - len(picked)])
    return picked

# P2 失败彩蛋：某人格在地牢里 0 分（被彻底无视）时的一句静态吐槽。
SILENCED_JABS = {
    "ambition": "野心家全程没抢到一句话——你心里那点野，是真没了，还是被你摁死了？",
    "guardian": "守护者一次都没拦住你。要么你天生命硬，要么你根本没在听警报。",
    "empath": "共情者整场失声——这局里，没有“别人”这回事吗？",
    "selfcore": "本我一声没吭。你做的每个选择，到底有几个是你自己想要的？",
    "logician": "计算师没插上嘴——你这一路，是凭着不算账的勇气走下来的。",
    "dreamer": "造梦师没出现过。眼前的路你看得很清，可远方呢，你还看得见吗？",
}

# 会前自陈的静态问法（P0.5）：计算师问"你有什么牌"、本我问"你想要什么"。
# 语义骨架锁死、措辞固定；阶段 3 的动态措辞失败/超时也回退到这里，零风险。
ASK_FALLBACK = {
    "logician_q": "先盘点一下——你手里到底有什么牌？存款、技能、人脉、时间、"
                  "健康、试错的余地……等等，现实里你具备的筹码有哪些？",
    "selfcore_q": "抛开“该不该”——你到底想要什么？别管别人怎么看。",
}

# NODES（三节点矩阵）：架空冒险情境、不影射现实、每选项无标准答案、delta 总分约 3-4。
# 三节点张力轴：node1 冒进vs谨慎 / node2 自我vs他人 / node3 现实vs理想。
# 每节点：scene 场景文本；interject 登台插话的人格（2-3 个，挑与本轴相关的）；
#         choices 选项与 delta（delta 对全部六人格开放，每节点都在为六人悄悄积分）。
# 注：覆盖性(每人≥6-9)与 27 路径多样性的【配平校验】是阶段 2 的步骤，此处为候选草稿。
NODES: dict = {
    # —— node1 · 冒进 vs 谨慎 ——（轴：野心家 / 守护者）
    "node1": {
        "axis": "冒进 vs 谨慎",   # 内部元数据，不下发前端（避免剧透测量轴）
        "stage": "open",
        "place": "废墟深处 · 将闭的石门",
        "bridge": "你刚踏进这道门，就听到了几个声音——",
        "scene": "废墟深处有一扇正在缓缓关闭的石门，门后透出微光，"
                 "但你不知道里面是什么。脚步声从身后的甬道隐隐传来。",
        "interject": ["ambition", "guardian", "selfcore"],
        "choices": {
            "A": {"text": "立刻冲进门里", "delta": {"ambition": 3, "dreamer": 1}},
            "B": {"text": "先退到暗处观察", "delta": {"guardian": 3, "logician": 1}},
            "C": {"text": "回头看看身后是谁", "delta": {"guardian": 2, "empath": 2}},
        },
    },
    # —— node2 · 自我 vs 他人 ——（轴：共情者 / 本我）
    "node2": {
        "axis": "自我 vs 他人",   # 内部元数据，不下发前端
        "stage": "relation",
        "place": "废墟旧集市",
        "bridge": "你的手刚碰到那壶水，几个声音就嚷了起来——",
        "scene": "废墟里的旧集市早已荒废，摊架东倒西歪。你在一具落满灰的背包里"
                 "翻出最后一壶还没变质的净水。抬头时，一个发着高烧的陌生旅人"
                 "正死死盯着它，干裂的嘴唇动了动，却没出声。",
        "interject": ["empath", "selfcore", "guardian"],
        "choices": {
            "A": {"text": "把净水递给旅人", "delta": {"empath": 3, "dreamer": 1}},
            "B": {"text": "自己留着，转身就走", "delta": {"selfcore": 3, "ambition": 1}},
            "C": {"text": "分一半，但要他拿东西来换", "delta": {"logician": 2, "selfcore": 2}},
        },
    },
    # —— node3 · 现实 vs 理想 ——（轴：计算师 / 造梦师）
    "node3": {
        "axis": "现实 vs 理想",   # 内部元数据，不下发前端
        "stage": "vision",
        "place": "无标记的岔路口",
        "bridge": "你停在岔路口，几个声音抢着替你拿主意——",
        "scene": "岔路在你脚下分开。左边是地图上清楚标注的路，尽头是有水有粮的"
                 "补给站，平稳但漫长。右边没有任何标记，只有地平线上一座隐隐"
                 "发光的高塔——传说它装着你要找的答案，可没人证明它真的存在。",
        "interject": ["logician", "dreamer", "ambition"],
        "choices": {
            "A": {"text": "走向那座发光的高塔", "delta": {"dreamer": 3, "empath": 1}},
            "B": {"text": "走地图标注的补给路", "delta": {"logician": 3, "guardian": 1}},
            "C": {"text": "抛开两条路，自己攀崖抄近道", "delta": {"ambition": 2, "dreamer": 1, "selfcore": 1}},
        },
    },
    "node4": {
        "axis": "冒进 vs 谨慎",
        "stage": "open",
        "place": "暴雨前的吊桥",
        "bridge": "桥身开始晃动，几个声音同时贴了上来——",
        "scene": "山谷上方的吊桥只剩半边木板。对岸有一盏刚刚点亮的灯，"
                 "身后的云层却已经压低，雨点砸在绳索上，像在倒数。",
        "interject": ["ambition", "guardian", "dreamer"],
        "choices": {
            "A": {"text": "趁桥还没断，立刻冲过去", "delta": {"ambition": 3, "dreamer": 1}},
            "B": {"text": "先加固绳结，再慢慢过桥", "delta": {"guardian": 3, "logician": 1}},
            "C": {"text": "沿山谷找另一条更远的路", "delta": {"guardian": 2, "empath": 1, "logician": 1}},
        },
    },
    "node5": {
        "axis": "自我 vs 他人",
        "stage": "relation",
        "place": "沉船上的救生艇",
        "bridge": "海水已经没过脚踝，几个声音在浪声里吵起来——",
        "scene": "甲板正在倾斜，救生艇只剩一个空位。一个受伤的水手抓着栏杆，"
                 "旁边还有一只装着航海图和药品的箱子。远处雾里传来微弱的呼救。",
        "interject": ["empath", "selfcore", "guardian"],
        "choices": {
            "A": {"text": "把空位让给受伤的水手", "delta": {"empath": 3, "guardian": 1}},
            "B": {"text": "自己上船，带走航海图和药品", "delta": {"selfcore": 3, "logician": 1}},
            "C": {"text": "先把箱子扔上船，再拉水手一起试试", "delta": {"ambition": 1, "empath": 2, "logician": 1}},
        },
    },
    "node6": {
        "axis": "现实 vs 理想",
        "stage": "vision",
        "place": "钟楼顶端的望远镜",
        "bridge": "镜片里映出两种未来，几个声音开始争抢视野——",
        "scene": "旧钟楼顶有一台望远镜。调向南方，可以看见灯火稳定的港口；"
                 "调向北方，可以看见雪线背后一座没人抵达过的天文台。镜座只能再转一次。",
        "interject": ["logician", "dreamer", "guardian"],
        "choices": {
            "A": {"text": "看向港口，确认补给和航线", "delta": {"logician": 3, "guardian": 1}},
            "B": {"text": "看向天文台，寻找未知的信号", "delta": {"dreamer": 3, "ambition": 1}},
            "C": {"text": "拆下镜片带走，路上再决定看哪里", "delta": {"selfcore": 2, "logician": 1, "dreamer": 1}},
        },
    },
    "node7": {
        "axis": "冒进 vs 谨慎",
        "stage": "pressure",
        "place": "赌桌旁的最后一枚筹码",
        "bridge": "筹码在指尖发烫，几个声音把桌面围住了——",
        "scene": "地下赌厅的灯一盏盏熄灭。你手里只剩最后一枚筹码，"
                 "庄家说下一局赔率最高，但门口的守卫已经开始清场。",
        "interject": ["ambition", "guardian", "logician"],
        "choices": {
            "A": {"text": "把最后一枚筹码压上去", "delta": {"ambition": 3, "selfcore": 1}},
            "B": {"text": "收手离桌，保住还能带走的东西", "delta": {"guardian": 3, "logician": 1}},
            "C": {"text": "要求先看清规则，再决定压不压", "delta": {"logician": 3, "guardian": 1}},
        },
    },
    "node8": {
        "axis": "自我 vs 他人",
        "stage": "pressure",
        "place": "剧院后台的替补名单",
        "bridge": "幕布即将拉开，几个声音在后台压低声音争执——",
        "scene": "主角突然失声，导演把替补名单递到你手里。你知道自己能演，"
                 "也知道另一位替补准备了很久，正站在角落里发抖。",
        "interject": ["selfcore", "empath", "ambition"],
        "choices": {
            "A": {"text": "接过名单，自己上台", "delta": {"selfcore": 3, "ambition": 1}},
            "B": {"text": "把机会推给那位准备更久的人", "delta": {"empath": 3, "dreamer": 1}},
            "C": {"text": "提议两人分场上台，各自承担一半", "delta": {"empath": 1, "logician": 2, "selfcore": 1}},
        },
    },
    "node9": {
        "axis": "现实 vs 理想",
        "stage": "pressure",
        "place": "炼金炉前的蓝图",
        "bridge": "炉火忽明忽暗，几个声音盯着那张蓝图不肯眨眼——",
        "scene": "你有一张能造出飞行器的蓝图，也有一份稳定产粮机器的订单。"
                 "炉火只够熔一批金属，天亮前必须开炉。",
        "interject": ["logician", "dreamer", "ambition"],
        "choices": {
            "A": {"text": "先完成产粮机器的订单", "delta": {"logician": 3, "guardian": 1}},
            "B": {"text": "把金属投进飞行器蓝图", "delta": {"dreamer": 3, "ambition": 1}},
            "C": {"text": "改蓝图，先造一个能卖钱的小飞行翼", "delta": {"logician": 2, "dreamer": 1, "selfcore": 1}},
        },
    },
    "node10": {
        "axis": "冒进 vs 谨慎",
        "stage": "close",
        "place": "清晨前的城门",
        "bridge": "天色快亮了，几个声音终于不再客气——",
        "scene": "城门只在清晨前打开一次。城外是未知的旷野，城内有你熟悉的床、"
                 "熟悉的名字和熟悉的规矩。守门人问你：要不要出城？",
        "interject": ["ambition", "guardian", "selfcore"],
        "choices": {
            "A": {"text": "趁门开着，直接走出去", "delta": {"ambition": 3, "dreamer": 1}},
            "B": {"text": "再住一晚，等下一次门开", "delta": {"guardian": 3, "empath": 1}},
            "C": {"text": "先把城内牵挂处理完，再自己开门", "delta": {"selfcore": 2, "empath": 1, "logician": 1}},
        },
    },
    "node11": {
        "axis": "自我 vs 他人",
        "stage": "close",
        "place": "空房间里的两封信",
        "bridge": "墨水还没干，几个声音围着信纸低声较劲——",
        "scene": "桌上有两封只够寄出一封的信。一封写给你自己，里面是你一直没敢承认的话；"
                 "另一封写给某个等你解释的人，封口处已经被泪水洇开。",
        "interject": ["selfcore", "empath", "dreamer"],
        "choices": {
            "A": {"text": "寄出写给自己的那封", "delta": {"selfcore": 3, "dreamer": 1}},
            "B": {"text": "寄出写给对方的那封", "delta": {"empath": 3, "guardian": 1}},
            "C": {"text": "把两封都撕开，改写成一封真话", "delta": {"selfcore": 1, "empath": 1, "logician": 2}},
        },
    },
    "node12": {
        "axis": "现实 vs 理想",
        "stage": "close",
        "place": "黎明前的灯塔",
        "bridge": "第一束光还没出现，几个声音都知道这是最后一问——",
        "scene": "灯塔顶端有两个开关。一个能照亮脚下的安全航线，另一个能把光打向"
                 "从没人去过的海域。燃油只够亮到日出。",
        "interject": ["logician", "dreamer", "guardian"],
        "choices": {
            "A": {"text": "照亮安全航线，让船稳稳靠岸", "delta": {"logician": 3, "guardian": 1}},
            "B": {"text": "把光打向未知海域，给远方一个信号", "delta": {"dreamer": 3, "ambition": 1}},
            "C": {"text": "先扫一圈近海，再把余光留给远方", "delta": {"logician": 1, "guardian": 1, "dreamer": 2}},
        },
    },
}

# CARDS（想法卡片）：把地牢分数翻译成"指着具体行为说话"的观察 + 对会议 weights 的 ±1 修正。
# 写卡守则：①复述行为再"轻轻拧一下"给新视角（禁贴标签）②标题名词化有余味
#          ③effect 反向制衡、±1 封顶 ④保底卡写"均衡"本身。
# settle 逻辑：取 trigger 命中的多张；不足时补最高共振人格的通用卡；都没中则发 is_fallback 保底卡。
CARDS: list = [
    {
        "id": "act_first",
        "title": "行动先于答案",
        "trigger": lambda s: top_persona(s["scores"]) == "ambition"
        and chose(s["choices"], "node1", "A"),
        "text": "你没等火把照亮整条通道，就跨进了那道门。有趣的是——"
                "你的眼睛在黑暗里，自己学会了看见。",
        "effect": {"guardian": +1},   # 你越敢冲，那个记得疼的声音越需要被听见
    },
    {
        "id": "perfectionism",
        "title": "完美主义的代价",
        "trigger": lambda s: top_persona(s["scores"]) == "guardian"
        and chose(s["choices"], "node1", "B"),
        "text": "你退到暗处，把每一步都看清了才肯走。稳妥得无可指摘——"
                "只是那点微光，没有等你。",
        "effect": {"ambition": +1, "guardian": -1},
    },
    {
        "id": "others_first",
        "title": "替别人活的人",
        "trigger": lambda s: top_persona(s["scores"]) == "empath"
        and chose(s["choices"], "node2", "A"),
        "text": "你把最后一壶水递了出去，自己咽了口唾沫。"
                "你顾得上每一个人，除了渴着的自己。",
        "effect": {"selfcore": +1},
    },
    {
        "id": "naked_want",
        "title": "不必解释的转身",
        "trigger": lambda s: top_persona(s["scores"]) == "selfcore"
        and chose(s["choices"], "node2", "B"),
        "text": "你留下了水，转身就走，没有回头解释。"
                "那一刻你没有在权衡——你只是终于诚实。",
        "effect": {"empath": +1},
    },
    {
        "id": "the_ledger",
        "title": "连善意都要计价",
        "trigger": lambda s: top_persona(s["scores"]) == "logician"
        and chose(s["choices"], "node2", "C"),
        "text": "你愿意分一半，但先谈好了他拿什么来换。账算得没错——"
                "只是有些东西，一标价就凉了。",
        "effect": {"dreamer": +1},
    },
    {
        "id": "chasing_light",
        "title": "追光的人",
        "trigger": lambda s: top_persona(s["scores"]) == "dreamer"
        and chose(s["choices"], "node3", "A"),
        "text": "补给站就在地图上，你却朝着那座没人证明存在的塔走去。"
                "你要的从来不是抵达，是那束光本身。",
        "effect": {"logician": +1},
    },
    # —— 组合卡（非 top_persona 条件，可与上面的主题卡同时掉，凑满多张掉落）——
    {
        "id": "all_in",
        "title": "孤注一掷",
        "trigger": lambda s: chose(s["choices"], "node1", "A")
        and chose(s["choices"], "node3", "C"),
        "text": "石门你直接撞，岔路你攀崖抄近道——两道关你都挑了最不留退路的走法。"
                "你不是不怕，你是赌自己输不起。",
        "effect": {"guardian": +1},   # 越莽，越需要那个记得疼的声音
    },
    {
        "id": "the_hesitant",
        "title": "迟疑的代价",
        "trigger": lambda s: chose(s["choices"], "node1", "B")
        and chose(s["choices"], "node3", "B"),
        "text": "两道门你都先退后、看清了才肯走。你把“看清”当成了周全——"
                "可有些门，是在你确认的时候关上的。",
        "effect": {"ambition": +1},
    },
    # —— 题库随机化后的通用主题卡：当本轮没抽到老三题，也能把最高分人格翻译成观察 —— 
    {
        "id": "generic_ambition",
        "title": "先把火点起来",
        "trigger": lambda s: top_persona(s["scores"]) == "ambition",
        "text": "你在几次岔路前都更愿意让事情先动起来。你不是没看见风险，"
                "只是你更怕那股劲在等待里冷掉。",
        "effect": {"guardian": +1},
    },
    {
        "id": "generic_guardian",
        "title": "退路也是欲望",
        "trigger": lambda s: top_persona(s["scores"]) == "guardian",
        "text": "你总会先摸一摸出口在哪。别急着骂自己保守——有时候，"
                "你想守住的东西，正是你真正珍惜的东西。",
        "effect": {"ambition": +1},
    },
    {
        "id": "generic_empath",
        "title": "别人的重量",
        "trigger": lambda s: top_persona(s["scores"]) == "empath",
        "text": "你的选择里总留着别人的位置。温柔不是问题，问题是你有没有"
                "给自己也留一个座位。",
        "effect": {"selfcore": +1},
    },
    {
        "id": "generic_selfcore",
        "title": "终于不解释",
        "trigger": lambda s: top_persona(s["scores"]) == "selfcore",
        "text": "你很快能听见自己想要什么，而且没有急着替它找一个体面的理由。"
                "这份诚实很好，但它也会伤到旁边的人。",
        "effect": {"empath": +1},
    },
    {
        "id": "generic_logician",
        "title": "账本里的光",
        "trigger": lambda s: top_persona(s["scores"]) == "logician",
        "text": "你不断把混乱的场景折成条件、资源和交换。账算清楚了，"
                "但别忘了问：你为什么要赢这笔账？",
        "effect": {"dreamer": +1},
    },
    {
        "id": "generic_dreamer",
        "title": "远方先开口",
        "trigger": lambda s: top_persona(s["scores"]) == "dreamer",
        "text": "还没算清每一步，你已经听见远方在喊你。那不是幼稚，"
                "只是你的人生不能只靠地图活着。",
        "effect": {"logician": +1},
    },
    {
        "id": "even_council",
        "title": "势均力敌",
        "is_fallback": True,   # 没有任何卡命中时发它
        "trigger": lambda _: True,
        "text": "还没有哪个声音真正赢得你。这场会议，谁都别想轻松——"
                "每个人都得拼尽全力。",
        "effect": {},
    },
]
