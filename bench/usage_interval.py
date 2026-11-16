"""Weighted tokens of all sessions (all projects, subagents included) between two /usage
readings, to turn estimated cost into a % of the subscription limit.

Usage: python -I usage_interval.py [usage_readings.jsonl]
(default: usage_readings.jsonl next to this script)

Recording a reading: run `/usage` in Claude Code before and after a work period and
append one JSON line per reading to the readings file:
  {"ts": "2026-01-15T09:00:00-05:00", "seven_day": 42, "seven_day_resets": "2026-01-19T12:00:00Z"}
  ts                ISO 8601 time of the reading (with UTC offset)
  seven_day         % of the 7-day window used, as shown by /usage
  seven_day_resets  the reset time shown by /usage (readings with different values are
                    not compared, because the window restarted in between)
For each pair of consecutive readings with the same weekly reset it prints: points the
7-day window rose, equivalent USD (weights 1/1.25/2/0.1/5 x 2.85e-6) and points per USD.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

K = 2.85e-6
PROJECTS = Path.home() / ".claude" / "projects"


def units(u):
    cc = u.get("cache_creation") or {}
    h1 = cc.get("ephemeral_1h_input_tokens") or 0
    m5 = (u.get("cache_creation_input_tokens") or 0) - h1
    return ((u.get("input_tokens") or 0) + 1.25 * m5 + 2 * h1
            + 0.1 * (u.get("cache_read_input_tokens") or 0) + 5 * (u.get("output_tokens") or 0))


def calls_between(since, until):
    seen, per_project = set(), {}
    for f in PROJECTS.rglob("*.jsonl"):
        if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < since:
            continue
        for line in f.open(encoding="utf-8", errors="replace"):
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = d.get("message") or {}
            if d.get("type") != "assistant" or not m.get("usage") or not d.get("timestamp"):
                continue
            ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
            key = d.get("requestId") or m.get("id")
            if not (since <= ts < until) or key in seen:
                continue
            seen.add(key)
            p = f.relative_to(PROJECTS).parts[0]
            per_project[p] = per_project.get(p, 0) + units(m["usage"])
    return per_project


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("usage_readings.jsonl")
    readings = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for a, b in zip(readings, readings[1:]):
        if a["seven_day_resets"] != b["seven_day_resets"]:
            print(f"{a['ts']} -> {b['ts']}: the week reset, not used")
            continue
        since = datetime.fromisoformat(a["ts"]).astimezone(timezone.utc)
        until = datetime.fromisoformat(b["ts"]).astimezone(timezone.utc)
        pp = calls_between(since, until)
        usd = sum(pp.values()) * K
        pts = b["seven_day"] - a["seven_day"]
        print(f"{a['ts']} -> {b['ts']}: +{pts} weekly pts, {usd:.2f} USD equivalent"
              + (f", {pts / usd:.3f} pts/USD" if usd else ""))
        for p, u in sorted(pp.items(), key=lambda x: -x[1]):
            print(f"    {p:30s} {u * K:7.2f} USD")


if __name__ == "__main__":
    main()
