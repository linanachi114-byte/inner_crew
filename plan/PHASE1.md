# 阶段 1 执行清单 · 双地基

> 来源：`inner-crew-v2-详细执行计划.md` 第九节阶段 1。
> 目标：FastAPI 骨架 + `/api/interject` 流式插话 + 6 人格 prompt + 前端骨架联调全部立住。
> **联调不通过不进阶段 2。**
>
> 用法：执行某步并验证通过后，把该步验证点从 `- [ ]` 改为 `- [x]`。
> 顺序大致按依赖排列；步骤 12-13（文案类）可与 1-11 并行起草。

---

## 1. 项目骨架与依赖
`uv init` + `uv venv`，`uv add fastapi uvicorn openai openai-agents`，空 `main.py` / `personas.py` / `constants.py` / `scoring.py` / `static/`。

- [x] `uv run uvicorn main:app` 启动无报错，访问 `/` 返回 200。<!-- 已验证：venv Python 3.12.13、/ 返回 200(index.html)、/api/health 返回 200 -->

## 2. StepFun 连通
`.env` 放 StepFun key + base_url + 模型名，写最小 `AsyncOpenAI(base_url="https://api.stepfun.com/v1")` 调用，模型 `step-2-16k`（非推理；勿用 `-flash` 系，推理会吃光 max_tokens 返空）。

- [x] 一次调用能从 StepFun 拿到非空回复。<!-- 已实测：HTTP 200、step-2-16k 正文干净、~1s、function calling 触发 web_search -->

## 3. role:system 生效验证
用一条明显的 system 指令测 Agents SDK `instructions` 映射是否生效。

- [x] system 指令被遵守。<!-- 已实测：system "only English" 被严格遵守、finish:stop，role:system 生效，无需改 role:assistant -->

## 4. 6 人格 prompt 初稿
写入 `personas.py` 的 `PERSONA_PROMPTS`（野心家 / 守护者 / 共情者 / 本我 / 计算师 / 造梦师）。

- [x] 六段齐全，每段含：人设隐喻 + 存在意义 + 固定句式 + 对立态度 + 禁止中立。<!-- 已结构自检：6 键与 PERSONAS 对齐、每段含人格名/禁止中立/对立鄙视。盲测留步骤 6 -->

## 5. Agent 对象 + run_persona()
6 个 `Agent` 对象，封装 `run_persona(pid, user, suffix, max_tokens, timeout)` 辅助函数。

- [x] 单独跑每个 agent 返回符合人设的话。<!-- 已实测：6 人格用项目代码+.env 调 StepFun，输出均对味（命令式/反问/落到人/戳破/数据腔/画面）。注：StepFun 偶发 451 censorship_blocked 误杀，重试即过——留步骤 9 做兜底 -->

## 6. 人格盲测对比
同一场景跑六人格并排输出。

- [x] 盲测可 100% 对上号；分不清的人格重写后复测通过。<!-- 独立判官盲测：首轮 10/12（本我混野心家/守护者）→ 强化本我“戳破”特征重写 → 复测 12/12=100%。脚本 scripts/blind_test.py -->

## 7. 插话短调用
`INTERJECT_SUFFIX`（≤30 字、强烈倾向、禁止中立、禁止分析利弊）接入 `run_persona`。

- [x] 单人格插话 ≤30 字、立场鲜明、单条 <2s。<!-- 已实测：6 人格插话 12-19 字、1.1-1.9s，全部 ≤30 字且 <2s，立场鲜明对味。INTERJECT_SUFFIX + interject() in personas.py -->

## 8. /api/interject SSE 端点
`asyncio` 并行发起 2-3 人格 + `asyncio.as_completed` + `StreamingResponse`（`media_type="text/event-stream"`）。

- [x] `curl -N` 看到多条 `data:` 事件按完成顺序（乱序）到达。<!-- 已实测：三条事件时间戳分明(逐条非缓冲)，到达序 本我→守护者→野心家 ≠ 声明序[ambition,guardian,selfcore]，乱序成立，末尾 {"done":true}，HTTP 200 -->

## 9. 超时与失败兜底
`timeout=5`，单条异常 `continue` 静默跳过。

- [x] 人为制造一个慢/错人格，其余人格仍正常推送，接口不崩。<!-- 已实测：①timeout=0.01 触发 TimeoutError 被静默吞；②强制守护者报错(模拟451)，野心家+本我 照常推送、守护者静默跳过、{done} 正常、流不抛异常 -->

## 10. 前端骨架 static/index.html
议题输入框 + 流式读取 + 气泡逐条浮现（档位 A 单文件）。

- [x] 浏览器输入场景，插话气泡逐条出现。<!-- 已实测：agent-browser 驱动真实浏览器，填议题→点按钮→3 条插话(野心家/本我/守护者)逐条浮现，各带人格专属色发光线+圆点。fetch+ReadableStream 解析 SSE。截图 /tmp/ic_bubbles.png -->

## 11. 前后端联调（阶段 1 闸口）
端到端流式蹦字。

- [x] 截图①前后端流式蹦字；联调通过（不通过不进阶段 2）。<!-- 已通过：真实浏览器→FastAPI→StepFun→气泡流式逐条浮现，重启服务加载新人设后复测，本我/野心家清晰分开。截图①存仓库 docs/screenshots/phase1-02-interject-stream.png（及 01-landing） -->

## 12. 三节点场景文案初稿
`constants.py` 的 `NODES` scene 文本。

- [x] 三节点分别为 冒进vs谨慎 / 自我vs他人 / 现实vs理想，架空情境、不影射现实。<!-- 已写入 constants.NODES：石门/旧集市净水/岔路发光高塔；结构校验过(轴对、delta总分3-4、插话2-3合法)。覆盖:野心7/计算7/共情6/守护5/本我4/造梦4——本我&造梦偏低，留阶段2配平校验脚本处理 -->

## 13. 卡片库候选池起草
`CARDS` 6-8 张候选（含 1 张保底卡）。

- [x] 每张过自检三问：指着行为了吗？拧出新视角了吗？让会议更好看了吗？<!-- 已写入 constants.CARDS：6 themed + 1 保底(even_council)。结构校验过(effect 均±1、保底唯一、trigger 命中逻辑正确)。每张指着地牢具体行为+拧出新视角+反向制衡 weights。triggers 用 scoring.py 的纯谓词 -->

## 14. 阶段 1 验收产物
汇总发群验收。

- [x] 截图②一场景 + 三条风格迥异插话；两份中间产物（流式蹦字、插话截图）齐备。<!-- 截图②=docs/screenshots/phase1-02-interject-stream.png（一场景+命令/戳破/反问三插话+流式蹦字）。验收/交接文档 docs/PHASE1-acceptance.md -->

---

### 阶段 1 验收红线（对应总计划）
首条插话 <2s、全部 <4s · 6 人格盲测 100% 对号 · 前后端流式联调通过。
