# 阶段 1 验收 · 双地基

> 对应总计划第九节阶段 1。完成度 **14/14**，闸口（前后端流式联调）已通过。
> 逐步验证勾选见 `plan/PHASE1.md`。

## 已交付能力

- **后端基座**：`uv` + FastAPI，`uv run uvicorn main:app` 一条命令起；`/api/health`、`/api/interject`（SSE）。
- **LLM 接入**：StepFun（OpenAI 兼容）经 Agents SDK 统一组织，模型走 `.env`（默认 `step-2-16k`）。
- **六人格**：`personas.py` 定稿 6 段 system prompt，盲测独立判官 **100% 对号**；`run_persona()` 通用调用器 + `interject()` 插话姿势。
- **插话链路**：`/api/interject` 并行 2-3 人格 + `as_completed` 乱序流式 + 单条失败静默跳过。
- **前端**：单文件 `static/index.html`（frontend-design 出的暗色油画风），`fetch+ReadableStream` 消费 SSE，气泡逐条浮现、人格专属色。
- **内容草稿**：`constants.NODES` 三节点矩阵、`constants.CARDS` 7 张想法卡（含保底）。

## 验收产物

- 截图①/② `docs/screenshots/phase1-02-interject-stream.png` —— 一场景 + 三条风格迥异插话（命令/戳破/反问），前后端流式蹦字。
- 落地页 `docs/screenshots/phase1-01-landing.png`。
- 盲测脚本 `scripts/blind_test.py`、`scripts/blind_test_light.py`（可复跑）。

## 关键实测结论（影响后续）

- **模型**：`-flash` 系是推理模型，短发言会把 `max_tokens` 耗在 reasoning 上返空、关推理参数无效 → 默认用非推理 `step-2-16k`（function calling 已验证可带计算师工具）。
- **StepFun RPM=10**：超限报 `429`。插话并行 2-3 没问题，整场会议（duel+debate+verdict）须**串行/限速**，批量测试要 throttle。
- **StepFun 偶发 451 审查误杀**：正常内容也可能被拦，重试即过 → 插话单条静默跳过、debate/verdict 重试一次再降级。
- `role: system` 已生效，无需改 `role: assistant`。

## 交给阶段 2 的待办

- **矩阵配平校验**（脚本）：覆盖性每人 ≥6-9 + 枚举 27 路径多样性。当前可达分 `野心7/计算7/共情6/守护5/本我4/造梦4`——**本我、造梦师偏低需调 delta**。
- API 齐套：`/choose`、`/settle`、`/meeting/duel`、`/meeting/debate`、`/meeting/verdict`（计算师工具先留桩）。
- 会前自陈表单 + prompt 注入（静态文案版先行）。
