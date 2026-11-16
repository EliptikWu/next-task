#!/usr/bin/env bash
# Collects what grade.py needs from every run after the skill has run.
# Usage: bash tests/collect.sh <iteration-dir>
# For each <iteration-dir>/<case>/<config>/repo it writes <config>/facts/:
#   branch.txt        the last next/* branch, or empty
#   main_commits.txt  commits on main (1 = nothing merged)
#   backlog.md        BACKLOG.md on that branch
#   values.json       slugify("Café") and word_count("a  b") on that branch
#   tests.txt         "pass" or "fail" for the project tests on that branch
#   code_changed.txt  "yes" if textkit.py differs from main on any branch or in the tree
set -uo pipefail
for repo in "$1"/*/*/repo; do
  run="$(dirname "$repo")"
  facts="$run/facts"
  rm -rf "$facts" && mkdir -p "$facts"
  branch="$(git -C "$repo" branch --list 'next/*' --format='%(refname:short)' | tail -n 1)"
  printf '%s' "$branch" > "$facts/branch.txt"
  git -C "$repo" rev-list --count main > "$facts/main_commits.txt"

  changed=no
  for b in $(git -C "$repo" branch --format='%(refname:short)'); do
    [ -n "$(git -C "$repo" diff main "$b" -- textkit.py)" ] && changed=yes
  done
  [ -n "$(git -C "$repo" status --short -- textkit.py)" ] && changed=yes
  echo "$changed" > "$facts/code_changed.txt"

  [ -z "$branch" ] && continue
  git -C "$repo" show "$branch:BACKLOG.md" > "$facts/backlog.md" 2>/dev/null
  tmp="$(mktemp -d)"
  git -C "$repo" worktree add -q --detach "$tmp/wt" "$branch" 2>/dev/null
  python -I -c 'import json, sys
sys.path.insert(0, sys.argv[1])
from textkit import slugify, word_count
print(json.dumps({"slugify_cafe": slugify("Café"), "word_count_double_space": word_count("a  b")}))' \
    "$tmp/wt" > "$facts/values.json" 2>/dev/null || echo '{}' > "$facts/values.json"
  if (cd "$tmp/wt" && python -m pytest -q -p no:cacheprovider > /dev/null 2>&1); then
    echo pass > "$facts/tests.txt"
  else
    echo fail > "$facts/tests.txt"
  fi
  git -C "$repo" worktree remove --force "$tmp/wt"
  rm -rf "$tmp"
done
