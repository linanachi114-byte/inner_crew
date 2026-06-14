# 阶段 7 执行清单 · Claude「暖奶油编辑部」换肤

> 来源：`design/claude/DESIGN.md`（Claude.com 设计系统）+ 本次讨论拍板的四个取舍。
> 性质：**纯前端视觉换肤（token 级）**，只改 `static/index.html` 的 CSS + 极少量"文字-on-强调色"修正。**不动任何 JS 编排、API、舞台动效、导出逻辑。**
> owner 全部 = `我`（写代码）；验收 = 盲看像 Claude + 全流程跑通 + 对比度达标。

## 0. 已拍板（不再讨论，直接执行）

- **整体走向**：奶油亮屏 + 暗色舞台。平静五屏走暖奶油 canvas；会议屏是一张浮在奶油上的深海军蓝产品卡。奶油↔深蓝交替 = 设计系统的招牌节奏。
- **像素舞台**：保留 sprites + 全套编排，只换外壳（外框换成系统 surface-dark 产品卡）。
- **改造方式**：token 级换肤，逐屏把现有 CSS 指向新 token，**保住全部 JS**。
- **衬线字重**：大标题从 900 降到 **500 + 负字距**（系统铁律"衬线不加粗"，中文大字用 500 保存在感）。

## 1. 换肤核心机制（先懂这一条，后面都顺）

现有 CSS 大量引用 `--ground / --bone / --brass / --line / --ground-2 / --panel / --muted / --faint` 这几个语义变量。换肤靠两步，**绝大多数组件无需逐个改**：

1. **全局把这几个变量重定义成奶油值**（`:root`）→ 立题/转场/地牢/卡片/自陈/建议书 全部自动翻成奶油。
2. **在 `#s-meeting` 上把这几个变量「就地覆盖回深色」**（CSS 自定义属性会向子元素继承）→ 会议屏的所有子组件自动变回深色，**一行组件 CSS 都不用动**。

> 只有两类需要逐个手改：① 把强调色当**文字底**用的双关点（如 `.go` 在强调色上的文字色）；② 写死的深色 hex（`.card .face` 渐变等）落在了现在变奶油的屏上。清单见 §5。

## 2. Token 层（写进 `:root`，覆盖现有值 + 新增）

```css
:root{
  /* —— 面 —— */
  --ground:#faf9f5;        /* canvas 页面底 */
  --ground-2:#efe9de;      /* surface-card：输入框/选项/次级填充 */
  --panel:#f5f0e8;         /* surface-soft：scene 等柔色块 */
  --surface-dark:#181715;  /* 会议产品卡底 */
  /* —— 字 —— */
  --bone:#141413;          /* ink 主文字 */
  --body:#3d3d3a;          /* 正文 */
  --muted:#6c6a64;         /* 次级 */
  --faint:#8e8b82;         /* 最弱/说明 */
  /* —— 强调 —— */
  --brass:#cc785c;         /* coral：主 CTA + 关键 eyebrow（克制） */
  --coral-active:#a9583e;
  --on-primary:#ffffff;
  --teal:#5db8a6; --amber:#e8a55a;
  /* —— 线 —— */
  --line:#e6dfd8;          /* hairline */
  /* —— 6 人格色（保留、向暖调和；珊瑚不占人格位）—— */
  --ambition:#bf4d3a; --guardian:#7c93a8; --empath:#d29b8c;
  --selfcore:#b35a82; --logician:#5db8a6; --dreamer:#9b8fc9;
  /* —— 圆角（从 2-3px 抬到系统刻度）—— */
  --r-md:8px; --r-lg:12px; --r-xl:16px; --r-pill:9999px;
  /* —— 字体 —— */
  --serif:"Noto Serif SC",Georgia,serif;
  --sans:"Inter","Noto Sans SC",-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,monospace;
}
```

- [ ] 写入新 `:root`（保留 `--mono`，其余按上表覆盖/新增）。

## 3. 会议屏深色就地覆盖（一块搞定整个会议）

```css
/* 会议 = 浮在奶油上的深海军蓝产品卡 */
#s-meeting{
  background:var(--surface-dark); border-radius:var(--r-xl);
  padding:clamp(20px,4vw,32px); color:#faf9f5;
  /* 子组件沿用同名变量、自动变回深色 */
  --ground:#181715; --ground-2:#1f1e1b; --panel:#252320;
  --bone:#faf9f5; --body:#e9e3d6; --muted:#a09d96; --faint:#6c6a64;
  --line:#2a2925;
}
```

- [ ] 加上 `#s-meeting` 覆盖块。验证：arena/focus/speeches/verdict-zone/裁决 textarea 全部仍是深色、文字 on-dark 清晰。
- [ ] arena 内部写死深色（星空/剪影/月光地面）**保持不动**——它们本就该在暗卡里。

## 4. body / 字体 / 噪点

- [ ] `body`：背景换成 §2 的奶油渐变（暖奶油 radial，去掉冷紫调）；默认字体正文用 `--sans`、标题类用 `--serif`；文字色 `--bone`。
- [ ] `body::after` 胶片噪点：奶油屏上 `opacity` 从 `.045` 降到 `~.02`（系统是干净平面派）；落在会议暗卡上的部分不碍事，保留。
- [ ] 字体 `<link>`：保留 Noto Serif SC（降字重用，不再加载 900）；**正文加 Inter**（`wght@400;500`）；可选给 Latin 词配 EB Garamond（省加载可先不上，记备选）。
- [ ] h1/h2 大标题：`font-weight` 900→**500**，加负字距 `letter-spacing:-0.01em~-0.02em`；`.dim` 用 `--faint`。

## 5. 逐屏 / 逐组件改点清单（奶油屏的写死深色 + 双关点）

### 立题 s-intro / 转场 s-prelude（奶油）
- [ ] `.eyebrow` 保持 coral（小、克制，合规）。
- [ ] `.prelude-line` 现在是大块 `--brass`（会满屏珊瑚）→ 改 `--bone`/`--body`，只留必要的一处珊瑚强调。
- [ ] `.go`（主 CTA）：`background:var(--brass)`(coral) 保留；`color:var(--ground)` 会变奶油字→显式改 `color:var(--on-primary)`；圆角 2px→`--r-md`；hover 阴影色随 coral。
- [ ] 输入框 `input,textarea`：`background:var(--ground-2)`→奶油 surface（自动 reflow）；`color`→ink（reflow）；圆角 3px→`--r-md`；focus 环已是 `--brass`=coral，符合系统。

### 地牢 s-dungeon（奶油）
- [ ] `.scene`：深色渐变 → 奶油 `surface-soft/card`（用 `--panel,--ground-2` 自动 reflow，确认观感）；`.scene::before` 的 inset 暗角在奶油上要减弱或去掉；`.scene p{color:#d9d2c4}`(写死) → `var(--body)`。
- [ ] `.bubble`（匿名声音）：`color-mix(var(--c)...)` 渐变在奶油上会偏淡——把人格色 alpha 适度提高；`.bubble .said{color:#e9e3d6}`(写死) → `var(--bone)`；左脊 + 圆点保留人格色。
- [ ] `.choice` 选项：bg/color 走变量自动 reflow；圆角抬到 `--r-md`；hover 边框 coral。
- [ ] `.choose-prompt`/`.bridge`：走 muted 变量即可，确认在奶油上够清晰。

### 卡片 s-cards（奶油）★写死深色最多
- [ ] `.card .face`：`linear-gradient(160deg,#241c33,#191320)`(写死深) → 奶油 `surface-card`（可极淡渐变）；边框 `--brass`→ coral/hairline；圆角已 6px→抬 `--r-lg`。
- [ ] `.card .back`：深渐变 → `surface-cream-strong (#e8e0d2)`；文字 `--faint`。
- [ ] `.card .ctitle` coral 保留；`.card .ctext{color:#ddd6c8}`(写死) → `var(--body)`。
- [ ] `.jab` 末尾吐槽：`--faint` + 左线 `--line`，确认奶油上可读。
- [ ] 3D 翻转动画**不动**（只换面色）。

### 自陈 s-ask（奶油）
- [ ] 两个 `label`（计算师/本我）用人格色——确认在奶油上对比度够（logician=teal、selfcore=玫红，均 OK）。
- [ ] textarea 同立题输入框处理。

### 会议 s-meeting（深卡，§3 已覆盖；仅查关键项）
- [ ] `act-label` eyebrow = coral on dark，确认清晰。
- [ ] `.speech / .focus-card / .momentum / .veil / .verdict-caption / 三阵营 zones` 写死的浅色文字**保持**（它们就在暗卡里）。
- [ ] `verdict-btns / .vbtn`：在暗卡里走 reflow 后的深色变量；选中态 `.sel` 边框 coral。
- [ ] 裁决 textarea：暗卡内深色输入，focus 环 coral。

### 建议书 s-report（奶油）★第二个眼校屏
- [ ] `#report-card` 在奶油上呈"会议纪要"文档：`.eyebrow` coral、`h2` 衬线 500、`.report h3` 小标题 coral/uppercase。
- [ ] `.report li::before`、`.dissent` 顶线、`.pos-sep` 走 `--line/--faint` reflow，确认奶油上层次清楚。
- [ ] `.go`（导出 PNG 按钮）同主 CTA 处理。

### 全局零碎
- [ ] `#director` 演示导演条：深色悬浮条本就该深，保留或贴 surface-dark；按钮 coral。
- [ ] `.err` 错误色 → 用系统 `--error #c64545`（比现在的 ambition 红更准）。
- [ ] `.thinking` 圆点 → coral。

## 6. 红线（一行都不碰）

舞台全套编排（`arenaLineup/Send/Join/Argue/Turning/Verdict/Sit` 等）、`verdictLine` 文案与议题正则、focus 计时、`html2canvas` 导出（其底色取 `body` 背景，换奶油后自动一致）、所有 `/api/*` 调用、`?demo/?replay` 逻辑、`prefers-reduced-motion` 与移动端断点的**行为**（只调里面的颜色，不动结构）。

## 7. 推进顺序（先出两屏眼校，认可再铺）

- [ ] **第 1 步**：§2 token 层 + §4 body/字体/噪点（地基）。
- [ ] **第 2 步**：立题 + 转场 → 截图眼校（最能看出"变 Claude"）。
- [ ] **第 3 步**：建议书 → 截图眼校（编辑部纪要感）。
- [ ] → 用户认可后：地牢 + 卡片 → 自陈 → 会议暗卡（§3 + §5 查项）。
- [ ] **最后**：全流程回归。

## 8. 验收（视觉 + 不回归）

- [ ] 盲看三件套到位：暖奶油底 + 珊瑚 CTA + 衬线文气标题；**会议是一张深蓝暗卡**浮在奶油上。
- [ ] 6 人格色在奶油 / 暗卡两种底上都可辨、不打架（teal/玫红/砖红/桃/石板蓝/雾紫）。
- [ ] 奶油屏正文/标题对比度过 WCAG AA（ink on canvas ✓；注意 muted 小字别太淡）。
- [ ] 全流程跑通：立题→地牢插话→卡片翻面→自陈→三幕会议（舞台动效如常）→裁决→建议书。
- [ ] 导出 PNG 底色随之变奶油、版面完整。
- [ ] 移动端（≤560px）+ reduced-motion 两条路径无破版。
- [ ] **性能红线不回归**（换肤不应影响）：首条插话 <2s、完整会议 ≤90s。
