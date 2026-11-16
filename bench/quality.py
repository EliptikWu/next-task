"""Quality of PRs: one-task sessions versus chained sessions.

For each PR created in a session (from the transcripts) and its history on GitHub:
- merged, or closed without merging;
- reverted (a later PR titled "Revert ..." that names it);
- 7-day rework: a later `fix...` PR that touches any of its code files
  (excluding .md, docs/, cerebro/, lockfiles, .claude/, CHANGELOG, contract/) within the next 7 days;
- verified: tests, typecheck, lint or build ran in its segment before the PR was created;
- reviewed: code-review/security-review (skill or subagent) ran in its segment;
- size: changed lines.

Usage: python -I quality.py sessions1.json:gh_prs1.json:owner/repo [sessions2.json:gh_prs2.json:owner/repo ...]
  sessions*.json  written by measure.py
  gh_prs*.json    `gh pr list --repo owner/repo --state all --limit 1000 --json number,title,createdAt,mergedAt,state,additions,deletions,files`
  owner/repo      only PRs created in that repository are counted for that argument; several
                  can be given comma-separated, and a bare `repo` name (no owner) matches any owner
(paths must not contain ':'; use relative paths on Windows)
"""
import json
import random
import re
import statistics as st
import sys
from datetime import datetime, timedelta

random.seed(1)
NON_CODE = re.compile(r"(\.md$|^docs/|^cerebro/|lock\.json$|\.lock$|^\.claude/|CHANGELOG|^contract/)", re.I)


def parse_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load(arg):
    sessions_path, gh_path, repo = arg.rsplit(":", 2)
    with open(sessions_path, encoding="utf-8") as fh:
        sessions = json.load(fh)
    with open(gh_path, encoding="utf-8") as fh:
        prs = {p["number"]: p for p in json.load(fh)}
    return sessions, prs, [r.lower() for r in repo.split(",")]


def tasks(sessions, prs, repos):
    rows = []
    ordered = sorted(prs.values(), key=lambda p: p["createdAt"])
    for f in sessions:
        created = [(t, n) for t, r, n in f["created_pr"] if n in prs and (r.lower() in repos or r.split("/")[1].lower() in repos)]
        if not created:
            continue
        n_ses = len(f["created_ts"])
        if n_ses == 1 and f["compactions"] == 0:
            group = "single"
        elif n_ses >= 3:
            group = "chained"
        else:
            continue
        prev = ""
        for t, n in created:
            p = prs[n]
            ev = [k for (te, k) in f["events"] if prev < te <= t]
            prev = t
            code = {x["path"] for x in p.get("files") or [] if not NON_CODE.search(x["path"])}
            begin = parse_date(p["createdAt"])
            end = begin + timedelta(days=7)
            rework = False
            reverted = False
            for q in ordered:
                cq = parse_date(q["createdAt"])
                if cq <= begin:
                    continue
                if re.match(r"revert", q["title"], re.I) and (f"#{n}" in q["title"] or p["title"][:40] in q["title"]):
                    reverted = True
                if cq <= end and re.match(r"(fix|hotfix)", q["title"], re.I) and code & {x["path"] for x in q.get("files") or []}:
                    rework = True
            rows.append({
                "session": f["id"], "group": group, "pr": n,
                "merged": bool(p["mergedAt"]), "closed": p["state"] == "CLOSED",
                "reverted": reverted, "rework": rework, "has_code": bool(code),
                "verified": "tests" in ev, "reviewed": "review" in ev,
                "lines": p["additions"] + p["deletions"],
            })
    return rows


def rate(g, k):
    return sum(x[k] for x in g) / len(g) if g else float("nan")


def ci(rows, k, sub=None):
    """95% CI of the difference (chained - one task) resampling sessions."""
    by = {}
    for x in rows:
        if sub and not x[sub]:
            continue
        by.setdefault((x["group"], x["session"]), []).append(x)
    single = [v for (g, _), v in by.items() if g == "single"]
    chained = [v for (g, _), v in by.items() if g == "chained"]
    if not single or not chained:
        return float("nan"), float("nan")
    diffs = []
    for _ in range(3000):
        a = [x for s in random.choices(single, k=len(single)) for x in s]
        b = [x for s in random.choices(chained, k=len(chained)) for x in s]
        diffs.append(rate(b, k) - rate(a, k))
    diffs.sort()
    return diffs[75], diffs[2925]


def report(name, rows):
    print(f"\n== {name}")
    single = [x for x in rows if x["group"] == "single"]
    chained = [x for x in rows if x["group"] == "chained"]
    print(f"  PRs: one task {len(single)}, chained {len(chained)}")
    print(f"  changed lines (median): one task {st.median([x['lines'] for x in single]):.0f}, "
          f"chained {st.median([x['lines'] for x in chained]):.0f}")
    for k, label, sub in (("merged", "merged", None), ("reverted", "reverted", None),
                          ("rework", "with 7-day rework (PRs with code)", "has_code"),
                          ("verified", "with tests/typecheck before the PR", None),
                          ("reviewed", "with code review before the PR", None)):
        a = [x for x in single if not sub or x[sub]]
        b = [x for x in chained if not sub or x[sub]]
        lo, hi = ci(rows, k, sub)
        print(f"  {label:42s} one task {rate(a, k)*100:5.1f} %  chained {rate(b, k)*100:5.1f} %  "
              f"(diff. chained-one 95% CI [{lo*100:+.1f}, {hi*100:+.1f}] pts)")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    everything = []
    for arg in sys.argv[1:]:
        s, p, repos = load(arg)
        f = tasks(s, p, repos)
        report(arg, f)
        everything += f
    report("all combined", everything)


if __name__ == "__main__":
    main()
