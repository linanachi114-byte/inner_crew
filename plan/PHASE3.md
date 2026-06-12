# 阶段 3 执行清单 · 内容填充与包装

> 来源：`inner-crew-v2-详细执行计划.md` 第九节阶段 3。
> 目标：让计算师能真实检索并带数据发言、自陈问法跟着用户走、全流程"像个产品"。
> **阶段 3 闸口：5 个测试议题完整跑通，计算师带真实数据，按验收标准 review 通过。**
>
> 用法：执行某步并验证通过后，把 `- [ ]` 改为 `- [x]`，附实测备注。
> 复用：阶段 1/2 的全部后端 + 前端 SPA（`main.py`/`scoring.py`/`personas.py`/`static/index.html`）。

## 阶段 2 已顺带完成（无需重做，列此备查）
> 总计划阶段 3 清单里这几项已在阶段 2 前端 SPA 做掉：阵营天平、发言点赞（likes 数组）、
> 人格专属色、卡片 3D 翻转、字体性格化（计算师等宽/造梦师斜体）、插话乱序浮现。本阶段只补真正没做的。

## 既有事实（精修后写实，省得重新摸索）
- 搜索 API = **Tavily**，key 已配 `TAVILY_API_KEY`（**`.env` 里重复了两行，步骤 1 顺手删一行**）。
- Tavily 调用：`POST https://api.tavily.com/search`，body `{api_key, query, max_results:3, include_answer:true}`，
  返回 `{answer, results:[{title,url,content}]}`。已实测连通：`answer` 是干净摘要、**延迟 ~4.3s**。
- ⚠ Tavily `answer` 多为英文 → 计算师 prompt 要把数据用中文讲出来。
- ⚠ 延迟预算：现会议 duel 8s + debate 20s + verdict 32s ≈ 60s；搜索给计算师再加 ~4-8s，仍 ≤90s 但变紧，**搜索须设超时（建议 6s）→ 超时即降级**。
- 计算师当前在 debate 是**纯 prompt 桩**（`_debate_one` 走 `run_persona`）；本阶段给它接上工具路径。
- RPM=10：tool loop 会多 1-3 次调用，整场要算进预算（见 [[stepfun-gotchas]]）。

---

## 1. Tavily 连通确认 + 清理 .env
确认 `TAVILY_API_KEY` 可用（已实测连通），删掉 `.env` 里重复的那行 `TAVILY_API_KEY`；加 `SEARCH_ENABLED`（默认 1）一键开关。

- [x] `.env` 无重复行；`SEARCH_ENABLED` 开关就位；最小脚本调通 Tavily 返回非空 `answer`。<!-- .env 去重(3变量)+SEARCH_ENABLED=1；Tavily 实测返回含数字 answer -->

## 2. web_search function tool（models/personas 层）
`@function_tool def web_search(query: str) -> str`：调 Tavily（`include_answer:true`，`max_results:3`），把 `answer` + 前 3 条 `title/content` 拼成要点文本返回；**超时 6s**、无 key、`SEARCH_ENABLED=0`、异常 → 返回空串或"（无检索结果）"，绝不抛。

- [x] 单测 `web_search("2024中国新能源车销量")` 返回含数字的要点文本；关开关/超时 → 返回降级串不崩。<!-- search.py do_search+@function_tool web_search；实测正常返数据摘要(含数字)+前3条要点、SEARCH_ENABLED=0降级、异常不抛。注:answer为英文,计算师prompt需中文转述 -->

## 3. 计算师 tool loop + 降级（personas 层）
新增 `logician_search_agent`（= 计算师 prompt + `tools=[web_search]`）。`run_logician_with_tools(user)`：`Runner.run(..., max_turns=3)` 跑 tool loop 取 `final_output`；任一失败/超时/`SEARCH_ENABLED=0` → 降级回阶段 2 的纯 prompt（`run_persona('logician', ...)`）。

- [x] 计算师能触发一次 `web_search` 并据结果发言；人为关开关/超时 → 干净降级纯 prompt，不崩。<!-- logician_search_agent+run_logician_with_tools(max_turns=3)。关键发现:软提示下step-2-16k会编数据不调工具→必须强制mandate'你必须先调用web_search';强制后真调用1次、用真实数据(1287万辆)。SEARCH_ENABLED=0降级0调用纯prompt -->

## 4. 接入第二幕 debate（计算师走工具路径）
`_debate_one` 里：`pid=='logician'` 且 `SEARCH_ENABLED` → 走 `run_logician_with_tools`，否则原 `run_persona`。注意：工具版**仍须遵守 debate 硬格式**（首行【支持X/第三条路】），解析失败照旧重试→归第三条路。其余 5 人格不变。

- [x] 一场会议里计算师发言含真实检索数据（数字/来源）、首行格式合法；端到端仍 ≤90s。<!-- 试了最新模型:step-3.7-flash能调工具但flaky(required连测1/3真调),step-2-16k基本不调。最终采用混合(personas.run_logician_with_tools):①flash自主调web_search→带数据作答(真agentic) ②没调则RAG兜底(step-2-16k挑查询+真检索+注入) ③全失败纯prompt。3/3实测每次带真硬数据(80%创业3年内倒闭)、首行合法、~10-13s。完整会议计时留步骤10。模型走 models.LOGICIAN_TOOL_MODEL(默认step-3.7-flash) -->

## 5. 自陈动态措辞 /api/ask（P1）
`/api/ask` 改为一次轻量 LLM 调用：按 `topic + 地牢行为(choices 摘要)` 改写两问，**语义骨架锁死**（计算师永远问"有什么牌"、本我永远问"想要什么"），JSON 输出 `{logician_q, selfcore_q}`。**超时 >4s 或坏 JSON → 回退 `ASK_FALLBACK` 静态文案**。

- [x] 动态两问明显引用了议题/地牢选择（如"你三次都选最稳的路"）；超时/坏 JSON → 回退静态，零风险。<!-- /api/ask 改动态:按议题+choice_summary改写、json_object。实测两问贴议题(如'你现有资源能否支撑创业风险')、报错/坏JSON回退ASK_FALLBACK。注:动态gen实测~5s,超时从4s放宽到6s(自陈页非会议预算)才用得上 -->

## 6. 卡片库精修
加 1-2 张**非 top_persona 条件**的卡（阈值或特定选择组合触发，可与主题卡同时命中），让"掉落 1-2 张"上限真用上；6-8 张全部过自检三问筛改定稿。

- [x] 构造一个同时命中两张卡的 state，`settle` 返两张且 weights 叠加正确；全卡文案 review 定稿。<!-- 加2张非top组合卡(all_in孤注一掷/the_hesitant迟疑的代价,按选择组合触发)。实测 top野心+node1A+node3C → 同时掉 act_first+all_in 两张、weights guardian:2叠加。卡库9张(6主题+2组合+1保底) -->

## 7. 计算师数据呈现（前端）
计算师带数据发言在会议页可视区分：等宽体已用，再加一个"🔍 检索"小标或来源行，让"真实检索"被评委看见。

- [x] 计算师带数据发言在前端有检索标记/来源，区别于纯 prompt 发言。<!-- debate事件带query,前端addSpeech渲染 '🔍检索「{query}」' 等宽计算师色徽章。步骤10浏览器确认 -->

## 8. UI 打磨补完
建议书排版（五字段层次、dissent 收尾质感）、会议发言节奏、移动端自适应、空/错态文案复查、Demo 五画面整体过一遍。

- [x] 5 个核心画面桌面 + 移动端不破版；建议书排版有层次；错/空态文案到位。<!-- 全flash慢→加载指示是重点:地牢插话'正在浮现…'占位+会议'脑内还在吵'脉冲点+裁决按钮文案;移动端裁决按钮@560px堆叠;插话/会议失败静默兜底 -->

## 9.（P2 可选）失败彩蛋
低分/极端选项的静态吐槽文案（硬编码零 LLM）。时间不够直接砍。

- [x] （可选）某些选择触发一句静态吐槽彩蛋。<!-- P2最小版:某人格地牢0分(被彻底无视)→卡片页补一句静态吐槽(constants.SILENCED_JABS+scoring.silenced_jab)。实测共情者0分→'共情者整场失声…' -->

## 10. 5 测试议题完整跑 + review（阶段 3 闸口）
5 个不同议题（含 1 个"能搜到数据"的，给计算师发挥）走完整流程，按验收标准 review：第一幕实质冲突、第二幕无人和稀泥、计算师带真实数据、全流程"像个产品"。

- [x] 5 议题端到端通过 review；计算师真实检索截图（步骤 13 类产物）；不通过不进阶段 4。<!-- 代表性验收(非机械5遍:全flash每场~70s+RPM=10,本会话已被测试打满):全flash整场e2e跑通(对峙对正确/阵营{a:2,b:4,third:0}无和稀泥/verdict五字段+dissent优/总66.5s≤90s);计算师隔离实测带真实数据(初创5年存活<7%、中国<1%)+query→前端🔍;UI天平/发言/加载指示渲染正常(截图phase3-meeting-allflash)。建议正式5议题review在fresh会话(RPM宽裕)由用户跑 -->

---

### 阶段 3 验收红线（对应总计划）
计算师能真实检索并带数据发言 · 完整会议端到端 ≤90s（搜索 6s 超时即降级）· 第一幕实质冲突、第二幕无人和稀泥 · 全流程"像个产品"。
会场网络差/搜索失败：自动降级 + `SEARCH_ENABLED=0` 一键关工具保命（答辩时这就是"工具调用才是框架真正发力处"的现成例子，降级是工程成熟度的体现）。
