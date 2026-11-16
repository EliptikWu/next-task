<img src=".claude-plugin/icon.png" width="96" alt="">

# next-task

[Leer en español](README.es.md)

A Claude Code skill for working through a backlog **one task per session**. Each session it
picks the next item and takes it to a verified pull request. It leaves a one-line handoff
in the repo, then tells you to type `/clear` and `/next-task` again.

You type two commands. Each task costs 60 % fewer tokens, without skipping tests or review.

## Measured savings

These numbers come from 561 real pull requests in two production projects:

- [LK Creator](https://lkcreator.com), a FastAPI + Next.js SaaS that converts custom
  Minecraft content.
- ISO 21101 turismo, a safety-management web app for adventure-tourism operators.

The data is the token usage that Claude Code already stores in its local session
transcripts. Same developer, same model (Claude Opus), November 2026.

| | One task per session | Chained tasks (≥3 PRs in one session) | Savings (95 % CI) |
|---|---|---|---|
| Cost per PR, LK Creator | $4.39 (162 PRs) | $14.58 (131 PRs) | **70 %** (37–72 %) |
| Cost per PR, ISO 21101 turismo | $5.10 (49 PRs) | $9.63 (219 PRs) | **47 %** (18–78 %) |
| **Cost per PR, both** | | | **60 %** (42–74 %) |
| **Context per model call, both** | 123–130k tokens | 342–357k tokens | **73 %** (62–75 %) |

**On a subscription.** We read `/usage` three times, around two work periods, and
summed the tokens of every session in between, across all projects and including
subagents.

- One point of the weekly limit cost $17.4 of API-equivalent tokens: 11 points in total,
  0.059 and 0.057 points per dollar in the two periods.
- `/usage` rounds to whole points, so this figure is ±9 %.
- So one task per session uses about **0.25–0.29 % of the weekly limit per PR**. Chaining
  tasks uses **0.55–0.84 %**. That is roughly **twice as many PRs per week** on the same
  plan.

**Why it works.** Every model call re-reads the whole conversation. In a chained session
the context per call keeps growing; it passed 500k tokens after about 10 tasks. So each
later task pays for all the earlier ones. A fresh session starts every task with the same
small context.

### Quality: no worse, and the safety steps actually happen

We joined the first 510 of these PRs with their GitHub history:

| | One task per session | Chained | Difference (95 % CI) |
|---|---|---|---|
| Merged | 98.2 % | 98.6 % | none (−3.5 to +3.1 pts) |
| Reverted later | 0 % | 0 % | none |
| Tests / typecheck run before opening the PR | **97.6 %** | 75.1 % | 22.5 pts more (2 to 38) |
| Code review run before opening the PR | **87.9 %** | 14.8 % | 73 pts more (55 to 87) |

In long chained sessions the model quietly starts skipping verification and review as the
context fills up. A fresh session follows the full checklist almost every time.

We also measured "rework within 7 days": a later `fix` PR that touches the same code files.
It favored one task per session on ISO 21101 turismo (8.6 % vs 59.2 %), but it is too
noisy to claim. In these repos a third of all PRs are planned `fix` work on the same
modules, so the combined interval crosses zero.

### Behavior tests

Before release we ran the skill and its previous version on three scripted repos, graded
automatically (scripts in [`tests/`](tests/)):

- **a real bug first:** fix it, one task only;
- **an already-fixed item first:** check the premise, mark it obsolete, move on;
- **no backlog:** offer to create one and don't invent work.

This version passed 19/19 checks with the same token use as the previous one (≈54k per
run). The previous version wrote invented PR numbers into the handoff when there was no
remote, and this version fixes that.

### How it was measured

The scripts are in [`bench/`](bench/).

- **Cost.** We took the tokens of every model call, including subagents, and weighted them
  by Anthropic's price ratios: cache read 0.1×, cache write 1.25× or 2×, output 5×. We
  checked these weights against the cost Claude Code records, and they agree within ±10 %.
- **Task.** A task is a pull request actually created in that session: a `gh pr create`
  that returned a PR URL.
- **Confidence intervals.** We ran a 5,000-sample bootstrap over **sessions**, not tasks.
  That way one long session doesn't count as 100 independent samples.

### Limits, stated plainly

- It's observational, not an A/B test. The tasks in the two groups are different, and the
  chained group has only 11 sessions.
- The dollar figures are API-price equivalents. The subscription figure comes from two
  periods and should be read as an estimate.
- The quality table shows that checks were *run*. It cannot show that each one was run
  well.

### Run it on your own sessions

```bash
python bench/measure.py ~/.claude/projects/<your-project-folder> next-task sessions.json
python bench/compare.py sessions.json
python bench/bootstrap.py "mine=sessions.json"
```

## What it does in each session

0. **Guard.**
   - If this conversation already closed a task, it asks you to `/clear` first.
   - If one of your PRs is still open, it finishes that one first.
   - If the default branch's CI is red, fixing it *is* the task.
1. **Pick.** It takes the first open item of the backlog (`BACKLOG.md`, `TODO.md`, or
   GitHub issues), reading only the part it needs.
2. **Check the premise.** It confirms in the code that the problem still exists, and drops
   items that are already fixed.
3. **Do it.** It finds the root cause and fixes it in the shared mechanism, in the
   surrounding style.
4. **Verify.** It runs the checks CI would run, then reviews the diff.
5. **Open the PR.** It merges only if your CLAUDE.md explicitly allows it, and only when
   checks pass.
6. **Hand off.** It writes one line in the backlog, with the PR number and the one thing
   the next session must know.
7. **Stop.** It tells you to type `/clear`, then `/next-task`.

It follows these token rules throughout:

- the repo is the memory;
- it reads line ranges, not whole files;
- wide searches go to a subagent that answers in under 15 lines;
- every command's output is trimmed;
- it uses CLI tools over MCP;
- it never re-derives a fact it already established;
- it stops after two failed attempts at the same fix;
- compaction is treated as a sign that the task was too big.

It works without a GitHub remote. In that case it commits on a branch and leaves the PR to
you.

It answers in your language; the skill itself is written in English because that's what
the model reads.

## Install

**As a plugin:**

```
/plugin marketplace add EliptikWu/next-task
/plugin install next-task@eliptikwu
```

**Or by hand:** copy `skills/next-task/` to `~/.claude/skills/next-task/` for every
project, or to `<repo>/.claude/skills/next-task/` for one project.

If a project already has its own skill for this loop, that one wins.

No backlog yet? The skill offers to create one. The format is in
[`skills/next-task/reference/backlog-format.md`](skills/next-task/reference/backlog-format.md).

## License

[Apache 2.0](LICENSE). You can use, change and share it. Copies and derived works must
keep the copyright and the [NOTICE](NOTICE) file, and must say what was changed. The
license doesn't grant use of the author's name to promote a derived work.

Made by [EliptikWu](https://github.com/EliptikWu) at LK Industries.
