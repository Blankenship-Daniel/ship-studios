"""Resolve a sibling MCP server's dir (worktree-aware) and exec it via uv.

Used by ``.mcp.json`` so the interactive ``stemmy-loops`` / ``stemmy-gemini``
servers resolve their sibling repo even when this checkout is a git **worktree**
— where a static ``--directory ../stemmy-*-mcp`` would point inside
``.claude/worktrees/`` and miss the siblings (which live next to the *canonical*
checkout).

Invoked as ``python scripts/mcp_launch.py <server-key>`` (server-key =
``stemmy-loops`` | ``stemmy-gemini``), with cwd at the workspace root. It reuses
``ship_studios.config`` (stdlib-only at import; no install needed) so the sibling
resolution stays in lockstep with the hub/CLI, then ``exec``s
``uv --directory <abs sibling> run <console-script>`` — the same final command the
old `.mcp.json` produced from the main checkout, just with the path corrected.

``--check`` prints the resolved command instead of exec-ing (for verification).

Lives in ``scripts/`` (outside ruff/mypy by design) because ``.mcp.json`` needs a
stable workspace-relative path that travels with every checkout/worktree.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# This script lives at <repo>/scripts/mcp_launch.py; put <repo> on sys.path so the
# stdlib-only config resolver imports without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from ship_studios import config  # noqa: E402


def _console_for(key: str) -> str:
    # Explicit per-key lookup: an unknown key raises KeyError rather than
    # silently falling back to the gemini console script.
    return {
        config.LOOPS_SERVER: config.LOOPS_CONSOLE_SCRIPT,
        config.GEMINI_SERVER: config.GEMINI_CONSOLE_SCRIPT,
    }[key]


def main(argv: list[str]) -> int:
    check = "--check" in argv
    positional = [a for a in argv if a != "--check"]
    if len(positional) != 1 or positional[0] not in config.SERVER_KEYS:
        sys.stderr.write(
            f"usage: mcp_launch.py [--check] <{' | '.join(config.SERVER_KEYS)}>\n"
        )
        return 2
    key = positional[0]
    cmd = ["uv", "--directory", str(config.server_dir(key)), "run", _console_for(key)]
    if check:
        print(" ".join(cmd))
        return 0
    # Replace this process with the server. .mcp.json forwards the API keys + the
    # documented STEMMY_* overrides as ${VAR:-}, so an UNSET override arrives here as
    # an empty string (Claude Code refuses to parse a bare ${VAR} when it is unset).
    # Drop those empties so the server sees an unset var as truly unset — mirroring
    # the CLI's config._passthrough_env (an empty STEMMY_MCP_ALLOWED_ROOTS would
    # otherwise read as an empty allow-list and lock the gemini server down). The
    # server inherits this cleaned env through `uv run <console>`.
    env = dict(os.environ)
    for var in config.FORWARDED_ENV:
        if env.get(var) == "":
            del env[var]
    os.execvpe(cmd[0], cmd, env)
    return 0  # unreachable (execvpe does not return on success)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
