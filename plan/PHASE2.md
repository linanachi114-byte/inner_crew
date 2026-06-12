# 阶段 2 执行清单 · 主流程（地牢 + 会议串通）

> 来源：`inner-crew-v2-详细执行计划.md` 第九节阶段 2。
> 目标：把地牢、卡片、自陈、三幕会议、建议书串成一条端到端能跑通的主流程（丑没关系）。
> **阶段 2 闸口：浏览器从立题走到建议书，一次完整流程跑通。**
>
> 用法：执行某步并验证通过后，把 `- [ ]` 改为 `- [x]`，附实测备注。
> 复用：`scoring.py`(top_persona/chose/count_chosen)、`constants.NODES/CARDS/OPPOSITION`、
> `personas.run_persona/interject`、`models.pick_model`。
> 注意：整场会议调用受 **StepFun RPM=10** 限制，须串行/限速 + 451/解析失败重试（见 CLAUDE.md）。

---

## 1. 矩阵配平校验脚本
`scripts/balance_check.py`：① 覆盖性——每人格三节点可达分上限 ≥6-9；② 多样性——枚举 27 条选择路径，统计最高分人格分布。不达标就调 `constants.NODES` 的 delta 重跑。

- [x] 脚本输出覆盖性 + 27 路径分布；每人覆盖达标、无单一人格占 20+ 条路径。<!-- scripts/balance_check.py。调 delta 后：覆盖性六人格全=6；多样性 27 路径胜场 野心6/守护7/共情6/本我3/计算3/造梦2，无0胜无20+。exit 0 通过。只改delta未动选项文案，卡片trigger仍对齐 -->

## 2. /api/choose 后端算分
`scoring.choose(state, node_id, choice_id)`：按 `NODES[node][choices][cid][delta]` 累加 `scores`，把 `(node, choice)` 追加进 `choices`，返回更新后 state。端点 `POST /api/choose`。

- [x] curl 连选三节点，`scores` 按 delta 正确累加、`choices` 记三项；delta 表只在后端（前端不持有）。<!-- 已实测：scoring.choose 纯函数(不原地改)+ /api/choose 端点；state 来回传 scores 服务端累加正确、choices 记三项、非法选项 graceful error -->

## 3. /api/settle 卡片结算（纯函数零 LLM）
`scoring.settle(state)`：遍历 `CARDS`，trigger 命中取前两张；都没中发 `is_fallback` 保底卡；按 `effect` 更新 `weights`（±1）。端点 `POST /api/settle`。

- [x] 命中态返前两卡、错配态返保底卡；`weights` 按 effect 正确更新、不改 scores 前两名排序。<!-- 已实测：scoring.settle 纯函数(命中act_first/错配走even_council/effect±1/不原地改)+ /api/settle 端点。注：当前6主题卡均以top_persona为条件→每次最多1张(符合"掉落1-2张"下限) -->

## 4. 会前自陈 /api/ask（静态版 P0.5）
`POST /api/ask`：入参 `{topic, state}`，返回静态 `{logician_q, selfcore_q}`（常量文案，动态措辞留阶段 3）。答案写回 `state.assets`(计算师问)/`state.desire`(本我问)。

- [x] 端点返回两问静态文案；前端把回答写入 state.assets / state.desire。<!-- 已实测：/api/ask 返回 constants.ASK_FALLBACK 两问(计算师"有什么牌"/本我"想要什么")。前端写回 assets/desire 是步骤11。动态措辞留阶段3 -->

## 5. 第一幕 /api/meeting/duel（对峙）
`scoring.pick_duelists(state)`：取 `OPPOSITION` 中 scores 之和最大的对立对。两人格依次陈词、流式逐字。prompt 注入 `topic/assets/desire/choice_summary/opponent_name`，预判并刺对手一句。

- [x] duel 端点流式返回两人格陈词；内容引用议题/自陈、点到对手；选出的确是最强对立对。<!-- 已实测：pick_duelists 选(野心家,守护者)和最大；stream_persona token级流式；两段陈词引用"六个月生活费/螺丝钉"、各自预判并刺对手、≤100字对味。串行2调用避RPM+首token前重试1次 -->

## 6. 第二幕 /api/meeting/debate（选边与调停）
其余 4 人格按 `scores + weights` 排序依次发言。硬格式：第一行只能是 `【支持X】/【支持Y】/【第三条路】`，再 ≤80 字理由。解析失败重试一次，再失败归"第三条路"。计算师工具**先留桩**（纯 prompt 发言）。

- [x] 4 人格依次表态，首行格式合法可解析、无人和稀泥；人为造一个坏格式能重试/归类不崩。<!-- 已实测：debate_order 按scores+weights(计算师因weights+1领先)；4人首行【】全部解析成功(third/b/a/a)、无和稀泥、引用自陈+呛人；坏格式→重试1次→归第三条路(parse_stance None用例+_debate_one兜底覆盖) -->

## 7. 阵营 + transcript 结构化记录
每条 duel/debate 发言解析出阵营（支持谁/第三条路）写入 `state.transcript`，供天平可视化(前端，阶段3)与 verdict 输入。

- [x] 一场会议跑完，`transcript` 含每条发言的 {persona, stance, text}。<!-- 已实测：scoring.append_speech/tally_camps 纯函数(模拟6条→结构对、阵营{a:3,b:2,third:1})；duel end事件改为带 stance+完整text，与 debate 对齐，前端两幕统一 append_speech 入 transcript -->

## 8. 第三幕 /api/meeting/verdict（裁决建议书）
`POST /api/meeting/verdict`：入参 `topic + 自陈 + transcript + likes + 用户裁决`，JSON 输出 `{verdict_summary, persona_positions, action_steps, risk_notes, dissent}`。prompt **写死**"用户裁决是最终决定，禁止重新论证该不该这样选"。

- [x] 给定 transcript + 裁决，返回五字段 JSON；只展开裁决为可执行建议、不重新权衡；dissent 是落败方一句保留意见。<!-- 已实测：裁决=听野心家(创业)+补充"留足缓冲"→五字段齐全、summary以裁决为基调不重新论证、action_steps围绕裁决+补充、dissent="机会背面是悬崖"(守护者)、persona_positions 6条。书记角色+写死铁律+json_object+重试 -->

## 9. 会议串行限速 + 失败兜底
整场会议（duel 2 + debate 4 + verdict 1）串行/限速跑，避开 RPM=10；451/解析失败重试一次再降级。

- [x] 完整会议端到端跑通不撞 429；单条 451/坏格式不拖垮整场。<!-- 已实测 scripts/meeting_e2e.py：7次调用串行、duel7.6s+debate19.9s+verdict32.2s=总59.7s(≤90s红线)、transcript6条、verdict五字段、未崩。三处重试加 models.is_rate_limit 429退避(限流等6s) -->

## 10. 前端 · 地牢三节点选择页
`index.html` 扩成多幕：立题 → 三节点（场景 + 插话 + 三选项），选项接 `/api/choose`、进节点接 `/api/interject`。state JSON 来回传。

- [x] 浏览器走完三节点，每步插话浮现、选择落库，state.scores/choices 正确累积。<!-- 已实测：立题→node1(3插话气泡+3选项,轴对)→选A→node2 scores累积{ambition3,dreamer1}choices记录→走完三节点 scores{ambition3,empath4,dreamer5}。新增 GET /api/nodes(无delta)。截图 ic2_intro/node1 -->

## 11. 前端 · 卡片结算页 + 自陈表单
卡片页接 `/api/settle`（可先假数据占位）；自陈表单（卡片后、会议前）两输入框接 `/api/ask`，回答写回 state。

- [x] 卡片翻出、自陈两问可填并写入 state.assets/desire。<!-- 已实测：settle 掉「追光的人」(top造梦师+node3A)、weights logician:1、3D翻转揭示；自陈页加载计算师/本我两问，2输入框写回 state.assets/desire。截图 ic2_cards/ic2_ask -->

## 12. 前端 · 会议三幕页 + 建议书
会议页串 duel → debate（逐条发言）→ 三按钮裁决（听A/听B/综合，均带可选补充框）→ 调 verdict 渲染建议书。

- [x] 浏览器看完三幕、点裁决按钮、出结构化建议书 + dissent 收尾。<!-- 已实测：duel流式两人入两阵营+天平、debate4人表态天平倾斜、6发言带👍、第三幕3按钮+可选补充→建议书(summary/3步骤/6立场/risk/dissent)。本轮对峙对=计算师vs造梦师(scores驱动)，听A=计算师=留职，补充被吸收。截图 phase2-04/05 -->

## 13. 端到端整跑（阶段 2 闸口）
一次完整流程：立题 → 地牢 → 卡片 → 自陈 → 会议三幕 → 建议书，state 全程正确传递。

- [x] 浏览器端到端跑通一次（丑没关系），截图③；不通过不进阶段 3。<!-- 已实测：立题→地牢三节点(插话+选择,scores累积)→卡片(追光的人,3D翻转)→自陈两问→会议三幕(对峙流式+选边天平+裁决)→建议书五字段。全程 state JSON 来回传正确。截图 docs/screenshots/phase2-01..05 -->

---

### 阶段 2 验收红线（对应总计划）
完整会议端到端 ≤90s（计算师搜索计入阶段3） · 第一幕有实质冲突、第二幕无人和稀泥 · 积分必在后端、前端薄。
