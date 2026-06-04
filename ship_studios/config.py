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

Building the launch parameters does no filesystem work beyond ``Path.resolve()``
and a small read of the ``.git`` worktree pointer (so the sibling lookup resolves
from the *main* checkout when this is a linked git worktree). Importing the module
stays side-effect free and works before the servers exist; ``doctor`` (in cli.py)
is the place that actually probes for existence.
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from mcp import StdioServerParameters

# --- Server identity --------------------------------------------------------

#: Key used everywhere (Hub, pipelines, tests) to address the loop server.
LOOPS_SERVER = "stemmy-loops"
#: Key used everywhere to address the Gemini audio server.
GEMINI_SERVER = "stemmy-gemini"

#: The valid server keys the Hub can open, in stable order.
SERVER_KEYS: tuple[str, ...] = (LOOPS_SERVER, GEMINI_SERVER)

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
#: Loops-server overrides ([L]): LLM model choices for its LLM-backed tools,
#: plus the *separate* Gemini model var its describe-loops tool reads
#: (``STEMMY_LISTEN_MODEL`` — distinct from the gemini server's
#: ``STEMMY_MCP_MODEL``; the loops server reads its own, so it must be forwarded
#: here or describe-loops stays on the default — the footgun in CLAUDE.md), plus
#: the disk-cache controls its separate/embed/classify tools read
#: (``STEMMY_CACHE_DIR``/``STEMMY_NO_CACHE`` — ``stemmy/_diskcache.py``).
LOOPS_OVERRIDE_ENV: tuple[str, ...] = (
    "STEMMY_LLM_MODEL",
    "STEMMY_LLM_CAPTION_MODEL",
    "STEMMY_LISTEN_MODEL",
    "STEMMY_CACHE_DIR",
    "STEMMY_NO_CACHE",
)

#: Every var the .mcp.json launch forwards (secrets + documented overrides). The
#: interactive launcher (``scripts/mcp_launch.py``) strips any of these that arrive
#: empty, so the server reads an unset var as unset — the interactive counterpart
#: to ``_passthrough_env``'s truthy-only rule. .mcp.json must reference each as
#: ``${VAR:-}`` (Claude Code refuses to parse a bare ``${VAR}`` when the var is
#: unset); the ``:-`` empty default is what mcp_launch.py then drops, so an empty
#: value never reaches a server as a meaningful empty (e.g. an empty
#: ``STEMMY_MCP_ALLOWED_ROOTS`` that would lock the gemini server's allow-list down).
FORWARDED_ENV: tuple[str, ...] = (*ENV_VARS, *LOOPS_OVERRIDE_ENV, *GEMINI_OVERRIDE_ENV)

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
        # A typo'd timeout would otherwise silently fall back — make it visible
        # (still return the default; never raise on a bad env value).
        warnings.warn(
            f"{env}={raw!r} is not a number; using default {default}s",
            stacklevel=2,
        )
        return default
    return None if val <= 0 else val


def startup_timeout_s() -> float | None:
    """Seconds to wait for a server's MCP handshake (``None`` = no limit)."""
    return _timeout(STARTUP_TIMEOUT_ENV, _DEFAULT_STARTUP_TIMEOUT_S)


def call_timeout_s() -> float | None:
    """Seconds to wait for a single tool call (``None`` = no limit)."""
    return _timeout(CALL_TIMEOUT_ENV, _DEFAULT_CALL_TIMEOUT_S)


def repo_root() -> Path:
    """Absolute path to this ship-studios checkout's root (worktree or main).

    ``config.py`` lives at ``<root>/ship_studios/config.py``, so the root is two
    parents up. Resolved so downstream ``--directory`` args are absolute. In a git
    worktree this is the *worktree* dir — use :func:`main_repo_root` for the
    canonical checkout the sibling repos sit next to.
    """
    return Path(__file__).resolve().parent.parent


def _resolve_main_root(root: Path) -> Path:
    """Map a checkout root to the MAIN working-tree root (pure helper, for testing).

    A linked git worktree has a ``.git`` *pointer file*
    (``gitdir: <canonical>/.git/worktrees/<name>``) rather than a ``.git``
    directory. The canonical checkout — where the ``../stemmy-*-mcp`` siblings live
    — is the parent of the shared ``.git`` dir, found via the worktree's
    ``commondir``. A normal checkout (or any IO/parse problem) returns ``root``
    unchanged, so resolution degrades safely.
    """
    git = root / ".git"
    try:
        if not git.is_file():  # normal checkout (.git is a dir) or no .git at all
            return root
        text = git.read_text(encoding="utf-8")
    except OSError:
        return root
    gitdir: Path | None = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("gitdir:"):
            p = Path(s[len("gitdir:") :].strip())
            gitdir = p if p.is_absolute() else (root / p).resolve()
            break
    if gitdir is None:
        return root
    try:
        commondir = gitdir / "commondir"
        if commondir.is_file():
            rel = commondir.read_text(encoding="utf-8").strip()
            common_git = Path(rel) if Path(rel).is_absolute() else (gitdir / rel)
        else:  # fall back to the standard .git/worktrees/<name> layout
            common_git = gitdir.parent.parent
        return common_git.resolve().parent  # parent of the canonical .git dir
    except OSError:
        return root


def main_repo_root() -> Path:
    """Root of the MAIN checkout (== :func:`repo_root` unless this is a worktree).

    The sibling MCP repos are looked up next to *this* root, so resolving it to the
    canonical checkout is what lets the hub/CLI find them from a git worktree.
    """
    return _resolve_main_root(repo_root())


def _sibling_dir(name: str, override_env: str) -> Path:
    """Resolve a sibling repo dir, honoring its override env var first.

    Without an override the sibling is looked up next to the **main** checkout
    (:func:`main_repo_root`), so resolution works from a git worktree too.
    """
    override = os.environ.get(override_env)
    if override:
        return Path(override).expanduser().resolve()
    return (main_repo_root().parent / name).resolve()


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
