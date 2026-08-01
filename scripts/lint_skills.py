#!/usr/bin/env python3
"""Deterministic skill-contract lint — the CI-able backstop for .claude/skills/.

The agent-driven `audit-skill-consistency` workflow is the deep, on-demand check
(it spawns one subagent per skill and needs the Claude harness + API, so it can't
run in CI). This script covers the *enumerable* subset of that contract with plain
stdlib so it can gate every commit/PR:

  1. KEY-LABEL BUG (the recurring one): the three pure-DSP tools that live on the
     [G] stemmy-gemini server but need NO GEMINI_API_KEY — find-sibilance,
     find-resonances, check-streaming-targets — must never be asserted to *need*
     the key. Correct "no key / pure DSP" disclaimers are fine.
  2. BROKEN WIKILINKS: every [[name]] must resolve to a real skill dir or a docs
     target (docs/<name>.md, docs/<name>/README.md, or any docs/**/*.md stem).
  3. FRONTMATTER: name + description + argument-hint present and non-empty.

Exit 0 = clean, 1 = at least one error. Lives under scripts/ (ruff/mypy-excluded
by design) and imports nothing outside the standard library.

Usage:  uv run python scripts/lint_skills.py [REPO_ROOT]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Pure-DSP tools that SIT on the [G] gemini server but make no model call → no key.
KEYLESS_GEMINI_TOOLS = ("find-sibilance", "find-resonances", "check-streaming-targets")
# Tokens that mark a sentence as a CORRECT "no key" disclaimer (so we don't flag it).
NEGATIONS = (
    "no gemini_api_key", "no `gemini_api_key`", "no key", "no-key", "keyless",
    "without a key", "without the key", "without gemini_api_key", "pure dsp",
    "pure-dsp", "makes no model call", "no model call", "no network", "not need",
    "needs no", "need no", "don't need", "do not need", "no api key",
)
NEED_WORDS = ("need", "require", "requires", "needed", "requiring")

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the leading --- YAML block into a flat {key: value} of its top-level
    single-line scalars (enough for name/description/argument-hint presence)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


#: Sentence break: end punctuation followed by whitespace, or any newline(s).
#: The trailing-whitespace requirement keeps "docs/foo.md" and "-14 LUFS." mid-token
#: periods from splitting; newlines break markdown bullets and table rows apart,
#: which is what we want — each is its own claim.
_SENTENCE_RE = re.compile(r"(?<=[.;:!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    """Split into claim-sized chunks for the key-label check (whitespace collapsed).

    Scoping that check to a sentence rather than a character window is what makes
    it sound: a window cannot attribute a negation to a tool, so a correct
    disclaimer about tool B silences a genuine mislabel of tool A sitting beside it.
    """
    return [" ".join(part.split()) for part in _SENTENCE_RE.split(text) if part.strip()]


def _wikilink_targets(raw: str) -> list[str]:
    """Normalize a [[...]] payload to its target name(s): strip alias (|) and
    anchor (#); a payload may itself be a pipe-list of alternatives."""
    targets = []
    for part in raw.split("|"):
        name = part.split("#", 1)[0].strip()
        if name:
            targets.append(name)
    # Only the FIRST is the link target; the rest are display aliases — but some
    # of our descriptions use [[a]] / [[b]] separately, never aliased, so callers
    # pass one payload per match. Return the first (the real target).
    return targets[:1]


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    skills_dir = root / ".claude" / "skills"
    docs_dir = root / "docs"
    if not skills_dir.is_dir():
        print(f"lint_skills: no skills dir at {skills_dir}", file=sys.stderr)
        return 1

    skill_names = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()}
    doc_stems: set[str] = set()
    if docs_dir.is_dir():
        for p in docs_dir.rglob("*.md"):
            doc_stems.add(p.stem)                       # docs/foo.md  -> foo
            doc_stems.add(p.parent.name)               # docs/foo/README.md -> foo
            doc_stems.add(str(p.relative_to(docs_dir).with_suffix("")))  # foo/bar

    errors: list[str] = []

    for name in sorted(skill_names):
        path = skills_dir / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        rel = f".claude/skills/{name}/SKILL.md"

        # (3) frontmatter presence
        fm = _frontmatter(text)
        for field in ("name", "description", "argument-hint"):
            if not fm.get(field):
                errors.append(f"{rel}: frontmatter missing/empty `{field}`")

        # (1) key-label bug — scoped to the SENTENCE the tool name appears in.
        # NOT a +/-100 char window: a window cannot tell WHOSE negation it sees, so
        # the repo's idiomatic contrast phrasing silenced real hits —
        #   "requires GEMINI_API_KEY for find-sibilance. measure-loudness is pure
        #    DSP and needs no key."
        # put a negation ("pure dsp", "needs no key") belonging to measure-loudness
        # inside find-sibilance's window, and the bug this gate exists to catch
        # passed CI. A sentence still holds a genuine same-clause disclaimer
        # ("find-sibilance needs no key"), which is the case we must not flag.
        seen_tools: set[str] = set()
        for sentence in _sentences(text):
            low = sentence.lower()
            if "gemini_api_key" not in low or not any(w in low for w in NEED_WORDS):
                continue
            if any(neg in low for neg in NEGATIONS):
                continue
            for tool in KEYLESS_GEMINI_TOOLS:
                if tool in low and tool not in seen_tools:
                    seen_tools.add(tool)
                    errors.append(
                        f"{rel}: key-label-bug — `{tool}` is pure DSP (no GEMINI_API_KEY) "
                        f"but this implies it needs one: …{sentence.strip()}…"
                    )

        # (2) broken wikilinks
        for m in WIKILINK_RE.finditer(text):
            for target in _wikilink_targets(m.group(1)):
                if target in skill_names or target in doc_stems:
                    continue
                # tolerate a docs/ path written inside the wikilink
                if (docs_dir / f"{target}.md").is_file() or (docs_dir / target).is_dir():
                    continue
                errors.append(f"{rel}: broken-wikilink [[{target}]]")

    if errors:
        print(f"lint_skills: {len(errors)} error(s) across {len(skill_names)} skills:\n")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print(f"lint_skills: OK — {len(skill_names)} skills clean "
          f"(frontmatter, wikilinks, [G]-keyless labels).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
