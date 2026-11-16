"""Grades next-task runs from the facts that collect.sh gathered and each run's final reply.

Usage: python -I grade.py <iteration-dir>
Layout: <iteration-dir>/<case>/<config>/{facts/, outputs/final.md}. Writes grading.json per
run and prints a summary. It only reads files: run collect.sh first.
"""
import json
import re
import sys
from pathlib import Path


def read(path, default=""):
    return path.read_text(encoding="utf-8").strip() if path.exists() else default


def section(text, name):
    m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def grade(case, run):
    facts = run / "facts"
    final = read(run / "outputs" / "final.md")
    br = read(facts / "branch.txt")
    backlog = read(facts / "backlog.md")
    values = json.loads(read(facts / "values.json", "{}"))
    last = ([l for l in final.splitlines() if l.strip()] or [""])[-1]
    done, nxt = section(backlog, "Done"), section(backlog, "Next")
    res = []

    def add(text, ok, evidence):
        res.append({"text": text, "passed": bool(ok), "evidence": str(evidence)[:300]})

    if case in ("normal", "obsolete"):
        add("A next/* branch was created", br, br)
        add("main was not changed (nothing merged)", read(facts / "main_commits.txt") == "1",
            read(facts / "main_commits.txt") + " commits on main")
        add("The project tests pass on the branch", read(facts / "tests.txt") == "pass", read(facts / "tests.txt"))
        add("Last line asks for /clear and /next-task", "/clear" in last and "/next-task" in last, last)
        add("The reply says the PR has to be opened by the user (no remote)",
            re.search(r"no remote|open the PR|PR.*(yourself|manually|for you)|no hay remoto|abrirlo t", final, re.I),
            "")
    if case == "normal":
        add("slugify('Café') returns 'cafe' on the branch", values.get("slugify_cafe") == "cafe", values)
        add("word_count was not touched (one task only)", values.get("word_count_double_space") == 3, values)
        add("The slugify item is a single checked line in ## Done",
            re.search(r"^- \[x\].*slugify", done, re.M | re.I)
            and not re.search(r"- \[ \].*slugify (keeps|drops) accented", nxt, re.I), done)
        add("The handoff line names the branch, not an invented PR number",
            br and br in done and not re.search(r"slugify.*PR #\d", done), done)
    if case == "obsolete":
        add("word_count('a  b') returns 2 on the branch (moved on to the next item)",
            values.get("word_count_double_space") == 2, values)
        add("The already-fixed slugify item is no longer open in ## Next",
            not re.search(r"- \[ \].*slugify (keeps|drops)", nxt, re.I), nxt)
        add("The handoff line does not invent a PR number", not re.search(r"word_count.*PR #\d", done), done)
    if case == "nobacklog":
        add("No code was changed (no invented work)", read(facts / "code_changed.txt") == "no",
            read(facts / "code_changed.txt"))
        add("The reply offers to create a backlog", re.search(r"backlog", final, re.I), final[:300])
    return res


def main():
    it = Path(sys.argv[1])
    for case_dir in sorted(p for p in it.iterdir() if p.is_dir()):
        for run in sorted(p for p in case_dir.iterdir() if (p / "facts").is_dir()):
            exp = grade(case_dir.name, run)
            n = sum(e["passed"] for e in exp)
            (run / "grading.json").write_text(json.dumps({
                "expectations": exp,
                "summary": {"passed": n, "failed": len(exp) - n, "total": len(exp),
                            "pass_rate": round(n / len(exp), 2) if exp else 0}}, indent=1), encoding="utf-8")
            print(f"{case_dir.name:10s} {run.name:11s} {n}/{len(exp)}")
            for e in exp:
                if not e["passed"]:
                    print(f"    FAIL {e['text']} :: {e['evidence'][:120]}")


if __name__ == "__main__":
    main()
