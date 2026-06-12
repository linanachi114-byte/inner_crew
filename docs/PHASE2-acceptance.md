# 阶段 2 验收 · 主流程（地牢 + 会议串通）

> 对应总计划第九节阶段 2。完成度 **13/13**，端到端闸口（浏览器立题→建议书）已通过。
> 逐步勾选见 `plan/PHASE2.md`。

## 已交付能力

- **纯函数层（scoring.py，可单测零 LLM）**：`choose`（算分）、`settle`（卡片结算）、`pick_duelists`、`debate_order`、`parse_stance`、`append_speech`、`tally_camps`、`choice_summary`。
- **矩阵配平**：`scripts/balance_check.py`——覆盖性六人格全 = 6、27 路径多样性无 0 胜无 20+。
- **API 齐套**：`/api/nodes`（只读，无 delta）、`/api/choose`、`/api/settle`、`/api/ask`（静态）、`/api/meeting/duel`（流式）、`/api/meeting/debate`（硬格式选边）、`/api/meeting/verdict`（JSON 五字段）。
- **会议三幕**：第一幕对峙（最强对立对、token 流式、引用自陈+刺对手）、第二幕选边（4 人按 scores+weights、首行【支持X/第三条路】硬格式、解析失败归第三条路）、第三幕裁决（书记角色+写死铁律"不重新论证"）。
- **前端多幕 SPA**（单文件 `static/index.html`）：立题→地牢三节点（插话+选择）→卡片 3D 翻转→自陈两问→会议三幕（阵营天平+👍点赞）→建议书。state JSON 全程前后端来回传。

## 验收产物

- 端到端截图 `docs/screenshots/phase2-01-intro … 05-report.png`。
- 会议后端 e2e：`scripts/meeting_e2e.py`（duel+debate+verdict 总 59.7s ≤90s 红线）。

## 关键实测结论

- 完整会议 7 次调用串行，总 ~60s，在 90s 红线内；三处重试加 `models.is_rate_limit` 429 退避。
- 卡片当前 6 主题卡均以 top_persona 为条件 → 每次最多掉 1 张（符合"1-2 张"下限）；要两张同掉需加非 top 条件卡。
- 计算师搜索工具阶段 2 留桩（纯 prompt 发言）。

## 交给阶段 3 的待办

- 计算师搜索工具（Agents SDK + function tool + 降级开关）——全项目唯一 agentic loop。
- 自陈动态措辞 `/api/ask`（按议题+地牢行为改写，超时回退静态文案）。
- UI 打磨：发言乱序浮现、字体性格化、建议书排版、卡片情绪高点。
- 5 个测试议题完整跑 + 验收 review。
