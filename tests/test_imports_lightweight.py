"""Lock in the dependency-light / lazy-import architecture the perf report verified.

The hub (``ship_studios``) is a DSP-free MCP *client*: ``import ship_studios``
must stay cheap (~1.7 ms in the perf run) by NOT eagerly pulling the heavy stack
— the MCP SDK (``mcp``), numpy/scipy/soundfile/pyloudnorm, or ``psutil``. Those
are imported lazily, only when a code path that genuinely needs them runs (e.g.
``perf.sample_rss`` imports ``psutil`` on demand). These guards fail loudly if a
future edit reintroduces a top-level heavy import.

A FRESH interpreter per check is REQUIRED: the running pytest session has already
imported numpy/scipy/mcp (other tests use them), so they sit in *this* process's
``sys.modules`` regardless of what ``ship_studios`` imports — an in-process check
would be meaningless. We launch ``sys.executable -c <import + dump>`` in a
subprocess and inspect *its* clean ``sys.modules``.
"""
from __future__ import annotations

import subprocess
import sys


def _modules_after_import(import_stmt: str) -> set[str]:
    """Run ``import_stmt`` in a fresh interpreter; return its sys.modules names."""
    code = (
        f"{import_stmt}\n"
        "import sys\n"
        "print('\\n'.join(sorted(sys.modules)))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in proc.stdout.splitlines() if line}


def test_core_hub_import_stays_lightweight() -> None:
    loaded = _modules_after_import("import ship_studios")
    heavy = {"mcp", "numpy", "scipy", "soundfile", "pyloudnorm"}
    leaked = heavy & loaded
    assert not leaked, f"`import ship_studios` eagerly pulled heavy modules: {sorted(leaked)}"


def test_cli_import_does_not_pull_heavy_or_psutil() -> None:
    # The CLI is DSP-free; the MCP SDK and psutil are lazy (this also guards the
    # perf.py lazy-psutil fix, exercised at the CI gate after that fix lands).
    loaded = _modules_after_import("import ship_studios.cli")
    heavy = {"mcp", "numpy", "scipy", "soundfile", "pyloudnorm", "psutil"}
    leaked = heavy & loaded
    assert not leaked, f"`import ship_studios.cli` eagerly pulled lazy modules: {sorted(leaked)}"
