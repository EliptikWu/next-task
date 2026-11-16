# Backlog format

Read this only when the project has no backlog yet, or the user asks how to set one up.

`BACKLOG.md` at the repository root, three sections, in this order:

```markdown
# Backlog

## Next
- [ ] Fix the off-by-one in pagination (#41)
- [ ] Add rate limiting to /login
- [ ] Split users.py (over 800 lines): first the auth helpers

## Waiting on a human
- [ ] Rotate the staging API key (needs dashboard access)
- [ ] Decide: keep or drop the CSV export

## Done
- [x] Cache the settings query — PR #38 — settings are read in middleware.py, not views
- [x] Upgrade the test runner — PR #39 — none
```

Rules that keep it cheap to read:

- **One line per item.** Detail lives in the issue or PR the line links to.
- **`## Next` is ordered**: the top unchecked item is the next task. Reorder it to steer.
- **`## Done` lines are handoffs**: the third field is the one thing the next session
  should know (a gotcha, where something really lives, a decision). `none` is fine.
- **`## Done` is capped at 20 lines**; older ones move to `docs/backlog-archive.md`,
  which nobody reads unless they need history.
- Items for a human go under `## Waiting on a human`, so the loop never touches them.

To point the skill at a different file or at GitHub issues, add one line to the project's instructions file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`...):

```markdown
Backlog: docs/roadmap.md
```

or

```markdown
Backlog: GitHub issues, label "ready"
```

To let the skill merge its own PRs when checks are green, the instructions file must say so
explicitly, for example:

```markdown
/next-task may merge its own PRs once all checks pass.
```
