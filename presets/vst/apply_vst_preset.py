"""Apply a saved VST preset to any WAV: input gain-stage -> UADx plugin chain -> M/S narrow -> peak trim.

Usage:
    python apply_vst_preset.py <preset.json> <in.wav> <out.wav>

Reproduces a preset built with the vst suite. Needs pedalboard + soundfile + numpy — run it with the
stemmy-loops `vst` venv (e.g. ../stemmy-loops-mcp/.venv/bin/python). It sets the plugins' params
directly (handles UADx enum/float/bool params), which `apply-vst-chain`'s float-only dict can't, and
adds the gain-stage + narrowing that live outside the plugins.

UADx note: plugin `file`s are the **uaudio_*.vst3** build (the UADx native build that renders headless);
the `UAD ….component`/`.vst3` twins pass audio through unprocessed offline — do not use those.
"""
import sys, json
import numpy as np, soundfile as sf
from pedalboard import load_plugin, Pedalboard

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
            try:
                return float(str(x).replace("∞", "inf"))
            except Exception:
                return None
        tn = num(value)
        cand = [(abs(num(v) - tn), v) for v in vv if num(v) is not None]
        if tn is not None and cand:
            best = min(cand, key=lambda t: t[0])[1]
            setattr(p, name, best)
            return f"{name}={value!r} -> nearest valid {best!r}"
        return f"{name}={value!r}: {str(ex)[:100]}"


def main():
    preset = json.load(open(sys.argv[1]))
    inp, outp = sys.argv[2], sys.argv[3]
    R = preset.get("recipe", preset)

    audio, sr = sf.read(inp, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    x *= 10 ** (R.get("input_gain_db", 0) / 20.0)

    plugins = []
    for e in R["chain"]:
        p = load_plugin(PLUGIN_DIR + e["file"])
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

    peak = float(np.max(np.abs(y)))
    if peak > 0:
        y *= (10 ** (R.get("output_peak_dbfs", -1.0) / 20.0)) / peak

    sf.write(outp, y.T, sr, subtype="PCM_24")
    print(f"applied '{preset.get('name','preset')}' -> {outp}  "
          f"({R.get('input_gain_db',0):+g} dB in · {len(plugins)} plugins · width {w} · "
          f"peak {R.get('output_peak_dbfs',-1)} dBFS)")

if __name__ == "__main__":
    raise SystemExit(main())
