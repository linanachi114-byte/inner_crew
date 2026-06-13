# 六人格像素 Sprite · 生图提示词

> 给 2.0「像素小人对战」会议场用的角色立绘提示词。目标:六个 sprite 像**同一套卡司**（同画风/视角/比例/画布），拼在一个战斗场里不违和。
> 用法:每个角色把【通用风格块】粘在最前，再接该角色的【专属块】。主色 hex 与应用里的人格专属色一致（`static/index.html` 的 `--ambition` 等），务必让该色成为服装/光环主调。
> 配套计划见 `plan/PHASE5.md`；素材最终存到 `static/sprites/<persona_id>.png`。

---

## 通用风格块（每个角色前都粘这段）

```
16-bit SNES-era pixel art sprite, single character, full body, 3/4 side view
facing RIGHT in an idle battle-ready stance. Chibi heroic proportions, about
2.5 heads tall, consistent across a cast of six. Bold clean 1px dark outline,
limited ~16-color palette, soft dithered shading, flat front lighting.
Centered on a SOLID FLAT pure-green (#00FF00) background — one uniform color
filling every background pixel, NO checkerboard, NO gradient, NO scenery,
no text, no ground shadow. Generous padding around the character.
Readable distinct silhouette. Crisp pixels, no anti-aliasing, no blur.
```

> ⚠️ **别让模型自己出"透明背景"**——GPT/Gemini 只能输出 RGB、没有 alpha，"透明"会被它画成灰白棋盘格（假透明马赛克）。所以一律让它出**纯色实心底**，透明由我们事后抠（见末尾"抠图"）。计算师是青绿色，与绿底会糊在一起 → **那一张把背景色改成纯品红 #FF00FF**。

---

## 1. 野心家 ambition · 主色 `#c0463b`（砖红）

> 气质:脑内的征服者 · 只管"冲"

```
A bold conqueror youth, forward-lunging aggressive pose as if charging.
Brick-red (#c0463b) cape and light armor, a red scarf streaming forward with
momentum, one fist or a short sword raised. Confident fierce grin, sharp eyes.
Silhouette = dynamic forward motion. Red is the dominant color.
```

## 2. 守护者 guardian · 主色 `#6c8fb3`（钢蓝）

> 气质:风险清单的化身 · 永远反问"代价呢"

```
A steadfast sentinel, planted defensive stance, wide stable silhouette.
Steel-blue (#6c8fb3) heavy cloak and rounded pauldrons, holding a large round
guard shield in one arm and a small warning lantern in the other. Calm wary
eyes, watchful. A rolled checklist scroll tucked at the belt. Blue dominant.
```

## 3. 共情者 empath · 主色 `#d29b8c`（暖玫瑰陶土）

> 气质:替每个人感受的那根神经

```
A gentle warm-hearted figure, open welcoming posture, one hand reaching out
and one hand over the heart. Soft flowing rose-terracotta (#d29b8c) robe,
kind caring eyes, a faint small glowing heart hovering at the open palm.
Silhouette = open arms. Warm rose dominant.
```

## 4. 本我 selfcore · 主色 `#b15a86`（梅紫/品红）

> 气质:只问你真正想要什么 · 戳破伪装

```
A raw unmasked self, barefoot, stripped-down simple tunic in plum-magenta
(#b15a86). One hand on own chest, the other holding a removed blank theater
mask lowered at the side. Direct piercing honest gaze straight ahead.
Silhouette = simple and grounded. Plum-magenta dominant.
```

## 5. 计算师 logician · 主色 `#57b09b`（青绿）

> 气质:把一切折算成账 · 带真实检索

```
A studious accountant-strategist, slightly hunched bookish pose. Teal-green
(#57b09b) long coat, round spectacles, holding an open ledger book and a quill
in mid-calculation, a small magnifying glass and a satchel of scrolls at side.
Focused analytical eyes. Silhouette = book-in-hands. Teal dominant.
```

## 6. 造梦师 dreamer · 主色 `#9a8fd6`（薰衣草紫）

> 气质:用十年后的画面说话 · 追光

```
A dreamy visionary gazing upward, one hand reaching toward a small floating
glowing star/light above. Long trailing lavender (#9a8fd6) robe with a starry
hem, serene faraway eyes, faint sparkles around. Silhouette = upward reach.
Lavender dominant, ethereal glow.
```

---

## 生成 & 存放须知

- **保持一致**:六张用同一模型、同一句通用风格块;模型支持的话固定同一 seed;一次性出全套，别分多天换风格。
- **只出朝右一版**即可——左侧阵营用 CSS `transform: scaleX(-1)` 水平翻转，省一半素材。
- **背景出纯色实心底（绿 #00FF00 / 计算师用品红 #FF00FF），不要让模型出透明**——透明事后抠。
- **抠图(把纯色底变真 alpha)**:用 `scripts/key_bg.py`，从四角洪水填充扣掉纯色底，输出 RGBA 透明 PNG 到 `static/sprites/<id>.png`：
  ```
  .venv/bin/python scripts/key_bg.py <生成的图> <persona_id>
  # 绿底默认;品红底加 --chroma magenta;颜色不准加 --tol 60
  ```
  按人格 id 命名，六个 id:`ambition / guardian / empath / selfcore / logician / dreamer`。
  （前端 `StaticFiles` 托管，素材必须在 `static/` 下；前端按 `persona id → /sprites/{id}.png` 映射，与现有专属色天然对齐。）
- 显示时 CSS 加 `image-rendering: pixelated;`(像素风)或留默认(平滑)。
- **进阶（可选，先不急）**:每人再出一张"攻击姿势"（挥手/前冲）做反驳特效第二帧；或让模型直接出 idle+attack 的 sprite sheet。v1 用单张 idle + CSS 位移/抖动/闪光即可。
