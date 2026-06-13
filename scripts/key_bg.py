"""把生图模型在纯色底上画的角色，抠成真·透明 RGBA PNG → static/sprites/<id>.png

为什么需要它:GPT/Gemini 只输出 RGB、给不了 alpha，"透明背景"会被画成灰白棋盘格。
对策:让模型在纯色实心底(绿 #00FF00,计算师用品红 #FF00FF)上画，这里从四角洪水填充
扣掉那层纯色底(只扣与边缘连通的背景,不误伤角色内部同色像素)，并做边缘去色溢(despill)。

用法:
  .venv/bin/python scripts/key_bg.py <输入图> <persona_id> [--chroma green|magenta|white|auto] [--tol 50]
例:
  .venv/bin/python scripts/key_bg.py ~/Downloads/guardian_raw.png guardian
  .venv/bin/python scripts/key_bg.py ~/Downloads/logician_raw.png logician --chroma magenta
"""
import argparse, os, sys
from collections import deque
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), "..", "static", "sprites")
IDS = {"ambition", "guardian", "empath", "selfcore", "logician", "dreamer"}
CHROMA = {"green": (0, 255, 0), "magenta": (255, 0, 255), "white": (255, 255, 255)}


def pick_bg(px, w, h, mode):
    if mode != "auto":
        return CHROMA[mode]
    # 四角取样的众数近似:直接取左上角
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    return tuple(corners[0][:3])


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def despill(c, chroma):
    r, g, b = c[0], c[1], c[2]
    if chroma == (0, 255, 0):          # 绿溢:把过亮的绿压到 r、b 的较大值
        g = min(g, max(r, b))
    elif chroma == (255, 0, 255):      # 品红溢:把 r、b 压到 g 附近
        r = min(r, max(g, int((g + b) / 2)))
        b = min(b, max(g, int((g + r) / 2)))
    return (r, g, b)


def key(inp, pid, mode, tol):
    img = Image.open(inp).convert("RGBA")
    w, h = img.size
    px = img.load()
    bg = pick_bg(px, w, h, mode)
    chroma = CHROMA.get(mode if mode in CHROMA else "green")
    if mode == "auto":
        chroma = bg
    tol2 = tol * tol

    # —— 从四角洪水填充,只清与边界连通的背景 ——
    seen = bytearray(w * h)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            dq.append((x, y))
    cleared = 0
    while dq:
        x, y = dq.popleft()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, a = px[x, y]
        if dist2((r, g, b), bg) > tol2:
            continue  # 不是背景,边界到此为止
        px[x, y] = (r, g, b, 0)
        cleared += 1
        if x > 0: dq.append((x - 1, y))
        if x < w - 1: dq.append((x + 1, y))
        if y > 0: dq.append((x, y - 1))
        if y < h - 1: dq.append((x, y + 1))

    # —— 边缘去色溢 + 半透明软化 ——
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            d2 = dist2((r, g, b), bg)
            if d2 < (tol * 1.6) ** 2:           # 贴近背景色的边缘像素
                nr, ng, nb = despill((r, g, b), chroma)
                aa = int(255 * min(1.0, d2 ** 0.5 / (tol * 1.6)))
                px[x, y] = (nr, ng, nb, aa)

    # —— 按内容裁剪 + 留边 ——
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        pad = max(2, img.width // 16)
        canvas = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        canvas.alpha_composite(img, (pad, pad))
        img = canvas

    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{pid}.png")
    img.save(out)
    print(f"✓ {pid}: 清掉背景 {cleared}px → {os.path.relpath(out)}  ({img.width}x{img.height})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("persona_id")
    ap.add_argument("--chroma", default="green", choices=["green", "magenta", "white", "auto"])
    ap.add_argument("--tol", type=int, default=50, help="背景色匹配容差(颜色不准就调大,如 70)")
    a = ap.parse_args()
    if a.persona_id not in IDS:
        sys.exit(f"persona_id 必须是 {sorted(IDS)} 之一")
    if not os.path.exists(a.input):
        sys.exit(f"找不到输入图:{a.input}")
    key(a.input, a.persona_id, a.chroma, a.tol)


if __name__ == "__main__":
    main()
