"""Apply a saved VST preset to any WAV: input gain-stage -> UADx plugin chain -> M/S narrow -> peak trim.

Usage:
    python apply_vst_preset.py <preset.json> <in.wav> <out.wav>

Reproduces a preset built with the vst suite. Needs pedalboard + soundfile + numpy — run it with the
stemmy-loops `vst` venv (e.g. ../stemmy-loops-mcp/.venv/bin/python). It sets the plugins' params
directly (handles UADx enum/float/bool params), which `apply-vst-chain`'s float-only dict can't, and
adds the gain-stage + narrowing that live outside the plugins.

UADx note: plugin `file`s are the **uaudio_*.vst3** build (the UADx native build that renders headless);
the `UAD ….component`/`.vst3` twins pass audio through unprocessed offline — do not use those.

Output gain rule (recipe "output_peak_dbfs"):
    * a real NUMBER (e.g. -1.0)  -> renormalize the plugin output so its sample peak == that dBFS
      (the historical default; every shipped preset sets one, so they behave exactly as before).
    * JSON ``null``              -> FAITHFUL: write the plugin output UNCHANGED (no gain touched).
      Use this for a true-peak limiter or any plugin that already OWNS its ceiling — renormalizing by
      *sample* peak would re-scale the limiter and push the true-peak back over the ceiling, and would
      even AMPLIFY a quiet render up to the target. Faithful never touches gain.
    * absent                     -> the historical default (-1.0). Pass ``null`` to opt into faithful.

pedalboard is imported lazily inside ``main()`` so ``set_param`` stays importable (and unit-testable)
with only numpy/soundfile present — handy for the harness tests, which don't load any plugin.
"""
import sys, json
from pathlib import Path

import numpy as np, soundfile as sf

PLUGIN_DIR = "/Library/Audio/Plug-Ins/VST3/"


def set_param(p, name, value):
    """Set a Pedalboard param tolerantly. Tries the exact assignment first (so presets that pass a
    valid enum string / bool / on-grid float are byte-identical to before). If that fails and the
    param is a discrete/enum with valid_values, snap a numeric target to the nearest valid value —
    this handles the log-stepped string enums some plugins expose (e.g. an SSL HPF corner whose only
    valid strings are '39.8'/'40.2', never '40.0'). Returns a note string when it snapped/failed."""
    try:
        setattr(p, name, value)
        return None
    except Exception as ex:
        try:
            par = p.parameters[name]
            vv = list(getattr(par, "valid_values", []) or [])
        except Exception:
            return f"{name}={value!r}: {str(ex)[:100]}"

        def num(x):
            # Parse a numeric target out of a value/valid-value. Plain numbers parse directly;
            # labeled ratio enums (' 4.0:1', '10.0:1', 'Inf:1') keep only the LEADING token before
            # the ':' so the nearest-valid snap can pick a ratio (a near-miss ratio used to fall to
            # default because float('4.0:1') raised). '∞' -> inf.
            s = str(x).replace("∞", "inf").strip()
            if ":" in s:
                s = s.split(":", 1)[0].strip()
            try:
                return float(s)
            except Exception:
                return None
        tn = num(value)
        # Bail BEFORE building candidates when the target isn't numeric: there is
        # nothing to snap to, and `dist` would evaluate abs(<float> - None) and raise
        # TypeError out of set_param — aborting the whole chain render at the one
        # place that promises never to (main() only prints a `warn:` line). Reached by
        # a single mistyped or plugin-renamed enum label ('Off' against valid_values
        # ['35.0','39.8','40.2']).
        if tn is None:
            return f"{name}={value!r}: {str(ex)[:100]}"

        def dist(nv):  # 0 for an exact match (incl. inf==inf, where abs(inf-inf) would be nan)
            return 0.0 if nv == tn else abs(nv - tn)
        cand = [(dist(num(v)), v) for v in vv if num(v) is not None]
        if cand:
            best = min(cand, key=lambda t: t[0])[1]
            setattr(p, name, best)
            return f"{name}={value!r} -> nearest valid {best!r}"
        return f"{name}={value!r}: {str(ex)[:100]}"


def output_gain(peak, target_dbfs):
    """Pure: the linear gain to apply to a buffer whose current sample peak is ``peak``.

    ``target_dbfs`` is the recipe's ``output_peak_dbfs`` — a real number to renormalize to that
    sample-peak dBFS, or ``None`` (explicit JSON null) to leave the gain untouched (returns 1.0).
    Also returns 1.0 for a silent buffer (peak <= 0). Extracted so the faithful-vs-renormalize
    decision is testable with no plugin/pedalboard.

    There is no separate "absent" sentinel: ``R.get("output_peak_dbfs", -1.0)`` in main() already
    maps an ABSENT key to the -1.0 historical default and an explicit null to ``None``, so the old
    ``_FAITHFUL`` object could never reach here from a real recipe — it only ever appeared in its
    own test."""
    if target_dbfs is None or peak <= 0:
        return 1.0
    return (10 ** (target_dbfs / 20.0)) / peak


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        print("usage: python apply_vst_preset.py <preset.json> <in.wav> <out.wav>", file=sys.stderr)
        return 2
    from pedalboard import load_plugin, Pedalboard  # lazy: keeps set_param importable w/o pedalboard

    with open(sys.argv[1]) as fh:
        preset = json.load(fh)
    inp, outp = sys.argv[2], sys.argv[3]
    R = preset.get("recipe", preset)

    audio, sr = sf.read(inp, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    x *= 10 ** (R.get("input_gain_db", 0) / 20.0)

    plugins = []
    plugin_root = Path(PLUGIN_DIR).resolve()
    for e in R["chain"]:
        # Resolve the plugin file under PLUGIN_DIR and refuse a `file` that escapes it
        # (absolute path or `../` traversal): plugin binaries are loaded+executed, so an
        # untrusted preset must not point load_plugin() at arbitrary filesystem locations.
        cand = (plugin_root / e["file"]).resolve()
        if plugin_root not in cand.parents and cand != plugin_root:
            raise ValueError(f"plugin path escapes {PLUGIN_DIR!r}: {e['file']!r}")
        p = load_plugin(str(cand))
        for k, v in e.get("params", {}).items():
            note = set_param(p, k, v)  # exact-first, then nearest-valid snap; never crashes the render
            if note:
                print(f"warn: {e['file']} {note}", file=sys.stderr)
        plugins.append(p)

    y = Pedalboard(plugins)(x, sr)

    w = R.get("width", 1.0)
    if w != 1.0 and y.shape[0] == 2:  # M/S narrow toward period-mono
        mid = (y[0] + y[1]) * 0.5
        side = (y[0] - y[1]) * 0.5 * w
        y = np.stack([mid + side, mid - side], 0)

    # absent -> -1.0 (historical default); explicit JSON null -> faithful (gain untouched).
    target = R.get("output_peak_dbfs", -1.0)
    peak = float(np.max(np.abs(y)))
    y *= output_gain(peak, target)

    sf.write(outp, y.T, sr, subtype="PCM_24")
    peak_note = "faithful (as-is)" if target is None else f"{target} dBFS"
    print(f"applied '{preset.get('name','preset')}' -> {outp}  "
          f"({R.get('input_gain_db',0):+g} dB in · {len(plugins)} plugins · width {w} · "
          f"peak {peak_note})")

if __name__ == "__main__":
    raise SystemExit(main())
