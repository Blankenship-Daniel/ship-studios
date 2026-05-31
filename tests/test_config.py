"""Config resolves sibling paths, console scripts, server keys, and env."""
from __future__ import annotations

from pathlib import Path

import pytest

from ship_studios import config


def test_server_keys_are_the_blueprint_keys() -> None:
    assert config.LOOPS_SERVER == "stemmy-loops"
    assert config.GEMINI_SERVER == "stemmy-gemini"


def test_console_scripts_match_siblings() -> None:
    assert config.LOOPS_CONSOLE_SCRIPT == "stemmy-loops-mcp"
    assert config.GEMINI_CONSOLE_SCRIPT == "stemmy-gemini-mcp"


def test_env_vars_are_only_the_two_keys() -> None:
    # The hub must never reference any secret beyond these two.
    assert config.ENV_VARS == ("ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def test_default_sibling_paths_resolve_next_to_repo() -> None:
    root = config.repo_root()
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
