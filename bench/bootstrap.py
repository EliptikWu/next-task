"""95% CI of the per-PR saving (bootstrap by session: resamples whole sessions, not tasks,
so the sample is not inflated by the 100+ tasks of one long session).

Usage: python -I bootstrap.py "A=a.json" "B=b.json" "both=a.json,b.json"
Each argument is `label=file.json[,file2.json]` (files written by measure.py); one row
group is printed per label. Saving = 1 - (one-task cost / chained cost).
"""
import json
import random
import sys

K = 2.85e-6
random.seed(1)


def groups(paths):
    single, chained = [], []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            sessions = json.load(fh)
        for f in sessions:
            n = len(f['created_ts'])
            if not n:
                continue
            c = (f['units_main'] + f['units_sub']) * K
            ctx = f['mean_context']
            if n == 1 and f['compactions'] == 0:
                single.append((c, 1, ctx))
            elif n >= 3:
                chained.append((c, n, ctx))
    return single, chained


def ratio(single, chained, i):
    a = sum(x[i] if i == 0 else x[i] * x[1] for x in single) / sum(x[1] for x in single)
    b = sum(x[i] if i == 0 else x[i] * x[1] for x in chained) / sum(x[1] for x in chained)
    return 1 - a / b


def main():
    specs = []
    for arg in sys.argv[1:]:
        label, _, files = arg.partition("=")
        if not files:
            sys.exit(f"bad argument {arg!r}: expected label=file.json[,file2.json]")
        specs.append((label, files.split(",")))
    if not specs:
        sys.exit(__doc__)
    for label, paths in specs:
        single, chained = groups(paths)
        for i, what in ((0, 'cost per PR'), (2, 'context per call')):
            obs = ratio(single, chained, i)
            bs = sorted(ratio(random.choices(single, k=len(single)), random.choices(chained, k=len(chained)), i) for _ in range(5000))
            print(f"{label:12s} {what:21s} saving {obs*100:5.1f} %  95% CI [{bs[125]*100:5.1f} %, {bs[4875]*100:5.1f} %]  "
                  f"(one task: {len(single)} sess.; chained: {len(chained)} sess., {sum(x[1] for x in chained)} PRs)")


if __name__ == "__main__":
    main()
