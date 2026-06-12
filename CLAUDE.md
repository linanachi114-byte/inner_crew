# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目状态

黑客松项目 **Inner Crew v2**（Track 02，比赛日 6/14）。当前仓库仅有总计划 `inner-crew-v2-详细执行计划.md`，**代码尚未开始**——动工前先读该计划，它是唯一的事实来源（人格设定、prompt 模板、矩阵、卡片、三幕结构、API 契约、砍单优先级全在里面）。

一句话定位：重要决策时帮用户把脑内"没开成的会"开起来。
主线：**立题 → 三步地牢（测人格）→ 想法卡片结算 → 会前自陈问询 → 决策会议三幕 → 决策建议书**。

## 技术栈与运行

- 后端 = **FastAPI（Python）**，承载全部逻辑；LLM 用 **StepFun（阶跃星辰，本项目赞助方）OpenAI 兼容端点**（`base_url=https://api.stepfun.com/v1`，国际版 `https://api.stepfun.ai/v1`），**默认全用 `step-3.7-flash`**（`.env` 的 `STEPFUN_MODEL`，已定全 flash）；统一用 **OpenAI Agents SDK**（`Agent` + `Runner.run`），流式用 `StreamingResponse`（SSE）。
- **flash 是推理模型，必须给足 max_tokens + reasoning_effort=low**：它先写 `reasoning` 再写 `content`、共用 `max_tokens`；预算不够时思考没写完就被截断（`finish_reason:length`）→ `content` 返空。**解法**：`reasoning_extra()` 注入 `reasoning_effort=low`（flash 吃、step-2-16k 忽略）+ 短发言 max_tokens 地板 **≥2500**（verdict 3500/ask 2000）+ `run_persona` 空内容重试一次。实测 0/6 空、~4s/次（慢但稳，已接受这个延迟换"最新模型 + agentic 工具调用"）。
- **JSON 结构化调用（verdict 建议书 / ask 两问）用 `models.JSON_MODEL`（默认 `step-2-16k`）**：flash 的 `response_format=json_object` 会产出乱码键（实测 `{": ":`）→ 这俩幕后总结器必须用非推理模型。即"人格全 flash，幕后 JSON 用 step-2-16k"。
- **想回快版**：`.env` 的 `STEPFUN_MODEL=step-2-16k` 一行即切回（非推理、~1s）；代码两套兼容（token 地板/超时只在含 flash 时抬高）。模型配置集中在 `models.py`：`DEFAULT_MODEL`（人格）/ `LOGICIAN_TOOL_MODEL`（计算师工具循环，flash）/ `JSON_MODEL`（verdict、ask）。
- 前端 = vibe 出来的静态页面，FastAPI 静态托管：`app.mount("/", StaticFiles(directory="static", html=True))`。起步用单文件 `static/index.html`（档位 A）。
- **环境与依赖用 `uv` 管理**：`uv venv` 建虚拟环境、`uv add` 加依赖、`uv run uvicorn main:app` 启动；依赖锁在 `pyproject.toml` / `uv.lock`，不手搓 `pip install`。
- **一个进程、一个仓库**：`uv run uvicorn main:app` 跑起来。
- 所有 key（StepFun、搜索 API）只放后端 `.env`，前端永不直连外部 API。

## 架构铁律（违反即返工）

- **前端尽可能薄**：流程逻辑（在哪一幕、积分、掉卡、排序）全在 Python 纯函数里；前端只"报告用户动作 + 渲染返回内容"。
- **状态全在前端**：全局 `state`（JSON：topic/assets/desire/scores/choices/cards/weights/likes/transcript）每次请求带给后端，后端算完连同结果返回，**后端零持久化**。
- **积分必须后端算**（`/api/choose` 独立端点），前端不持有 delta 表。
- `scores` 是地牢测量（决定第一幕谁对峙），`weights` 是卡片修正（仅卡片可改，±1 封顶，不得改变 scores 前两名排序）。

## 6 个人格

定义为 6 个 `Agent` 对象，`instructions` = system prompt、`name` = 人格名。五个纯 prompt 人格直接 `Runner.run`；**仅计算师**挂 `web_search` function tool 跑 tool loop（`max_turns=3`，失败降级为无工具纯 prompt，可用环境变量一键关）。
对立轴：`OPPOSITION = [("ambition","guardian"),("empath","selfcore"),("logician","dreamer")]`。
写 prompt 守则：极端化、固定句式、禁止中立；六个写完同场景盲测，分不清谁是谁就重写。
StepFun 注意：① `role: system` 已实测生效（Agents SDK 的 `instructions` 默认映射 system）。② StepFun 偶发 `451 censorship_blocked` 误杀正常内容（重试即过）——所以插话单条失败要静默跳过、debate/verdict 要重试一次再降级，别让单次审查误杀拖垮整场。③ **当前档位 RPM=10（每分钟 10 次请求），超了报 `429 rate_limited`**——插话并行 2-3 个没问题，但整场会议（duel 2 + debate 4 + verdict 1）要串行/限速跑、别一次性并发；批量测试要 throttle 到 ≤10/min；demo 前确认配额或升档。

## 目录结构（保持清晰，新增文件归位别堆根目录）

```
main.py          # FastAPI app、路由、SSE 编排
personas.py      # 6 个 Agent 定义 + PERSONA_PROMPTS + web_search 工具
constants.py     # NODES（三节点矩阵）、CARDS、OPPOSITION 等纯数据
scoring.py       # 算分/结算/排序等纯函数（无 LLM、可单测）
static/index.html# vibe 前端（档位 A 单文件）
.env             # StepFun key + base_url + 模型名 / 搜索 key，仅后端，勿提交
```

逻辑（纯函数）与数据（常量）与编排（路由）分文件；前端产物一律进 `static/`。

## API 端点

`/api/interject`（SSE，并行 2-3 人格短调用、乱序推送）· `/api/choose`（后端算分）· `/api/settle`（纯函数零 LLM，trigger 命中取前两张卡）· `/api/ask`（动态生成两问，超时>4s 回退静态文案）· `/api/meeting/duel`（第一幕对峙）· `/api/meeting/debate`（第二幕选边，第一行硬约束表态格式，解析失败重试一次后归"第三条路"）· `/api/meeting/verdict`（汇总 JSON 建议书，prompt 须写死"用户裁决是最终决定，禁止重新论证"）。

## 砍单优先级（时间不够按序砍）

P2 彩蛋 → 自陈动态措辞（回退静态）→ 点赞按钮 → 计算师搜索（降级纯 prompt）→ 阵营天平 → 卡片压到 4 张+保底。
**永不砍**：插话、三幕会议、自陈注入（静态版）、录屏兜底。
验收红线：首条插话 <2s；完整会议端到端 ≤90s；Demo 3 分钟。
