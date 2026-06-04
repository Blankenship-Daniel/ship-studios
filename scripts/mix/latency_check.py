"""Verify a set of per-stem FabFilter chains are LATENCY-MATCHED (so a phase-aligned kit stays coherent
after the EQ) — by impulse-probing each chain's EXACT latency. The clean kit-coherence guarantee for
[[ff-stems]]; not confused by the EQ magnitude the way a program-material cross-correlation is.

Why: a LINEAR-PHASE EQ adds a constant delay. At a FIXED Pro-Q `processing_resolution` that delay is
FFT-fixed and CURVE-INDEPENDENT, so every kit-mode stem comes out delayed by the SAME amount → the prior
phase-alignment survives and NO compensation is needed. This script proves it (and only if a chain ever
reports a DIFFERENT latency does it offer to compensate that stem by the exact integer difference).

Usage:
    python scripts/mix/latency_check.py <chains_dir> \
        [--plugin-dir /Library/Audio/Plug-Ins/VST3/] \
        [--processed <dir> --suffix _ffchain --write]   # only needed if latency is NON-uniform

Loads every <chains_dir>/*.json that is a single-stem preset (has recipe.chain), runs a unit impulse
through the plugin chain, and reports each chain's latency (the impulse-response peak) + the spread. Needs
the loops `vst` venv (pedalboard + numpy + soundfile). Exit 0 = uniform (coherent), 1 = non-uniform.
"""
import sys, json
from pathlib import Path
import numpy as np
import soundfile as sf

SR = 48000
DEFAULT_PLUGIN_DIR = "/Library/Audio/Plug-Ins/VST3/"


def chain_latency(preset, plugin_dir):
    from pedalboard import load_plugin, Pedalboard
    plugs = []
    for e in preset["recipe"]["chain"]:
        p = load_plugin(plugin_dir + e["file"])
        for k, v in e.get("params", {}).items():
            try:
                setattr(p, k, v)
            except Exception:
                pass  # enum snap handled at apply time; latency is unaffected by an unset cosmetic param
        plugs.append(p)
    x = np.zeros((SR * 2, 2), dtype=np.float32)
    x[SR, :] = 0.5  # moderate impulse: below comp/limiter thresholds so we measure pure chain latency
    y = Pedalboard(plugs)(x.T.copy(), SR).T
    return int(np.argmax(np.abs(y[:, 0]))) - SR


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__, file=sys.stderr)
        return 2
    chains_dir = Path(a[0])
    plugin_dir = a[a.index("--plugin-dir") + 1] if "--plugin-dir" in a else DEFAULT_PLUGIN_DIR
    presets = {}
    for p in sorted(chains_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and "recipe" in d and d["recipe"].get("chain"):
            presets[p.stem] = d
    if not presets:
        print(f"no single-stem presets in {chains_dir}", file=sys.stderr)
        return 2

    print(f"{'stem':16} {'latency_samp':>12} {'ms':>8}")
    lat = {}
    for s, d in presets.items():
        lat[s] = chain_latency(d, plugin_dir)
        print(f"{s:16} {lat[s]:>12d} {lat[s] / SR * 1000:>8.2f}")
    spread = max(lat.values()) - min(lat.values())
    print(f"\nlatency spread = {spread} samp ({spread / SR * 1000:.3f} ms) -> "
          f"{'UNIFORM: kit stays coherent, no compensation needed' if spread <= 1 else 'NON-UNIFORM: stems will drift'}")

    if spread > 1 and "--processed" in a and "--write" in a:
        proc = Path(a[a.index("--processed") + 1])
        suffix = a[a.index("--suffix") + 1] if "--suffix" in a else "_ffchain"
        base = min(lat.values())
        for s in presets:
            f = proc / f"{s}{suffix}.wav"
            if not f.is_file():
                continue
            y, sr = sf.read(str(f), dtype="float32", always_2d=True)
            k = lat[s] - base  # advance each stem by its EXCESS latency over the fastest chain
            if k > 0:
                y = np.vstack([y[k:], np.zeros((k, y.shape[1]), dtype=y.dtype)])
            sf.write(str(f), y, sr, subtype="PCM_24")
            print(f"  compensated {s}: advanced {k} samp")
    return 0 if spread <= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
