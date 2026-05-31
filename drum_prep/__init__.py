"""drum_prep — local multi-mic drum-stem DSP for ship-studios.

A deliberate *local-DSP* package, separate from the pure MCP-orchestration hub
in ``ship_studios/`` (which "owns no DSP"). It covers a job the stemmy MCP
servers do not: phase-aligning and tonally reference-matching a whole multi-mic
drum kit, stem by stem, then rendering loudness-matched A/B auditions.

DSP dependencies (numpy / scipy / soundfile / pyloudnorm) are opt-in via the
``drum-prep`` extra::

    uv sync --extra drum-prep

Heavy imports are deferred (PEP 562 ``__getattr__``) so ``import drum_prep`` and
``drum-prep --help`` stay cheap and work even before the extra is installed.
"""
from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__", "Role", "Kit", "KitStem", "KitError"]


def __getattr__(name: str):  # lazy re-exports — keep top-level import dependency-free
    if name in ("Kit", "KitStem", "KitError"):
        from drum_prep import kit

        return getattr(kit, name)
    if name == "Role":
        from drum_prep.roles import Role

        return Role
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
