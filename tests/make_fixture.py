"""Creates a small git repo to test next-task against.

Usage: python -I make_fixture.py <dest> <variant>   (writes the files only;
setup.sh calls it and makes the git repo)
Variants: normal (a real bug first), obsolete (the first item is already fixed),
nobacklog (no backlog at all).

Then run the skill in <dest> as if the user typed /next-task, save its final reply to
outputs/final.md next to the repo, and grade with grade.py.
"""
import sys
from pathlib import Path

CLAUDE = """# textkit

Small text utilities. Tests: `python -m pytest -q`. Commits: `fix:`, `feat:`, `docs:`.
Merging: never merge; leave PRs open for review.
"""

TEXT_OK = '''import unicodedata


def slugify(s: str) -> str:
    """'Café Olé!' -> 'cafe-ole'"""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    out = "".join(c.lower() if c.isalnum() else "-" for c in s)
    return "-".join(p for p in out.split("-") if p)


def word_count(s: str) -> int:
    return len(s.split(" "))
'''

TEXT_BUG = TEXT_OK.replace(
    '    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()\n', "")

TESTS = '''from textkit import slugify, word_count


def test_slug_basic():
    assert slugify("Hello World") == "hello-world"


def test_words():
    assert word_count("a b c") == 3
'''

BACKLOG = """# Backlog

## Next

- [ ] {first}
- [ ] word_count counts empty strings between double spaces: `word_count("a  b")` returns 3, should be 2.
- [ ] (waiting on a human) Decide whether slugify should keep underscores.

## Waiting on a human

## Done

- [x] Project skeleton — PR #1 — tests run with `python -m pytest -q`
"""


def main():
    dest, var = Path(sys.argv[1]), sys.argv[2]
    dest.mkdir(parents=True)
    (dest / "CLAUDE.md").write_text(CLAUDE, encoding="utf-8")
    (dest / "textkit.py").write_text(TEXT_OK if var == "obsolete" else TEXT_BUG, encoding="utf-8")
    (dest / "test_textkit.py").write_text(TESTS, encoding="utf-8")
    if var != "nobacklog":
        (dest / "BACKLOG.md").write_text(BACKLOG.format(
            first="slugify keeps accented letters instead of transliterating them: `slugify(\"Café\")` gives `café`, should give `cafe`."),
            encoding="utf-8")


if __name__ == "__main__":
    main()
