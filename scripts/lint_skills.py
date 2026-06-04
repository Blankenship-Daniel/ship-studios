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

        # (1) key-label bug — proximity-window scoped (newlines normalized to
        # spaces) so a wrapped "X needs the key; <keyless-tool> is pure DSP"
        # contrast keeps its negation in view and is NOT flagged.
        flat = " ".join(text.split())
        flat_low = flat.lower()
        seen_tools: set[str] = set()
        for tool in KEYLESS_GEMINI_TOOLS:
            start = 0
            while (i := flat_low.find(tool, start)) != -1:
                start = i + len(tool)
                if tool in seen_tools:
                    break
                win = flat_low[max(0, i - 100): i + len(tool) + 100]
                if (
                    "gemini_api_key" in win
                    and any(w in win for w in NEED_WORDS)
                    and not any(neg in win for neg in NEGATIONS)
                ):
                    seen_tools.add(tool)
                    snippet = flat[max(0, i - 60): i + len(tool) + 60].strip()
                    errors.append(
                        f"{rel}: key-label-bug — `{tool}` is pure DSP (no GEMINI_API_KEY) "
                        f"but this implies it needs one: …{snippet}…"
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
