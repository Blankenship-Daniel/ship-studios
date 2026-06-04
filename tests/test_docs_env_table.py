"""CLAUDE.md env-var table ⊇ ``config.FORWARDED_ENV`` (A5).

CLAUDE.md's "Environment variables" table is a hand-maintained mirror of the
vars the launch actually forwards (``ship_studios.config.FORWARDED_ENV``); the
code comment literally says "keep in sync with CLAUDE.md". This one-line gate
closes that manual-sync gap: every forwarded var must be documented somewhere
in CLAUDE.md, so adding a forwarded var without documenting it fails CI.

It is intentionally a SUPERSET check (doc ⊇ forwarded), not equality — the doc
also covers hub-only vars (timeouts, dir overrides, artifact roots) that aren't
forwarded to the siblings, and that's fine. Offline: just reads the file.
"""
from __future__ import annotations

from ship_studios import config


def _claude_md_text() -> str:
    return (config.repo_root() / "CLAUDE.md").read_text(encoding="utf-8")


def test_every_forwarded_env_var_is_documented() -> None:
    text = _claude_md_text()
    missing = [var for var in config.FORWARDED_ENV if var not in text]
    assert not missing, (
        "FORWARDED_ENV vars absent from CLAUDE.md (document them in the "
        f"Environment variables table): {missing}"
    )


def test_forwarded_env_is_nonempty() -> None:
    # A sanity guard so a refactor that empties FORWARDED_ENV doesn't make the
    # superset check pass vacuously.
    assert config.FORWARDED_ENV, "FORWARDED_ENV is unexpectedly empty"
