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

#: Documented, non-secret behaviour overrides each server reads from its env.
#: These are NOT inherited automatically: the MCP stdio transport spawns the
#: server with only a minimal safe allow-list (HOME/PATH/…) merged with whatever
#: ``StdioServerParameters.env`` carries, so anything we don't forward here is
#: silently dropped. Keep this in sync with CLAUDE.md's env-vars table.
#: Gemini-server overrides ([G]): model + per-call thinking tier + FS allow-list.
GEMINI_OVERRIDE_ENV: tuple[str, ...] = (
    "STEMMY_MCP_MODEL",
    "STEMMY_MCP_THINKING_LEVEL",
    "STEMMY_MCP_THINKING_BUDGET",
    "STEMMY_MCP_ALLOWED_ROOTS",
)
#: Loops-server overrides ([L]): LLM model choices for its LLM-backed tools.
LOOPS_OVERRIDE_ENV: tuple[str, ...] = (
    "STEMMY_LLM_MODEL",
    "STEMMY_LLM_CAPTION_MODEL",
)

#: Which env vars each server actually consumes (secrets + documented overrides).
#: The loops server can reach both Anthropic (LLM critique) and Gemini
#: (describe-loops); the gemini server only ever needs the Gemini key. Every var
#: here is forwarded ONLY when set (see ``_passthrough_env``), so listing an
#: unset override is harmless.
_SERVER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    LOOPS_SERVER: (ANTHROPIC_API_KEY, GEMINI_API_KEY, *LOOPS_OVERRIDE_ENV),
    GEMINI_SERVER: (GEMINI_API_KEY, *GEMINI_OVERRIDE_ENV),
}


#: Default timeouts (seconds). The first ``uv run`` of a sibling can be slow
#: while it builds/resolves the dependency tree, so the handshake budget is
#: generous; a tool call (esp. a Gemini perceptual call with thinking) gets more.
#: Override via the env vars; set ``0`` to disable a timeout entirely.
STARTUP_TIMEOUT_ENV = "SHIP_STUDIOS_STARTUP_TIMEOUT"
CALL_TIMEOUT_ENV = "SHIP_STUDIOS_CALL_TIMEOUT"
_DEFAULT_STARTUP_TIMEOUT_S = 120.0
_DEFAULT_CALL_TIMEOUT_S = 600.0


def _timeout(env: str, default: float) -> float | None:
    """Read a timeout from ``env`` (seconds); ``None`` means no timeout (``0``)."""
    raw = os.environ.get(env)
    if raw is None or raw == "":
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    return None if val <= 0 else val


def startup_timeout_s() -> float | None:
    """Seconds to wait for a server's MCP handshake (``None`` = no limit)."""
    return _timeout(STARTUP_TIMEOUT_ENV, _DEFAULT_STARTUP_TIMEOUT_S)


def call_timeout_s() -> float | None:
    """Seconds to wait for a single tool call (``None`` = no limit)."""
    return _timeout(CALL_TIMEOUT_ENV, _DEFAULT_CALL_TIMEOUT_S)


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
    """Collect the env vars this server consumes from the current process env.

    Forwards the server's secrets *and* its documented behaviour overrides
    (model / thinking tier / allow-list / LLM model) — the stdio transport does
    not inherit the parent shell beyond a minimal allow-list, so an override we
    don't forward here never reaches the subprocess. Only keys that are actually
    set are included; an unset override is simply omitted (the server applies its
    own default), and the server raises if a key it truly needs is absent.
    """
    keys = _SERVER_ENV_KEYS[server_key]
    return {k: os.environ[k] for k in keys if os.environ.get(k)}


def server_parameters(server_key: str) -> StdioServerParameters:
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


def all_server_parameters() -> dict[str, StdioServerParameters]:
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
