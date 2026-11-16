#!/usr/bin/env bash
# Creates the three test repos for one configuration of next-task.
# Usage: bash tests/setup.sh <iteration-dir> <config-name>
#   e.g. bash tests/setup.sh work/iteration-1 with_skill
# Result: <iteration-dir>/{normal,obsolete,nobacklog}/<config-name>/repo, each a git repo
# on main with one commit, plus an empty outputs/ folder for the run's final reply.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for variant in normal obsolete nobacklog; do
  run="$1/$variant/$2"
  python -I "$here/make_fixture.py" "$run/repo" "$variant"
  mkdir -p "$run/outputs"
  git -C "$run/repo" init -q -b main
  git -C "$run/repo" add .
  git -C "$run/repo" -c user.name=test -c user.email=test@example.invalid commit -qm init
done
