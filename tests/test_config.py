"""Config resolves sibling paths, console scripts, server keys, and env."""
from __future__ import annotations

from pathlib import Path

import pytest

from ship_studios import config


@pytest.fixture(autouse=True)
def _clear_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear behaviour-override + timeout env so exact-env assertions are stable
    regardless of the shell that runs the suite."""
    for var in (
        *config.GEMINI_OVERRIDE_ENV,
        *config.LOOPS_OVERRIDE_ENV,
        config.STARTUP_TIMEOUT_ENV,
        config.CALL_TIMEOUT_ENV,
    ):
        monkeypatch.delenv(var, raising=False)


def test_server_keys_are_the_blueprint_keys() -> None:
    assert config.LOOPS_SERVER == "stemmy-loops"
    assert config.GEMINI_SERVER == "stemmy-gemini"


def test_console_scripts_match_siblings() -> None:
    assert config.LOOPS_CONSOLE_SCRIPT == "stemmy-loops-mcp"
    assert config.GEMINI_CONSOLE_SCRIPT == "stemmy-gemini-mcp"


def test_env_vars_are_only_the_two_keys() -> None:
    # The hub must never reference any secret beyond these two.
    assert config.ENV_VARS == ("ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def test_default_sibling_paths_resolve_next_to_main_checkout() -> None:
    # Siblings sit next to the MAIN checkout — == repo_root in a normal checkout,
    # the canonical checkout when run from a git worktree.
    root = config.main_repo_root()
    assert config.loops_dir() == (root.parent / "stemmy-loops-mcp").resolve()
    assert config.gemini_dir() == (root.parent / "stemmy-gemini-mcp").resolve()


def test_sibling_paths_overridable_via_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    loops_override = tmp_path / "alt-loops"
    gemini_override = tmp_path / "alt-gemini"
    monkeypatch.setenv(config.LOOPS_DIR_ENV, str(loops_override))
    monkeypatch.setenv(config.GEMINI_DIR_ENV, str(gemini_override))

    assert config.loops_dir() == loops_override.resolve()
    assert config.gemini_dir() == gemini_override.resolve()


def _make_fake_worktree(tmp_path: Path, *, commondir: bool = True) -> tuple[Path, Path]:
    """Build a fake canonical checkout + a linked worktree under it, mirroring git's
    real layout. Returns ``(worktree_root, canonical_root)``."""
    canonical = tmp_path / "ship-studios"
    gitdir = canonical / ".git" / "worktrees" / "wt"
    gitdir.mkdir(parents=True)
    if commondir:
        (gitdir / "commondir").write_text("../..\n")
    wt = canonical / ".claude" / "worktrees" / "wt"
    wt.mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {gitdir}\n")
    return wt, canonical


def test_resolve_main_root_normal_checkout(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()                       # .git is a real dir -> not a worktree
    assert config._resolve_main_root(tmp_path) == tmp_path


def test_resolve_main_root_no_git_returns_root(tmp_path: Path) -> None:
    assert config._resolve_main_root(tmp_path) == tmp_path


def test_resolve_main_root_worktree_via_commondir(tmp_path: Path) -> None:
    wt, canonical = _make_fake_worktree(tmp_path, commondir=True)
    assert config._resolve_main_root(wt) == canonical.resolve()


def test_resolve_main_root_worktree_layout_fallback(tmp_path: Path) -> None:
    # No commondir file -> fall back to the standard .git/worktrees/<name> layout.
    wt, canonical = _make_fake_worktree(tmp_path, commondir=False)
    assert config._resolve_main_root(wt) == canonical.resolve()


def test_resolve_main_root_malformed_pointer_falls_back(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("garbage, no gitdir line\n")
    assert config._resolve_main_root(tmp_path) == tmp_path


def test_siblings_resolve_from_main_checkout_in_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The regression this fixes: from a worktree, siblings must resolve next to the
    # CANONICAL checkout, not the worktree dir under .claude/worktrees/.
    monkeypatch.delenv(config.LOOPS_DIR_ENV, raising=False)
    monkeypatch.delenv(config.GEMINI_DIR_ENV, raising=False)
    wt, canonical = _make_fake_worktree(tmp_path)
    monkeypatch.setattr(config, "repo_root", lambda: wt)
    assert config.loops_dir() == (canonical.parent / "stemmy-loops-mcp").resolve()
    assert config.gemini_dir() == (canonical.parent / "stemmy-gemini-mcp").resolve()


def test_server_dir_dispatches_on_key() -> None:
    assert config.server_dir(config.LOOPS_SERVER) == config.loops_dir()
    assert config.server_dir(config.GEMINI_SERVER) == config.gemini_dir()
    with pytest.raises(KeyError):
        config.server_dir("nope")


def test_loops_server_parameters_launch_via_uv_directory() -> None:
    params = config.server_parameters(config.LOOPS_SERVER)
    assert params.command == "uv"
    assert params.args == [
        "--directory",
        str(config.loops_dir()),
        "run",
        "stemmy-loops-mcp",
    ]


def test_gemini_server_parameters_launch_via_uv_directory() -> None:
    params = config.server_parameters(config.GEMINI_SERVER)
    assert params.command == "uv"
    assert params.args == [
        "--directory",
        str(config.gemini_dir()),
        "run",
        "stemmy-gemini-mcp",
    ]


def test_unknown_server_key_raises() -> None:
    with pytest.raises(KeyError):
        config.server_parameters("ghost-server")


def test_loops_env_passthrough_includes_both_keys_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    params = config.server_parameters(config.LOOPS_SERVER)
    assert params.env == {"ANTHROPIC_API_KEY": "a-key", "GEMINI_API_KEY": "g-key"}


def test_gemini_env_passthrough_only_gemini_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    params = config.server_parameters(config.GEMINI_SERVER)
    # The gemini server never consumes the Anthropic key.
    assert params.env == {"GEMINI_API_KEY": "g-key"}


def test_unset_keys_are_not_forwarded_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    params = config.server_parameters(config.LOOPS_SERVER)
    assert params.env == {}


def test_documented_overrides_reach_the_server_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression guard: the stdio transport does not inherit the parent shell, so
    # every documented override must be explicitly forwarded or it is dropped.
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("STEMMY_MCP_MODEL", "gemini-x")
    monkeypatch.setenv("STEMMY_MCP_THINKING_LEVEL", "high")
    monkeypatch.setenv("STEMMY_MCP_THINKING_BUDGET", "4096")
    monkeypatch.setenv("STEMMY_MCP_ALLOWED_ROOTS", "/tmp")
    gemini_env = config.server_parameters(config.GEMINI_SERVER).env
    assert gemini_env["STEMMY_MCP_MODEL"] == "gemini-x"
    assert gemini_env["STEMMY_MCP_THINKING_LEVEL"] == "high"
    assert gemini_env["STEMMY_MCP_THINKING_BUDGET"] == "4096"
    assert gemini_env["STEMMY_MCP_ALLOWED_ROOTS"] == "/tmp"

    monkeypatch.setenv("STEMMY_LLM_MODEL", "claude-x")
    monkeypatch.setenv("STEMMY_LLM_CAPTION_MODEL", "claude-haiku-x")
    # describe-loops reads its OWN Gemini model var on the loops server (distinct
    # from the gemini server's STEMMY_MCP_MODEL) — the footgun if not forwarded.
    monkeypatch.setenv("STEMMY_LISTEN_MODEL", "gemini-listen-x")
    loops_env = config.server_parameters(config.LOOPS_SERVER).env
    assert loops_env["STEMMY_LLM_MODEL"] == "claude-x"
    assert loops_env["STEMMY_LLM_CAPTION_MODEL"] == "claude-haiku-x"
    assert loops_env["STEMMY_LISTEN_MODEL"] == "gemini-listen-x"
    # gemini-only overrides never leak into the loops server's env, and the
    # loops-only listen override never leaks into the gemini server's.
    assert "STEMMY_MCP_MODEL" not in loops_env
    assert "STEMMY_MCP_THINKING_BUDGET" not in loops_env
    assert "STEMMY_LISTEN_MODEL" not in gemini_env


def test_override_env_sets_are_locked() -> None:
    # Lock the full expected override surface so a future drop (or an accidental
    # addition that isn't documented in CLAUDE.md) is caught here.
    assert config.LOOPS_OVERRIDE_ENV == (
        "STEMMY_LLM_MODEL",
        "STEMMY_LLM_CAPTION_MODEL",
        "STEMMY_LISTEN_MODEL",
        "STEMMY_CACHE_DIR",
        "STEMMY_NO_CACHE",
    )
    assert config.GEMINI_OVERRIDE_ENV == (
        "STEMMY_MCP_MODEL",
        "STEMMY_MCP_THINKING_LEVEL",
        "STEMMY_MCP_THINKING_BUDGET",
        "STEMMY_MCP_ALLOWED_ROOTS",
    )


def test_timeouts_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    assert config.startup_timeout_s() == 120.0
    assert config.call_timeout_s() == 600.0
    monkeypatch.setenv(config.STARTUP_TIMEOUT_ENV, "5")
    monkeypatch.setenv(config.CALL_TIMEOUT_ENV, "0")  # 0 => disabled
    assert config.startup_timeout_s() == 5.0
    assert config.call_timeout_s() is None
    monkeypatch.setenv(config.STARTUP_TIMEOUT_ENV, "not-a-number")
    with pytest.warns(UserWarning):  # bad value warns, then falls back to default
        assert config.startup_timeout_s() == 120.0


def test_malformed_timeout_warns_but_keeps_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A typo'd timeout must surface a warning (not silently swallow) yet still
    # fall back to the default rather than raising.
    monkeypatch.setenv(config.CALL_TIMEOUT_ENV, "30s")
    with pytest.warns(UserWarning, match=r"CALL_TIMEOUT.*30s.*default 600"):
        assert config.call_timeout_s() == 600.0


def test_all_server_parameters_keyed_by_server() -> None:
    params = config.all_server_parameters()
    assert set(params) == {config.LOOPS_SERVER, config.GEMINI_SERVER}


def test_artifacts_root_default_and_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SHIP_STUDIOS_ARTIFACTS_DIR", raising=False)
    assert config.artifacts_root() == config.repo_root() / "artifacts"
    monkeypatch.setenv("SHIP_STUDIOS_ARTIFACTS_DIR", str(tmp_path / "art"))
    assert config.artifacts_root() == (tmp_path / "art").resolve()
