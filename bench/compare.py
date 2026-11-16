"""Cost per PR created: one-task sessions versus chained sessions.

Usage: python -I compare.py sessions1.json [sessions2.json ...]   (files written by measure.py)

Cost comes from each call's tokens (Anthropic price weights) times the USD-per-unit
constant K, calibrated against the cost-state of single-process sessions.
"""
import json
import statistics as st
import sys

K = 2.85e-6  # USD per unit; median calibrated on two projects (2.79 and 2.85)


def med(x):
    return st.median(x) if x else float('nan')


def usd(f):
    return (f['units_main'] + f['units_sub']) * K


for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as fh:
        F = [f for f in json.load(fh) if f['created_ts']]
    single = [f for f in F if len(f['created_ts']) == 1 and f['compactions'] == 0]
    chained = [f for f in F if len(f['created_ts']) >= 3]
    print(f"\n== {path}")
    for label, g in (('one task', single), ('chained (>=3 PRs created)', chained)):
        n = sum(len(f['created_ts']) for f in g)
        tot = sum(usd(f) for f in g)
        print(f"  {label}: {len(g)} sessions, {n} PRs, aggregate USD/PR {tot/n:.2f}, median per session {med([usd(f)/len(f['created_ts']) for f in g]):.2f}, "
              f"median of mean context/call {med([f['mean_context'] for f in g])/1000:.0f}k")
    print("  chained detail: PRs created | USD (tokens) | USD/PR | mean context | /compact")
    for f in sorted(chained, key=lambda f: -len(f['created_ts'])):
        n = len(f['created_ts'])
        print(f"    {n:4d} | {usd(f):8.0f} | {usd(f)/n:6.2f} | {f['mean_context']/1000:4.0f}k | {f['compactions']}")
    # Segments within chained sessions: cost of task k (between created PRs)
    pos = {}
    for f in chained:
        cuts = f['created_ts']
        seg = [0.0] * len(cuts)
        ctxs = [[] for _ in cuts]
        for t, u in sorted(f['series'] + f['series_sub']):
            j = next((j for j, c in enumerate(cuts) if t <= c), None)
            if j is None:
                break
            seg[j] += u
        for (t, _), c in zip(sorted(f['series']), f['contexts']):
            j = next((j for j, c_ in enumerate(cuts) if t <= c_), None)
            if j is not None:
                ctxs[j].append(c)
        for j in range(len(cuts)):
            b = 1 if j == 0 else 2 if j == 1 else 3 if j < 5 else 4 if j < 10 else 5 if j < 20 else 6
            pos.setdefault(b, ([], []))
            pos[b][0].append(seg[j] * K)
            if ctxs[j]:
                pos[b][1].append(st.mean(ctxs[j]))
    names = {1: '1st', 2: '2nd', 3: '3rd-5th', 4: '6th-10th', 5: '11th-20th', 6: '21st+'}
    print("  task by position in the chain: n | mean USD | median USD | mean context")
    for b in sorted(pos):
        c, x = pos[b]
        print(f"    {names[b]:9s} {len(c):4d} | {st.mean(c):6.2f} | {med(c):6.2f} | {med(x)/1000:4.0f}k")
