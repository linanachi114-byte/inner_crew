"""纯数据：人格清单、对立轴、三节点矩阵、想法卡片。无逻辑、无 LLM。"""

from scoring import chose, top_persona  # 卡片 trigger 用到的纯谓词

PERSONAS = ["ambition", "guardian", "empath", "selfcore", "logician", "dreamer"]

OPPOSITION = [("ambition", "guardian"), ("empath", "selfcore"), ("logician", "dreamer")]

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
    "logician_q": "先盘点一下——你手里到底有什么牌？存款、技能、人脉、时间，"
                  "现实里你具备的筹码有哪些？",
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
        "place": "废墟深处 · 将闭的石门",
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
        "place": "废墟旧集市",
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
        "place": "无标记的岔路口",
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
}

# CARDS（想法卡片）：把地牢分数翻译成"指着具体行为说话"的观察 + 对会议 weights 的 ±1 修正。
# 写卡守则：①复述行为再"轻轻拧一下"给新视角（禁贴标签）②标题名词化有余味
#          ③effect 反向制衡、±1 封顶 ④保底卡写"均衡"本身。
# settle（阶段2）逻辑：取 trigger 命中的前两张；都没中则发 is_fallback 那张保底卡。
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
    # —— 组合卡（非 top_persona 条件，可与上面的主题卡同时掉，凑满"1-2 张"）——
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
