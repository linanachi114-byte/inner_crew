# Inner Crew v2 详细开发计划（定稿版）

> 黑客松 Track 02 · 自由创意 · 两人队 · **比赛日 6 月 14 日，剩余约 2 天**
> 一句话定位：重要决策时，每个人心里都有一场没开成的会。Inner Crew 帮你把这场会开起来。
> 流程主线：**立题 → 三步地牢（测人格）→ 想法卡片结算（buff）→ 会前自陈问询 → 决策会议（用人格）**

---

## 〇、系统总览与技术栈

```
用户输入真实决策议题
        │
        ▼
┌─ 三步地牢 ────────────────────────┐
│  节点1 → 节点2 → 节点3            │
│  每节点：场景文本 → 人格插话(2-3条) │
│         → 用户选择 → 矩阵累积得分  │
└──────────────┬───────────────────┘
               ▼
   想法卡片结算（if-else 匹配，掉落 1-2 张 buff 卡）
               ▼
  人格化自陈采集（会前问询：计算师问"你有什么牌"，本我问"你想要什么"）
               ▼
┌─ 决策会议 ────────────────────────┐
│  第一幕：最对立的两个人格对峙陈词    │
│  第二幕：其余人格选边/调停           │
│    · 阵营天平实时倾斜（battle 可视化）│
│    · 每条发言可 👍（用户中途参与）   │
│    · 计算师可调搜索工具带数据进场    │
│    · 人格发言可引用用户自陈作论据    │
│  第三幕：用户主意识裁决（选边/综合， │
│          均可附一句补充）           │
└──────────────┬───────────────────┘
               ▼
        决策建议书（结构化输出）
```

**技术栈（定稿）**：
- **后端 = FastAPI（Python）**：人格调用、矩阵、结算、会议编排全在这；LLM 经 **StepFun（阶跃星辰，本项目赞助方）OpenAI 兼容端点**，流式用 `StreamingResponse`（SSE）
- **前端 = vibe 出来的静态页面**，由 FastAPI 静态托管：`app.mount("/", StaticFiles(directory="static", html=True))`
- **一个进程、一个仓库、一条 `uvicorn main:app` 跑起来**
- 状态全放前端：全局 `state` 是一个 JSON，每次请求带给后端，后端算完连同结果返回。后端零持久化
- 比赛现场：本地跑 + 录屏兜底；赛后部署：Railway / Render / HF Spaces

**LLM 调用方式：全部用 OpenAI Agents SDK 统一组织**：
- **六个人格全部定义为 `Agent` 对象**：`instructions` 放 system prompt、`name` 放人格名
- **五个纯 prompt 人格**不挂工具，`Runner.run()` 直接跑；**计算师**挂 `web_search` function tool 跑 tool loop
- 接口：Chat Completions（StepFun OpenAI 兼容接口），SDK 指向 StepFun（base_url 与模型名走 `.env`，便于切换）：

```python
from agents import Agent, Runner, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

stepfun_client = AsyncOpenAI(
    base_url="https://api.stepfun.com/v1",   # 国际版：https://api.stepfun.ai/v1
    api_key="YOUR_STEPFUN_KEY",
)
MODEL = OpenAIChatCompletionsModel(model="step-2-16k",   # 非推理、正文干净、~1s、function calling 可用
                                   openai_client=stepfun_client)
# 注意：勿用 -flash 系（step-3.7/3.5-flash）——推理模型，短发言会把 max_tokens 耗在 reasoning 上返空

guardian_agent = Agent(name="守护者", instructions=PERSONA_PROMPTS["guardian"], model=MODEL)
logician_agent = Agent(name="计算师", instructions=PERSONA_PROMPTS["logician"],
                       model=MODEL, tools=[web_search])
# ... 其余四个同理
```
- 一句话答辩词：**"六个人格统一用 Agents SDK 组织，计算师额外挂搜索工具跑 tool loop——框架用来统一结构，工具调用才是它真正发力的地方。"**

**模型选择（按场景，改起来方便）**：模型名集中在 `.env` + 一处映射 `pick_model(endpoint)`，代码不写死，后期不满意只改环境变量、不动逻辑。
- **默认全用 `step-2-16k`**（非推理、正文干净、~1s、function calling 已实测可带计算师工具）。本项目几乎全是 ≤30/≤80 字的短发言，非推理模型最合适。
- **唯一例外：决策建议书 `/api/meeting/verdict`**——慢 2-3s 可接受、要综合 transcript/自陈/点赞做深推理，可选 `step-3.7-flash` + `reasoning_effort`，用环境变量开关（默认仍 `step-2-16k`）。
- **flash 系（3.7/3.5）不能做短发言**：推理模型先写 reasoning 再写 content、共用 `max_tokens`，短预算下思考没写完就被截断返空；官方无法关推理（`reasoning_effort` 仅 low/medium/high，无 none）。已逐一实测确认。
```python
# models.py —— 一处映射，后期改这里即可
DEFAULT_MODEL = os.getenv("STEPFUN_MODEL", "step-2-16k")
VERDICT_MODEL = os.getenv("STEPFUN_MODEL_VERDICT", DEFAULT_MODEL)  # 想给 verdict 用 flash 就设这个环境变量

def pick_model(endpoint: str) -> str:
    return VERDICT_MODEL if endpoint == "verdict" else DEFAULT_MODEL
```

**架构铁律：前端尽可能薄。** 流程逻辑（在哪一幕、积分、掉卡、排序）全在 Python 纯函数里，前端只负责"报告用户动作 + 渲染返回内容"。**积分必须在后端算**（`/api/choose` 独立端点），前端不持有 delta 表。

**安全细节**：StepFun 与搜索 API 的 key 只放后端 `.env`，前端永不直连外部 API。

---

## 一、人格阵容（6 个）

三组天然对立轴：

| ID | 人格名 | 一句话人设 | 口癖/语气 | 对立面 | 工具 | 自陈采集 |
|----|--------|-----------|----------|--------|------|---------|
| `ambition` | 野心家 | 脑内的征服者，蔑视一切"够用就好" | 命令式，爱用"必须""现在" | `guardian` | — | — |
| `guardian` | 守护者 | 风险清单的化身，先想最坏情况 | 总在反问"如果……怎么办？" | `ambition` | — | — |
| `empath` | 共情者 | 替所有相关的人感受，先人后己 | 总提到具体的"那个人会怎样" | `selfcore` | — | — |
| `selfcore` | 本我 | 只关心"你真正想要什么"，对义务过敏 | 直白甚至刻薄，戳破伪装 | `empath` | — | **问"你想要什么"** |
| `logician` | 计算师 | 一切翻译成成本收益和概率 | 数据腔，爱列"第一、第二" | `dreamer` | **搜索** | **问"你有什么牌"** |
| `dreamer` | 造梦师 | 用十年后的画面说话，鄙视精算 | 诗意腔，描述画面而非论证 | `logician` | — | — |

```python
OPPOSITION = [("ambition", "guardian"), ("empath", "selfcore"), ("logician", "dreamer")]
```

> 命名注意：不用极乐迪斯科原技能名，机制致敬、文案原创，pitch 里大方说灵感来源。
> 工具分配原则：只给计算师、只给搜索一个工具、只在会议陈词时触发。

---

## 二、人格化自陈采集（会前问询 · 固定骨架 + 动态措辞）

**流程位置：地牢 → 卡片 → 自陈 → 会议**。放在地牢之后的三个理由：
1. **保护测量纯度**：先郑重写下"我想要什么"再进地牢，用户会表演一致性（"说了想要自由就该选大胆的"），投射被污染；先玩后问，地牢选择保持诚实；
2. **角色先登场，提问才成立**：地牢走完用户已认识各人格，计算师上前问话是熟人开口，不是陌生角色查户口；
3. **摩擦后置**：开场打字是流失点；玩完地牢领完卡的用户已经投入，此刻填两框是"为会议蓄势"。

叙事定位：试炼 → 试炼的裁定（卡片）→ **会前问询** → 议事会。

**设计**：两个输入框，视觉包装成两个人格在发问。**问题的语义骨架锁死，措辞动态生成**：
- **计算师**永远问"我具备什么"（资源盘点），**本我**永远问"我想要什么"（真实欲望）——问什么不变；
- 一次轻量 LLM 调用（两问合并生成），针对**议题 + 地牢行为**改写问法——怎么问跟着用户走。

示例（议题"要不要离职去创业公司"，地牢选择偏稳）：
- 计算师："你在三个路口都选了最稳的路——那么算笔账，你现实里稳妥的牌有哪些？存款够撑几个月？"
- 本我："试炼里你每次都先看别人。现在没人看着——你到底想要什么？"

提问引用地牢行为，延续卡片建立的"它在观察我"体验。

**安全性**：语义骨架锁死，最坏情况只是问法平淡，不会问出格；预设 demo 议题的生成结果可提前彩排。**回退逻辑**：生成超时（>4s）或失败，落回静态默认文案（"盘点一下，你手里有什么牌？"/"抛开'应该不应该'——你到底想要什么？"），零风险。

**实现**：`POST /api/ask`，入参 `{topic, state}`（state 供引用地牢行为），一次调用 JSON 输出 `{logician_q, selfcore_q}`，失败回退常量。**不做全自主动态提问**（LLM 自主决定问什么 → 流程不可控、demo 不可彩排）。回答存入 `state.assets` 和 `state.desire`，注入**会议所有人格**的 prompt 作为可引用论据（采集是两人的，使用是全员的）。

**效果**：会议中人格能说出"你自己说过，你有六个月的生活费"——用户的真话成为辩论弹药；问询本身贴着用户的议题和行为，是和纯聊天体验区分的关键一击。

**优先级与成本**：静态文案版属 P0.5，主线必做；动态措辞属 **P1**，排在插话、三幕、流式联调全部跑通之后——一次额外调用、+2-3s、prompt 模板半小时，回退兜底后零风险。

---

## 三、打分矩阵与状态结构

```python
state = {
    "topic": "",                          # 用户的真实决策议题
    "assets": "",                         # 自陈：我有什么牌（计算师采集）
    "desire": "",                         # 自陈：我想要什么（本我采集）
    "scores": {p: 0 for p in PERSONAS},   # 六人格激活度（地牢测量）
    "choices": [],                        # [(node_id, choice_id), ...]
    "cards": [],                          # 掉落的想法卡片 id
    "weights": {p: 0 for p in PERSONAS},  # 会议权重修正（仅卡片可改）
    "likes": [],                          # 会议中用户点赞的发言 [(persona, utterance_id)]
    "transcript": [],                     # 会议记录，供建议书使用
}
```

**scores 与 weights 的分工**：scores 是测量（你内心哪些声音本来就强，决定第一幕谁对峙）；weights 是修正（卡片基于观察调整话语权，影响第二幕的发言顺序/篇幅/出场保底）。卡片 effect 限 ±1：只微调格局，不颠覆测量——任何卡不应改变 scores 排序前两名。

矩阵示例（节点 1，`constants.py`）：

```python
NODE_1 = {
    "scene": "……（场景文本）",
    "interject": ["ambition", "guardian", "selfcore"],  # 本节点登台插话的人格（固定）
    "choices": {
        "A": {"text": "立刻推门进去", "delta": {"ambition": 3, "dreamer": 1}},
        "B": {"text": "先绕一圈观察", "delta": {"guardian": 3, "logician": 1}},
        "C": {"text": "问同伴的意见", "delta": {"empath": 3}},
    },
}
```

**插话人格与打分解耦**：插话名单是演出安排（每节点 2-3 个，挑与本节点张力轴相关的上台）；delta 对全部六人格开放（每个节点都在为六人悄悄积分，只是台上吵架的换班）。

场景写作要求：节点1 = 冒进 vs 谨慎，节点2 = 自我 vs 他人，节点3 = 现实 vs 理想；架空冒险情境（废墟、集市、岔路），不影射现实决策；每选项 delta 总分相近（3-4 分），无标准答案。

**矩阵配平校验（定稿前必跑，十几行脚本）**：
1. 覆盖性：三节点全选项 delta 加总，六人格每个理论上限 ≥ 6-9 分；
2. 路径多样性：枚举 27 条选择路径，统计最高分人格分布——若 20+ 条都是同一人格，调 delta 重配。

---

## 四、P0-1 插话机制

`POST /api/interject` — 入参 `{node_id, state}`。并行发起 2-3 个人格短调用，SSE 逐条推送，前端按到达顺序浮现（乱序更像脑内吵架）。

```python
import asyncio, json
from fastapi.responses import StreamingResponse

async def interject_stream(node, state):
    tasks = {
        pid: asyncio.create_task(run_persona(pid,
            user=f"场景：{node['scene']}", suffix=INTERJECT_SUFFIX,
            max_tokens=80, timeout=5))
        for pid in node["interject"]
    }
    for coro in asyncio.as_completed(tasks.values()):
        try:
            pid, text = await coro
            yield f"data: {json.dumps({'persona': pid, 'text': text})}\n\n"
        except Exception:
            continue          # 单条失败静默跳过

@app.post("/api/interject")
async def interject(req: InterjectRequest):
    return StreamingResponse(interject_stream(NODES[req.node_id], req.state),
                             media_type="text/event-stream")
```

插话 prompt 后缀（共用）：

```
现在你在用户的脑内目睹了上述场景。用你的性格插一句话（不超过30个字），
带强烈倾向地建议用户怎么做。禁止中立，禁止分析利弊，就一句你的直觉。
直接输出这句话，不要任何前缀。
```

人格 system prompt 模板（守护者示例）：

```
你是用户脑内的一个人格碎片：守护者。
你是风险清单的化身。你的存在意义是确保用户活下来、不失去已有的东西。
你看任何事第一反应是"最坏会发生什么"。你说话总用反问句式：
"如果失败了怎么办？""你确定退路还在吗？"
你不是懦弱，你是用户脑内唯一记得疼的人。你对那些怂恿冒险的声音感到愤怒。
你永远有明确立场，从不说"看情况"。你的话简短、紧绷、像拉响的警报。
```

写作守则：人设隐喻 + 存在意义 + 固定句式 + 对其他人格的态度 + 禁止中立。六个写完同场景跑一遍并排对比，分不清谁是谁的重写。

**StepFun 注意**：先测 `role: system` 是否生效，不行再换 `role: assistant` 放首条；Agents SDK 的 `instructions` 默认映射 system。

验收：首条插话 < 2s，全部 < 4s；盲测 6 人格输出可 100% 对上号。

---

## 五、想法卡片结算（P1，纯硬编码）

**卡片的本质**：把地牢分数翻译成一段"指着你具体行为说话"的观察（叙事面），同时对会议话语权做一次修正裁定（数值面）。卡在"测量结束"和"使用开始"之间：给地牢一个结算仪式，给会议埋一个钩子。

```python
CARDS = [
    {
        "id": "perfectionism",
        "title": "完美主义的代价",
        "trigger": lambda s: s["scores"]["guardian"] >= 8
                     and count_info_choices(s) >= 2,
        "text": "你在地牢里三次停下来确认地图，却两次错过了正在关闭的门。"
                "准备的尽头不是完美，是错过。",
        "effect": {"ambition": +1, "guardian": -1},
    },
    {
        "id": "act_first",
        "title": "行动先于答案",
        "trigger": lambda s: top_persona(s) == "ambition"
                     and ("node2", "A") in s["choices"],
        "text": "你没等火把照亮整条通道就走了进去。有趣的是——"
                "你的眼睛在黑暗里自己适应了。",
        "effect": {"guardian": +1},   # 反向制衡：你越偏科，对立面越需要声量
    },
    # ……6-8 张（主要得分模式 + 1 张保底）
]
```

`POST /api/settle`（纯函数零 LLM）：trigger 命中取前两张，没中发保底卡；按 effect 更新 weights。

写卡守则：① 文案复述具体行为再"轻轻拧一下"（给新视角），禁止标签判断；② 标题名词化有余味（「行动先于答案」不是「冒险型人格」）；③ 效果反向制衡，±1 封顶；④ 保底卡写"均衡"本身（"还没有哪个声音赢得你——这场会议，每个人都要拼尽全力"）。每张自检三问：指着行为了吗？拧出新视角了吗？让会议更好看了吗？

UI：3D 翻转解锁，停留 3-5 秒。demo 情绪高点。

---

## 六、P0-2 决策会议三幕结构

### 第一幕 · 对峙

```python
def pick_duelists(state):
    return max(OPPOSITION,
               key=lambda pair: state["scores"][pair[0]] + state["scores"][pair[1]])
```

`POST /api/meeting/duel` — 两人格依次陈词，流式逐字渲染。陈词 prompt 附加：

```
用户的真实议题是：{topic}
用户的自陈——拥有的资源：{assets}；真实渴望：{desire}
用户在试炼中的表现摘要：{choice_summary}
用你的性格就这个议题发言（不超过100字），给出明确建议和一个最有力的理由。
可以引用用户的自陈作为论据。你知道 {opponent_name} 会反对你，预判并刺它一句。
```

### 第二幕 · 选边与调停

`POST /api/meeting/debate` — 其余 4 人格按 `scores + weights` 排序依次发言（权重高者先发言、max_tokens 120 其余 100、被 buff 者保底出场）。格式硬约束：

```
刚才 {duelist_a} 主张：{statement_a}
{duelist_b} 主张：{statement_b}
用户的自陈——拥有：{assets}；渴望：{desire}
你必须明确表态，第一行只能是：【支持{duelist_a}】/【支持{duelist_b}】/【第三条路】
然后用不超过80字陈述理由，可引用用户自陈，可点名呛上一位发言者。
禁止和稀泥，禁止"两边都有道理"。
```

解析失败重试一次，再失败归"第三条路"。

**人格互呛**（形似 handoff 的零风险替代）：允许点名呛声——观感像自主交锋，控制流仍在 Python 手里。不用真 handoff：其行为可预测性差，会让三幕结构散架。

**阵营天平（battle 可视化，新增）**：会议页顶部一个立场条，每条发言解析出表态后，该人格头像滑入对应阵营、天平实时倾斜。数据全部来自已有的结构化表态，**零后端改动、零额外调用**，纯前端组件。不做血条/攻击动画等重度版。

**发言点赞（用户中途参与，新增）**：每条发言旁一个"👍 有道理"，点击记入 `state.likes`，作为 verdict 输入（"用户对守护者、计算师的发言表示认同"）。**不做多轮循环发言**（每轮 +6 次调用 +30s，且边际信息量衰减；demo 3 分钟红线扛不住），互呛已提供交锋感。

### 计算师的搜索工具（P1，全项目唯一 agentic loop）

```python
from agents import Agent, Runner, function_tool

@function_tool
def web_search(query: str) -> str:
    """检索与决策议题相关的真实数据（市场、统计、行情等）。"""
    # 调 Tavily / Serper 等（免费额度），返回要点文本
    ...

async def logician_speak(ctx):
    try:
        result = await Runner.run(logician_agent, build_debate_input(ctx),
                                  max_turns=3)   # 循环上限，防失控
        return result.final_output
    except Exception:
        fallback = Agent(name="计算师", instructions=PERSONA_PROMPTS["logician"],
                         model=MODEL)            # 降级：去工具纯 prompt 发言
        result = await Runner.run(fallback, build_debate_input(ctx), max_turns=1)
        return result.final_output
```

**降级开关**：搜索超时/失败时自动降级；环境变量可一键关工具，会场网络不稳时保命。

### 第三幕 · 主意识裁决

三个按钮：听 A 的 / 听 B 的 / 我要综合。**三个选项都带同一个可选输入框**："想补充一句吗？（可选）"——选边的用户同样有保留意见要落地（"听野心家的，但先存够六个月生活费"），只给综合选项配输入框等于惩罚选边用户。必须标注可选、留空可提交：按钮是表态，补充是馈赠，别把馈赠变成作业。

`POST /api/meeting/verdict` 汇总调用（输入：topic + 自陈 + transcript + likes + 用户裁决），JSON 输出：

```json
{
  "verdict_summary": "以用户裁决为基调的方向总结",
  "persona_positions": [{"persona": "...", "stance": "...", "key_point": "..."}],
  "action_steps": ["围绕用户裁决/补充拆出的可执行步骤"],
  "risk_notes": "守护者要求附上的风险提示",
  "dissent": "落败一方人格的保留意见（一句话）"
}
```

**verdict prompt 必须写死从属关系**："用户的裁决是最终决定，你的任务是把它展开为可执行建议并附风险，禁止重新论证该不该这样选。"不写这条，模型会夹带重新权衡，毁掉裁决的意义。裁决的产品哲学：AI 只组织辩论、不拍板（IFS 的 Self-leadership；也是答辩时回应"AI 替人做决定"质疑的现成答案）。

`dissent` 收口："野心家保留意见：缓冲期是怯懦的别名。"——内心的会永远开不完。

验收：完整会议端到端 ≤ 90s（计算师搜索计入预算，超时即降级）；5 个测试议题 review：第一幕实质冲突、第二幕无人和稀泥。

---

## 七、视觉规范（给 vibe 工具的审美指令）

- **整体气质**：神秘 + 内省。暗色调、油画质感、衬线标题（借极乐迪斯科的气质，不借素材）
- **人格专属色**：六人格各一色，贯穿插话气泡、会议发言、天平头像、建议书立场标注。一个决定让全产品显得"被设计过"
- **字体性格化**：计算师等宽体、造梦师衬线体
- **五个核心画面**：立题与自陈页 / 地牢场景页 / 卡片解锁页 / 会议页（含阵营天平）/ 建议书页

前端档位：
- **档位 A（推荐起步且大概率够用）**：单文件 `index.html`，CSS/JS 内联或 CDN（Tailwind CDN / React UMD）。vibe 成功率最高，放进 `static/` 即可
- **档位 B**：Vite + React + Tailwind + Framer Motion，build 出 `dist/` 给 FastAPI mount。两天冲刺期默认不升

---

## 八、Demo 演示脚本（3 分钟红线）

| 时间 | 内容 | 提前准备 |
|------|------|---------|
| 0:00-0:30 | 概念 pitch + 总览图 + 输入议题 | pitch 词背熟 |
| 0:30-1:15 | 地牢节点 1 完整走 + 节点 2/3 快进 | 议题预设（"要不要离职去创业公司"），插话彩排过 |
| 1:15-1:30 | 卡片翻转解锁，念文案 | 选最惊艳的卡确保命中 |
| 1:30-1:50 | **会前问询**：两个人格针对议题和地牢表现发问，快速填两句自陈 | 自陈答案提前想好两短句，现场快打 |
| 1:50-2:50 | 会议三幕：对峙 → 天平倾斜中各人格表态（**计算师检索真实数据**，发言引用自陈"你说过你有六个月存款"）→ 邀评委按裁决按钮 | 议题选能搜到数据的；备搜索降级话术 |
| 2:50-3:00 | 建议书 + dissent 收尾："内心的会，永远值得再开一次" | — |

**兜底**：全程录屏。现场抽风直接切录屏，不现场调试。

---

## 九、排期与分工（四阶段，按依赖滚动推进）

**阶段 1 —— 双地基（并行，最先动工）**
- [ ] **你**：FastAPI 骨架 + `/api/interject` 跑通（async 并行 + SSE + 超时兜底），curl 验证流式；顺手测 `role: system` 在 StepFun 是否生效
- [ ] **你**：6 个人格 system prompt 初稿 → 同场景盲测对比 → 定稿（项目灵魂，最优先立住）
- [ ] **队友**：vibe 单文件前端骨架，接 SSE 逐条渲染——**联调通过才进阶段 2，不通过不盖楼**
- [ ] **并行启动**：卡片库 + 三节点场景文案，AI 起草候选池，两人有空就筛
- 中间产物：① 前后端流式蹦字；② 一场景 + 三条风格迥异插话的截图，发群验收

**阶段 2 —— 主流程（地牢 + 会议串通）**
- [ ] 三节点矩阵定稿（跑配平校验脚本：覆盖性 + 27 路径多样性）
- [ ] API 齐套：`/choose`、`/settle`、`/meeting/duel`、`/meeting/debate`、`/meeting/verdict`（计算师工具先留桩）
- [ ] 会前自陈表单（位于卡片后、会议前）+ prompt 注入（P0.5，静态文案版先行）
- [ ] 前端流程页串通：state JSON 来回传，先用假卡片数据
- 中间产物：端到端跑通一次完整流程（丑没关系）

**阶段 3 —— 内容填充与包装**
- [ ] 真卡片库接入（6-8 张，筛改定稿）
- [ ] 计算师搜索工具接入（Agents SDK + function tool + 降级开关）
- [ ] 自陈问题动态措辞（`/api/ask` 按议题+地牢行为改写两问，超时回退静态文案）
- [ ] 阵营天平 + 点赞按钮（纯前端 + 一个 likes 数组）
- [ ] UI 打磨：人格专属色、卡片 3D 翻转、发言乱序浮现、字体性格化、建议书排版
- [ ] 5 个测试议题完整跑，按验收标准 review
- 中间产物：计算师能真实检索并带数据发言；全流程"像个产品"

**阶段 4 —— 演练与兜底**
- [ ] Demo 脚本彩排 ≥ 3 次，互为观众掐表挑刺；重点演练计算师搜索段（含失败降级）
- [ ] **录屏兜底**（最迟阶段 4 一开始就录，别拖到最后）+ pitch 词定稿
- [ ] （有余力）P2 失败彩蛋：低分选项静态吐槽文案

**比赛日早晨**
- [ ] 会场网络实测（StepFun + 搜索 API 连通性），不通则开降级开关/切录屏预案
- [ ] 最后一次彩排

**分工总原则**：
- **你**：FastAPI 侧一切（人格 prompt、Agent 定义、流程逻辑、tool loop）+ pitch 与答辩
- **队友**：vibe 前端 + SSE 联调 + UI 打磨（含天平、点赞）
- **文案**：AI 起草 + 两人筛改
- 距比赛仅约两天，阶段推进以**砍单优先级**兜底——时间不够按此顺序砍：P2 彩蛋（默认不做）→ 自陈动态措辞（回退静态文案）→ 点赞按钮 → 计算师搜索工具（降级纯 prompt）→ 阵营天平 → 卡片压到 4 张 + 保底。**永不砍**：插话、三幕会议、自陈注入（静态版）、录屏兜底。

**赛后路线图（不写代码，答辩可提）**：小程序适配——前端薄 + 后端全逻辑天然支持换壳，FastAPI 原封不动；SSE 在小程序无标准支持、域名需 HTTPS+ICP 备案，列为赛后事项。部署 Railway / Render / HF Spaces 出公网链接进 portfolio。

---

## 十、风险清单

| 风险 | 对策 |
|------|------|
| SSE 在 vibe 前端出细节 bug | 今晚联调最小流式链路，不通过不盖楼 |
| 前端状态错乱 | 前端薄化：状态机全在 Python，前端只渲染 |
| API 延迟/抽风 | 并行 + 短输出 + timeout + 录屏兜底 |
| 计算师搜索失败/会场网络差 | 自动降级 + 环境变量一键关工具 |
| system prompt 角色映射 | 先测 `role: system`，不行换 `role: assistant` 放首条 |
| 人格趋同 | 极端化 prompt + 盲测，不过关重写 |
| 第二幕和稀泥 | 格式硬约束 + 重试 + 降级归类 |
| 时间不够 | 按砍单优先级执行，主线永不让位 |
| 评委质疑"玩具还是工具" | 答辩词：自我抽离/IFS 依据 + 自陈与真实数据进入辩论 + AI 只组织不拍板 + 诚实边界（非心理咨询、无效度宣称） |
| IP 争议 | 机制致敬、命名文案全原创，大方说灵感来源 |
