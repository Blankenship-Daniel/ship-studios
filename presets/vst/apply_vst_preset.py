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
            try:
                setattr(p, k, v)
            except Exception as ex:  # surface, don't crash — a wrong param leaves that one at default
                print(f"warn: {e['file']} {k}={v!r}: {str(ex)[:100]}", file=sys.stderr)
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
