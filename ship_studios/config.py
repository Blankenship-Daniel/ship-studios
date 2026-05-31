"""Canonical configuration for the ship-studios hub.

Single source of truth for: where the two sibling MCP servers live, the
server keys the rest of the package addresses them by, the env vars that
flow through to the subprocesses, and the StdioServerParameters that launch
each one via ``uv --directory <sibling> run <console-script>``.

Path resolution order for each sibling repo:

1. An explicit override env var (``SHIP_STUDIOS_LOOPS_DIR`` /
   ``SHIP_STUDIOS_GEMINI_DIR``) — set this when the repos aren't laid out
   as siblings (CI, a vendored checkout, etc.).
2. The default sibling location next to *this* repo
   (``../stemmy-loops-mcp`` / ``../stemmy-gemini-mcp``).

Building the launch parameters never touches the filesystem beyond
``Path.resolve()`` so that importing this module — and constructing the
parameters — stays side-effect free and works before the servers exist.
``doctor`` (in cli.py) is the place that actually probes for existence.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from mcp import StdioServerParameters

# --- Server identity --------------------------------------------------------

#: Key used everywhere (Hub, pipelines, tests) to address the loop server.
LOOPS_SERVER = "stemmy-loops"
#: Key used everywhere to address the Gemini audio server.
GEMINI_SERVER = "stemmy-gemini"

#: Console scripts each sibling repo declares in its own pyproject [project.scripts].
LOOPS_CONSOLE_SCRIPT = "stemmy-loops-mcp"
GEMINI_CONSOLE_SCRIPT = "stemmy-gemini-mcp"

#: Default sibling directory names (relative to this repo's parent).
LOOPS_DIR_NAME = "stemmy-loops-mcp"
GEMINI_DIR_NAME = "stemmy-gemini-mcp"

#: Env vars that override the sibling locations when the default layout
#: doesn't hold.
LOOPS_DIR_ENV = "SHIP_STUDIOS_LOOPS_DIR"
GEMINI_DIR_ENV = "SHIP_STUDIOS_GEMINI_DIR"

# --- Secrets / passthrough env ---------------------------------------------

#: Anthropic key — required by the loops server's LLM-backed tools
#: (diagnose-output, ask-about-output, suggest-approach, caption-loops).
ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
#: Gemini key — required by every perceptual stemmy-gemini tool and by the
#: loops server's describe-loops.
GEMINI_API_KEY = "GEMINI_API_KEY"

#: The full set of secrets the hub knows about, in stable order. Used by
#: ``doctor`` and by the per-server passthrough below.
ENV_VARS: tuple[str, ...] = (ANTHROPIC_API_KEY, GEMINI_API_KEY)

#: Which secrets each server actually consumes. The loops server can reach
#: both Anthropic (LLM critique) and Gemini (describe-loops); the gemini
#: server only ever needs the Gemini key.
_SERVER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    LOOPS_SERVER: (ANTHROPIC_API_KEY, GEMINI_API_KEY),
    GEMINI_SERVER: (GEMINI_API_KEY,),
}


def repo_root() -> Path:
    """Absolute path to this ship-studios repository root.

    ``config.py`` lives at ``<root>/ship_studios/config.py``, so the root is
    two parents up. Resolved so downstream ``--directory`` args are absolute.
    """
    return Path(__file__).resolve().parent.parent


def _sibling_dir(name: str, override_env: str) -> Path:
    """Resolve a sibling repo dir, honoring its override env var first."""
    override = os.environ.get(override_env)
    if override:
        return Path(override).expanduser().resolve()
    return (repo_root().parent / name).resolve()


def loops_dir() -> Path:
    """Resolved path to the stemmy-loops-mcp sibling repo."""
    return _sibling_dir(LOOPS_DIR_NAME, LOOPS_DIR_ENV)


def gemini_dir() -> Path:
    """Resolved path to the stemmy-gemini-mcp sibling repo."""
    return _sibling_dir(GEMINI_DIR_NAME, GEMINI_DIR_ENV)


def server_dir(server_key: str) -> Path:
    """Resolved sibling-repo path for either server key."""
    if server_key == LOOPS_SERVER:
        return loops_dir()
    if server_key == GEMINI_SERVER:
        return gemini_dir()
    raise KeyError(f"unknown server key: {server_key!r}")


def _passthrough_env(server_key: str) -> dict[str, str]:
    """Collect the secrets this server consumes from the current process env.

    Only keys that are actually set are forwarded — passing an empty string
    would shadow a value the server might otherwise pick up itself, and the
    server is responsible for raising a clear error when a key it needs is
    genuinely absent.
    """
    keys = _SERVER_ENV_KEYS[server_key]
    return {k: os.environ[k] for k in keys if os.environ.get(k)}


def server_parameters(server_key: str) -> "StdioServerParameters":
    """Build the StdioServerParameters that launch ``server_key`` via uv.

    Command shape mirrors the .mcp.json registration: ``uv --directory
    <abs sibling path> run <console-script>``. The MCP SDK import is local
    so importing ``ship_studios.config`` stays cheap (``doctor`` imports it
    without needing the SDK present).
    """
    from mcp import StdioServerParameters

    if server_key == LOOPS_SERVER:
        directory, console = loops_dir(), LOOPS_CONSOLE_SCRIPT
    elif server_key == GEMINI_SERVER:
        directory, console = gemini_dir(), GEMINI_CONSOLE_SCRIPT
    else:
        raise KeyError(f"unknown server key: {server_key!r}")

    return StdioServerParameters(
        command="uv",
        args=["--directory", str(directory), "run", console],
        env=_passthrough_env(server_key),
    )


def all_server_parameters() -> dict[str, "StdioServerParameters"]:
    """StdioServerParameters for both servers, keyed by server key."""
    return {
        LOOPS_SERVER: server_parameters(LOOPS_SERVER),
        GEMINI_SERVER: server_parameters(GEMINI_SERVER),
    }


def artifacts_root() -> Path:
    """Root for hub-generated run artifacts (``<repo>/artifacts``).

    Overridable via ``SHIP_STUDIOS_ARTIFACTS_DIR`` for sandboxed runs. The
    directory is *not* created here — callers create per-run subdirs lazily
    so importing config never writes to disk.
    """
    override = os.environ.get("SHIP_STUDIOS_ARTIFACTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "artifacts"


def projects_root() -> Path:
    """Root for per-track working directories (``<repo>/projects``).

    Overridable via ``SHIP_STUDIOS_PROJECTS_DIR``. Not created on import.
    """
    override = os.environ.get("SHIP_STUDIOS_PROJECTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "projects"
