"""试炼题库健康检查。

① 阶段覆盖：open/relation/vision/pressure/close 每段至少 2 题。
② 抽样组卷：随机抽 200 套 5 题，统计每人格 delta 覆盖与最高分分布。
"""
import itertools

import constants as C


def stage_counts():
    out = {stage: 0 for stage in C.TRIAL_STAGE_SEQUENCE}
    for node in C.NODES.values():
        stage = node.get("stage")
        if stage in out:
            out[stage] += 1
    return out


def score_combo(nodes, combo):
    scores = {p: 0 for p in C.PERSONAS}
    for node, choice_id in zip(nodes, combo):
        ch = node["choices"][choice_id]
        for p, v in ch["delta"].items():
            scores[p] += v
    return scores


def sampled_diversity(samples=200):
    coverage = {p: 0 for p in C.PERSONAS}
    wins = {p: 0 for p in C.PERSONAS}
    ties = 0
    for _ in range(samples):
        order = C.select_trial_order()
        nodes = [C.NODES[nid] for nid in order]
        # 每套题枚举 3^5=243 条路径；200 套约 4.8 万路径，足够快。
        for combo in itertools.product(*[list(n["choices"]) for n in nodes]):
            scores = score_combo(nodes, combo)
            for p, v in scores.items():
                coverage[p] += v
            mx = max(scores.values())
            winners = [p for p in C.PERSONAS if scores[p] == mx]
            ties += len(winners) > 1
            wins[winners[0]] += 1
    return coverage, wins, ties


def main():
    print("=== ① 阶段覆盖（每段至少 2 题）===")
    stages = stage_counts()
    ok_stage = True
    for stage in C.TRIAL_STAGE_SEQUENCE:
        count = stages.get(stage, 0)
        ok = count >= 2
        ok_stage = ok_stage and ok
        print(f"  {stage:<9}{count:>2}  {'✓' if ok else '⚠'}")

    print("\n=== ② 抽样组卷多样性（200 套 × 243 路径）===")
    coverage, wins, ties = sampled_diversity()
    ok_div = True
    for p in C.PERSONAS:
        win = wins[p]
        ok = win > 0
        ok_div = ok_div and ok
        print(f"  {p:<9}win={win:>5}  coverage={coverage[p]:>6}  {'✓' if ok else '⚠ 0 胜'}")
    print(f"  含平局路径: {ties}")

    print("\n=== 结论 ===")
    print(f"  阶段覆盖: {'通过' if ok_stage else '不通过——补题'}")
    print(f"  多样性: {'通过' if ok_div else '不通过——调 delta'}")
    return ok_stage and ok_div


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
