"""Measure per-task (pull request) cost in saved Claude Code sessions.

Usage: python -I measure.py <transcripts folder, e.g. ~/.claude/projects/<project>> <skill1,skill2> [out.json]

Per session: tokens (from the model responses, de-duplicated, subagents included),
cost in USD (the last cost-state Claude Code stores), distinct PRs created or linked,
model calls and mean context per call. Flags whether the session used the given
"one task per session" skill(s). Never prints conversation content.
"""
import json
import re
import sys
from pathlib import Path


def read_jsonl(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def collect_usage(path, calls):
    """Accumulate into `calls` (key -> (timestamp, usage)) the model responses of the file."""
    for o in read_jsonl(path):
        if o.get("type") != "assistant":
            continue
        m = o.get("message") or {}
        u = m.get("usage")
        if not u:
            continue
        key = o.get("requestId") or m.get("id") or o.get("uuid")
        calls[key] = (o.get("timestamp", ""), u)


# Weight of each token type relative to a normal input token (Anthropic pricing:
# cache read 0.1x; 5-minute cache write 1.25x; 1-hour cache write 2x; output 5x).
def units(u):
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5m = (u.get("cache_creation_input_tokens", 0) or 0) - w1h
    return ((u.get("input_tokens", 0) or 0) + 1.25 * w5m + 2 * w1h
            + 0.1 * (u.get("cache_read_input_tokens", 0) or 0) + 5 * (u.get("output_tokens", 0) or 0))


def session(path, skills):
    calls = {}
    collect_usage(path, calls)
    sub = path.with_suffix("")  # folder <id>/subagents
    sub_calls = {}
    for p in sub.glob("subagents/*.jsonl"):
        collect_usage(p, sub_calls)

    prs, cost, start, uses_skill, merges = {}, None, None, False, 0
    compactions = 0
    created, ok_ids = [], {}
    events = []
    TESTS = re.compile(r"pytest|npm (run )?test|vitest|npm run (typecheck|build|test:)|ruff check|pyright|tsc|playwright test|npm run lint")
    pattern = re.compile(r"<command-name>/?(%s)</command-name>" % "|".join(map(re.escape, skills)))
    for o in read_jsonl(path):
        t = o.get("type")
        ts = o.get("timestamp")
        if ts and (start is None or ts < start):
            start = ts
        if t == "pr-link":
            k = (o.get("prRepository"), o.get("prNumber"))
            if k not in prs or ts < prs[k]:
                prs[k] = ts
        elif t == "cost-state":
            cost = o.get("totalCostUSD")
        elif t == "assistant":
            for c in (o.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    cmd = str(inp.get("command", ""))
                    if c.get("name") == "Bash" and TESTS.search(cmd):
                        events.append((ts, "tests"))
                    if c.get("name") == "Skill" and inp.get("skill") in ("code-review", "security-review", "pr-review-toolkit:review-pr", "code-review-skill"):
                        events.append((ts, "review"))
                    if c.get("name") in ("Agent", "Task") and "review" in str(inp.get("subagent_type", "")) + str(inp.get("description", "")).lower():
                        events.append((ts, "review"))
                    if c.get("name") == "Skill" and inp.get("skill") in skills:
                        uses_skill = True
                    if c.get("name") == "Bash" and "gh pr merge" in str(inp.get("command", "")):
                        merges += 1
                    if c.get("name") == "Bash" and "gh pr create" in str(inp.get("command", "")):
                        created.append((ts, c.get("id")))
        elif t == "user" and isinstance((o.get("message") or {}).get("content"), list):
            for c in o["message"]["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    txt = json.dumps(c.get("content"))
                    hits = re.findall(r"github\.com/([^/\s\\\"]+/[^/\s\\\"]+)/pull/(\d+)", txt)
                    if hits and not c.get("is_error"):
                        ok_ids[c.get("tool_use_id")] = (hits[-1][0], int(hits[-1][1]))
        if t == "user":
            content = (o.get("message") or {}).get("content")
            if isinstance(content, str):
                if pattern.search(content):
                    uses_skill = True
                if "<command-name>/compact</command-name>" in content:
                    compactions += 1

    def total(dic):
        r = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "calls": len(dic)}
        for _, u in dic.values():
            r["input"] += u.get("input_tokens", 0) or 0
            r["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
            r["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
            r["output"] += u.get("output_tokens", 0) or 0
        return r

    main_tokens, sub_tokens = total(calls), total(sub_calls)
    contexts = [
        (u.get("input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)
        + (u.get("cache_read_input_tokens", 0) or 0)
        for _, u in sorted(calls.values(), key=lambda x: x[0])
    ]
    return {
        "id": path.stem,
        "start": start,
        "skill": uses_skill,
        "prs": len(prs),
        "merges": merges,
        "cost_usd": cost,
        "main": main_tokens,
        "subagents": sub_tokens,
        "mean_context": sum(contexts) / len(contexts) if contexts else 0,
        "max_context": max(contexts) if contexts else 0,
        "contexts": contexts,
        "compactions": compactions,
        "events": sorted(events),
        "created_ts": sorted(t for t, i in created if i in ok_ids),
        "created_pr": sorted((t, *ok_ids[i]) for t, i in created if i in ok_ids),
        "pr_ts": sorted(prs.values()),
        "units_main": sum(units(u) for _, u in calls.values()),
        "units_sub": sum(units(u) for _, u in sub_calls.values()),
        "series": [(t, units(u)) for t, u in sorted(calls.values(), key=lambda x: x[0])],
        "series_sub": [(t, units(u)) for t, u in sorted(sub_calls.values(), key=lambda x: x[0])],
    }


def main():
    folder = Path(sys.argv[1]).expanduser()
    skills = sys.argv[2].split(",")
    out = sys.argv[3] if len(sys.argv) > 3 else None
    rows = [session(p, skills) for p in sorted(folder.glob("*.jsonl"))]
    rows = [f for f in rows if f["main"]["calls"] > 0]
    if out:
        Path(out).write_text(json.dumps(rows), encoding="utf-8")
    print(f"sessions with calls: {len(rows)}; with skill: {sum(f['skill'] for f in rows)}; "
          f"with PR: {sum(1 for f in rows if f['prs'])}; with cost: {sum(1 for f in rows if f['cost_usd'] is not None)}")


if __name__ == "__main__":
    main()
