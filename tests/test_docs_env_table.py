"""Env-var docs ⊇ ``config.FORWARDED_ENV`` (A5).

The "Environment variables" table is a hand-maintained mirror of the vars the
launch actually forwards (``ship_studios.config.FORWARDED_ENV``); the code
comment says "keep in sync with the env-var docs". This one-line gate closes
that manual-sync gap: every forwarded var must be documented somewhere in the
env-var reference, so adding a forwarded var without documenting it fails CI.

The reference spans CLAUDE.md (the always-loaded contract: the two API keys +
broadly-applicable notes) plus ``docs/setup.md`` (the full env-var table that
CLAUDE.md links out to, to keep CLAUDE.md under its char limit). The gate reads
BOTH so a var documented in either satisfies the invariant.

It is intentionally a SUPERSET check (docs ⊇ forwarded), not equality — the docs
also cover hub-only vars (timeouts, dir overrides, artifact roots) that aren't
forwarded to the siblings, and that's fine. Offline: just reads the files.
"""
from __future__ import annotations

from ship_studios import config

#: Files that together form the env-var reference (see module docstring).
_ENV_DOC_PATHS = ("CLAUDE.md", "docs/setup.md")


def _env_doc_text() -> str:
    root = config.repo_root()
    return "\n".join(
        (root / rel).read_text(encoding="utf-8") for rel in _ENV_DOC_PATHS
    )


def test_every_forwarded_env_var_is_documented() -> None:
    text = _env_doc_text()
    missing = [var for var in config.FORWARDED_ENV if var not in text]
    assert not missing, (
        "FORWARDED_ENV vars absent from the env-var docs (document them in the "
        f"Environment variables table in docs/setup.md): {missing}"
    )


def test_forwarded_env_is_nonempty() -> None:
    # A sanity guard so a refactor that empties FORWARDED_ENV doesn't make the
    # superset check pass vacuously.
    assert config.FORWARDED_ENV, "FORWARDED_ENV is unexpectedly empty"
