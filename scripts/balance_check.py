"""阶段2步骤1：三节点矩阵配平校验。

① 覆盖性：每人格在全矩阵的总 delta（理论上限），目标 6-9。
② 多样性：枚举 27 条选择路径，统计最高分人格分布——无单一人格占 20+ 条、无人格 0 胜。
"""
import itertools

import constants as C


def coverage():
    tot = {p: 0 for p in C.PERSONAS}
    for node in C.NODES.values():
        for ch in node["choices"].values():
            for p, v in ch["delta"].items():
                tot[p] += v
    return tot


def diversity():
    nodes = list(C.NODES.values())
    win = {p: 0 for p in C.PERSONAS}
    ties = 0
    for combo in itertools.product(*[list(n["choices"].values()) for n in nodes]):
        scores = {p: 0 for p in C.PERSONAS}
        for ch in combo:
            for p, v in ch["delta"].items():
                scores[p] += v
        mx = max(scores.values())
        winners = [p for p in C.PERSONAS if scores[p] == mx]
        if len(winners) > 1:
            ties += 1
        win[winners[0]] += 1  # 平局归第一个；ties 单独报
    return win, ties


def main():
    print("=== ① 覆盖性（每人总 delta，目标 6-9）===")
    cov = coverage()
    ok_cov = True
    for p in C.PERSONAS:
        v = cov[p]
        flag = "" if 6 <= v <= 9 else f"  ⚠ 不在 6-9"
        if not (6 <= v <= 9):
            ok_cov = False
        print(f"  {p:<9}{v:>2}  {'█'*v}{flag}")

    print("\n=== ② 多样性（27 路径最高分人格分布）===")
    win, ties = diversity()
    ok_div = True
    for p in C.PERSONAS:
        c = win[p]
        flag = ""
        if c >= 20:
            flag = "  ⚠ 占 20+ 条（趋同）"; ok_div = False
        if c == 0:
            flag = "  ⚠ 0 胜（测不出）"; ok_div = False
        print(f"  {p:<9}{c:>2}/27  {'█'*c}{flag}")
    print(f"  含平局路径: {ties}/27")

    print("\n=== 结论 ===")
    print(f"  覆盖性: {'通过' if ok_cov else '不通过——调 delta'}")
    print(f"  多样性: {'通过' if ok_div else '不通过——调 delta'}")
    return ok_cov and ok_div


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
