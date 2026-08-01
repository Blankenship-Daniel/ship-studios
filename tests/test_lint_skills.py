"""scripts/lint_skills.py — the CI-gated skill-contract linter.

The gate had no tests of its own, which is how its headline check came to be
defeated by the repo's own idiomatic phrasing (see
``test_key_label_bug_is_not_masked_by_a_neighbouring_tools_disclaimer``). These
drive ``main()`` end to end over a throwaway skills tree.

Loaded by file path under a namespaced module name: ``scripts/`` is not a package,
and registering a bare ``lint_skills`` in ``sys.modules`` would leak into any later
import in the same session.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "scripts" / "lint_skills.py"


def _load():
    spec = importlib.util.spec_from_file_location("ship_studios_tests.lint_skills", _SRC)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # deliberately NOT added to sys.modules
    return mod


lint_skills = _load()

_FM = """---
name: {name}
description: A test skill.
argument-hint: "[path]"
---

"""


def _skill(root: Path, name: str, body: str) -> None:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(_FM.format(name=name) + body, encoding="utf-8")


def _run(root: Path, capsys) -> tuple[int, str]:
    rc = lint_skills.main(["lint_skills.py", str(root)])
    return rc, capsys.readouterr().out


def test_clean_skill_passes(tmp_path, capsys) -> None:
    _skill(tmp_path, "alpha", "Runs `measure-loudness`. Pure DSP, no key needed.\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0
    assert "OK" in out


def test_key_label_bug_is_flagged(tmp_path, capsys) -> None:
    """The recurring bug: a [G]-server pure-DSP tool asserted to need the key."""
    _skill(tmp_path, "alpha", "This skill requires GEMINI_API_KEY for find-sibilance.\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 1
    assert "key-label-bug" in out and "find-sibilance" in out


def test_key_label_bug_is_not_masked_by_a_neighbouring_tools_disclaimer(
    tmp_path, capsys
) -> None:
    """A correct disclaimer about ANOTHER tool must not silence a real mislabel.

    The check used to scan a +/-100 character window and skip the whole hit if any
    negation appeared in it — so this text, whose second sentence is a correct note
    about ``measure-loudness``, let the first sentence's genuine ``find-sibilance``
    mislabel through. That contrast phrasing is idiomatic across this repo's skills,
    so the gate was silently worth far less than it appeared.
    """
    _skill(
        tmp_path,
        "alpha",
        "This skill requires GEMINI_API_KEY for find-sibilance. "
        "Note measure-loudness is pure DSP and needs no key.\n",
    )
    rc, out = _run(tmp_path, capsys)
    assert rc == 1, "a real key-label bug was masked by an adjacent correct note"
    assert "find-sibilance" in out


@pytest.mark.parametrize(
    "body",
    [
        "`find-sibilance` needs no GEMINI_API_KEY — it is pure DSP.\n",
        "find-resonances requires no key (pure-DSP, despite the [G] server).\n",
        "Needs GEMINI_API_KEY; find-sibilance itself is keyless.\n",
    ],
)
def test_same_clause_disclaimers_are_not_flagged(tmp_path, capsys, body) -> None:
    """A genuine same-sentence 'no key' disclaimer stays legal — that is the whole
    point of tracking negations, and the case the sentence scope must preserve."""
    _skill(tmp_path, "alpha", body)
    rc, out = _run(tmp_path, capsys)
    assert rc == 0, out


def test_broken_wikilink_is_flagged(tmp_path, capsys) -> None:
    _skill(tmp_path, "alpha", "See [[no-such-skill]] for details.\n")
    rc, out = _run(tmp_path, capsys)
    assert rc == 1
    assert "broken-wikilink" in out


def test_wikilink_to_a_real_skill_and_doc_resolves(tmp_path, capsys) -> None:
    _skill(tmp_path, "alpha", "See [[beta]] and [[setup]].\n")
    _skill(tmp_path, "beta", "Hello.\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "setup.md").write_text("# setup\n", encoding="utf-8")
    rc, out = _run(tmp_path, capsys)
    assert rc == 0, out


def test_missing_frontmatter_field_is_flagged(tmp_path, capsys) -> None:
    d = tmp_path / ".claude" / "skills" / "alpha"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: No argument hint.\n---\n\nBody.\n", encoding="utf-8"
    )
    rc, out = _run(tmp_path, capsys)
    assert rc == 1
    assert "argument-hint" in out


def test_missing_skills_dir_is_an_error(tmp_path, capsys) -> None:
    assert lint_skills.main(["lint_skills.py", str(tmp_path)]) == 1
