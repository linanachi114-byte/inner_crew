"""手绘六人格像素 sprite(占位素材) → static/sprites/<id>.png

无第三方依赖:纯标准库(zlib)手写 PNG 编码器,程序化绘制。
定位:可替换的占位素材——等用 docs/persona-sprite-prompts.md 出了正图,同名 PNG 覆盖即可,前端不用改。
跑:  PYTHONPATH=. python scripts/gen_sprites.py
"""
import os, zlib, struct

W, H = 28, 34
OUT = os.path.join(os.path.dirname(__file__), "..", "static", "sprites")

# —— 公共调色 ——
OUTLINE = (34, 28, 40, 255)
SKIN    = (233, 200, 166, 255)
SKIN_SH = (201, 166, 134, 255)
EYE     = (40, 30, 42, 255)
WHITE   = (242, 238, 228, 255)
STEEL   = (203, 211, 219, 255)
STEEL_D = (120, 130, 142, 255)
STAR    = (242, 205, 92, 255)
HEART   = (201, 72, 92, 255)
T = (0, 0, 0, 0)

# —— 六人格主色(与前端 --xxx 一致) ——
PERSONAS = {
    "ambition": (192, 70, 59),    # 砖红
    "guardian": (108, 143, 179),  # 钢蓝
    "empath":   (210, 155, 140),  # 暖玫瑰
    "selfcore": (177, 90, 134),   # 梅紫
    "logician": (87, 176, 155),   # 青绿
    "dreamer":  (154, 143, 214),  # 薰衣草
}


def shade(c, f):
    return tuple(min(255, max(0, int(ch * f))) for ch in c[:3]) + (255,)


def write_png(path, grid):
    raw = bytearray()
    for row in grid:
        raw.append(0)  # filter type 0
        for (r, g, b, a) in row:
            raw += bytes((r, g, b, a))

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)  # RGBA 8-bit
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


class Canvas:
    def __init__(self):
        self.g = [[T for _ in range(W)] for _ in range(H)]

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H and c[3]:
            self.g[int(y)][int(x)] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.px(x, y, c)

    def disc(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.px(x, y, c)


def draw_figure(main, prop):
    c = Canvas()
    main = tuple(main[:3]) + (255,)   # 补 alpha
    D = shade(main, 0.68)   # 暗部
    L = shade(main, 1.22)   # 亮部
    cx = 12

    # —— 头(朝右:眼睛偏右) ——
    c.disc(cx, 9, 6, OUTLINE)      # 描边
    c.disc(cx, 9, 5, SKIN)
    # 头发帽(主色暗)盖住上半
    for y in range(3, 9):
        for x in range(cx - 5, cx + 6):
            if (x - cx) ** 2 + (y - 9) ** 2 <= 25 and y <= 7:
                c.px(x, y, D)
    c.px(cx + 3, 8, EYE); c.px(cx + 3, 9, EYE)   # 眼
    c.px(cx + 4, 11, SKIN_SH)                      # 下巴阴影

    # —— 斗篷/身体(梯形,facing right 右侧偏亮) ——
    for y in range(15, 31):
        hw = min(9, 4 + (y - 15) * 0.42)
        x0, x1 = int(cx - hw), int(cx + hw)
        c.px(x0 - 1, y, OUTLINE); c.px(x1 + 1, y, OUTLINE)   # 侧描边
        for x in range(x0, x1 + 1):
            col = main
            if x <= x0 + 1:
                col = D
            elif x >= x1 - 1:
                col = L
            elif x == cx + 1:
                col = L
            c.px(x, y, col)
    c.rect(cx - 9, 31, cx + 9, 31, OUTLINE)  # 底边描边(粗略)

    # —— 腿/脚 ——
    c.rect(cx - 4, 31, cx - 1, 33, OUTLINE)
    c.rect(cx + 1, 31, cx + 4, 33, OUTLINE)

    # —— 肩/手臂(主色暗) ——
    c.rect(cx - 7, 16, cx - 5, 22, D)
    c.rect(cx + 5, 16, cx + 7, 22, L)
    c.disc(cx + 7, 22, 1, SKIN)   # 右手

    prop(c, cx, main, D, L)
    return c.g


# —————————————— 各人格专属道具 ——————————————
def p_ambition(c, cx, main, D, L):   # 高举短剑
    x = cx + 9
    c.rect(x - 1, 3, x + 1, 16, OUTLINE)
    c.rect(x, 4, x, 15, STEEL)            # 剑身
    c.rect(x - 3, 15, x + 3, 16, shade((150, 110, 60), 1))  # 护手
    c.rect(x, 16, x, 19, shade((120, 85, 50), 1))           # 剑柄


def p_guardian(c, cx, main, D, L):   # 圆盾
    gx, gy = cx + 7, 21
    c.disc(gx, gy, 5, OUTLINE)
    c.disc(gx, gy, 4, L)
    c.disc(gx, gy, 2, shade(main, 0.85))
    c.rect(gx, gy - 3, gx, gy + 3, WHITE)   # 盾纹十字
    c.rect(gx - 3, gy, gx + 3, gy, WHITE)


def p_empath(c, cx, main, D, L):     # 掌心小爱心
    hx, hy = cx + 9, 18
    for (dx, dy) in [(-1, 0), (0, 0), (1, 0), (-2, -1), (-1, -1),
                     (1, -1), (2, -1), (-1, 1), (0, 1), (1, 1), (0, 2)]:
        c.px(hx + dx, hy + dy, HEART)


def p_selfcore(c, cx, main, D, L):   # 垂下的空白面具
    mx, my = cx + 8, 24
    c.disc(mx, my, 3, OUTLINE)
    c.disc(mx, my, 2, WHITE)
    c.px(mx - 1, my, EYE); c.px(mx + 1, my, EYE)   # 面具眼孔


def p_logician(c, cx, main, D, L):   # 摊开的账本
    bx, by = cx + 4, 19
    c.rect(bx - 1, by - 1, bx + 7, by + 6, OUTLINE)
    c.rect(bx, by, bx + 2, by + 5, WHITE)          # 左页
    c.rect(bx + 4, by, bx + 6, by + 5, WHITE)      # 右页
    c.rect(bx + 3, by, bx + 3, by + 5, shade((150, 110, 60), 1))  # 书脊
    for yy in (by + 1, by + 3):
        c.rect(bx, yy, bx + 2, yy, STEEL_D)
        c.rect(bx + 4, yy, bx + 6, yy, STEEL_D)


def p_dreamer(c, cx, main, D, L):    # 上方的星
    sx, sy = cx + 8, 5
    for (dx, dy) in [(0, -2), (0, -1), (-1, 0), (0, 0), (1, 0),
                     (0, 1), (-2, 0), (2, 0), (-1, 1), (1, 1)]:
        c.px(sx + dx, sy + dy, STAR)
    c.px(sx - 4, sy + 3, STAR); c.px(sx + 4, sy - 3, WHITE)  # 闪点


PROPS = {
    "ambition": p_ambition, "guardian": p_guardian, "empath": p_empath,
    "selfcore": p_selfcore, "logician": p_logician, "dreamer": p_dreamer,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for pid, color in PERSONAS.items():
        grid = draw_figure(color, PROPS[pid])
        path = os.path.join(OUT, f"{pid}.png")
        write_png(path, grid)
        print("wrote", os.path.relpath(path))


if __name__ == "__main__":
    main()
