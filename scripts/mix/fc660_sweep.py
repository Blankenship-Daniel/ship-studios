"""Isolation/characterization sweep for the UADx Fairchild 660 (uaudio_fairchild_660.vst3).

Loads the plugin fresh per render (state isolation), sets its enum params via a tolerant
setattr-with-nearest-valid snap (every Fairchild param is an enum), processes a drum-bus
excerpt, and writes FLOAT32 WAVs (no peak trim) so the real level / GR / color survive
measurement. Prints quick numpy peak/RMS/crest per render; use the MCP meters
(measure-loudness / measure-microdynamics / measure-spectrum) on the written files for the
authoritative numbers cited in docs/vst/fairchild-660.md.

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/fc660_sweep.py
"""
import re
import numpy as np
import soundfile as sf
from pedalboard import load_plugin, Pedalboard

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_fairchild_660.vst3"
SRC = "/Users/ship/Documents/code/ship-studios/projects/watercolors/mix/bus_warm.wav"
OUT = "/Users/ship/Documents/code/ship-studios/artifacts/fc660"
EXCERPT_S = 20.0


def first_num(x):
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace("∞", "inf"))
    return float(m.group()) if m else None


def set_param(p, name, value):
    """Exact setattr first; else snap a numeric target to the nearest numeric valid_value
    (handles '60 Hz' -> 60, '-inf', etc.). Returns a note when it snaps/fails."""
    try:
        setattr(p, name, value)
        return None
    except Exception as ex:
        try:
            vv = list(getattr(p.parameters[name], "valid_values", []) or [])
        except Exception:
            return f"{name}={value!r}: {str(ex)[:80]}"
        tn = first_num(value)
        cand = [(abs(first_num(v) - tn), v) for v in vv if first_num(v) is not None]
        if tn is not None and cand:
            best = min(cand, key=lambda t: t[0])[1]
            setattr(p, name, best)
            return f"{name}={value!r}->{best!r}"
        return f"{name}={value!r}: no-snap"


def metrics(y):
    peak = float(np.max(np.abs(y))) + 1e-12
    rms = float(np.sqrt(np.mean(y ** 2))) + 1e-12
    return 20 * np.log10(peak), 20 * np.log10(rms), 20 * np.log10(peak / rms)


# Base settings; each render overrides a subset. meter is display-only.
BASE = dict(meter="GR", input=-14.0, thresh=5.0, time_const=1.0, sc_filt="Off",
            bal=0.0, dc_thr=7.5, output=0.0, mix=100.0, headroom=16.0,
            power=True, master_bypass=False)

RENDERS = []
RENDERS.append(("_bypass", {**BASE, "master_bypass": True}))
# A: input drive (tc=4, thresh=5)
for v in (-14, -10, -6, -2, 0):
    RENDERS.append((f"a_in{v}", {**BASE, "input": float(v), "time_const": 4.0, "thresh": 5.0}))
# B: threshold direction (input=-4, tc=4)
for v in (2, 4, 6, 8):
    RENDERS.append((f"b_th{v}", {**BASE, "input": -4.0, "time_const": 4.0, "thresh": float(v)}))
# C: time constant (input=-4, thresh=5)
for v in (1, 2, 3, 4, 5, 6):
    RENDERS.append((f"c_tc{v}", {**BASE, "input": -4.0, "thresh": 5.0, "time_const": float(v)}))
# D: sidechain filter (input=-2, thresh=4, tc=4)
for v in ("Off", "60 Hz", "120 Hz", "250 Hz"):
    tag = "off" if v == "Off" else v.split()[0]
    RENDERS.append((f"d_sc{tag}", {**BASE, "input": -2.0, "thresh": 4.0, "time_const": 4.0, "sc_filt": v}))
# E: parallel mix (heavy: input=0, thresh=2, tc=2)
for v in (100, 75, 50, 25):
    RENDERS.append((f"e_mix{v}", {**BASE, "input": 0.0, "thresh": 2.0, "time_const": 2.0, "mix": float(v)}))
# F: headroom (input=-4, thresh=5, tc=4)
for v in (8, 16, 24):
    RENDERS.append((f"f_hr{v}", {**BASE, "input": -4.0, "thresh": 5.0, "time_const": 4.0, "headroom": float(v)}))


def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    audio, sr = sf.read(SRC, dtype="float32", always_2d=True)
    x = audio.T.copy()
    n = int(EXCERPT_S * sr)
    x = x[:, :n] if x.shape[1] > n else x
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    sf.write(f"{OUT}/_src.wav", x.T, sr, subtype="FLOAT")
    sp, sr_, scr = metrics(x)
    print(f"{'name':10} {'peak':>7} {'rms':>7} {'crest':>6}   params")
    print(f"{'_src':10} {sp:7.2f} {sr_:7.2f} {scr:6.2f}")
    for name, params in RENDERS:
        p = load_plugin(PLUG)
        notes = [set_param(p, k, v) for k, v in params.items()]
        notes = [s for s in notes if s]
        y = Pedalboard([p])(x, sr)
        sf.write(f"{OUT}/{name}.wav", y.T, sr, subtype="FLOAT")
        pk, rm, cr = metrics(y)
        key = {k: params[k] for k in ("input", "thresh", "time_const", "sc_filt", "mix", "headroom") if params[k] != BASE[k]}
        if params.get("master_bypass"):
            key = {"bypass": True}
        warn = ("  WARN " + "; ".join(notes)) if notes else ""
        print(f"{name:10} {pk:7.2f} {rm:7.2f} {cr:6.2f}   {key}{warn}")


if __name__ == "__main__":
    raise SystemExit(main())
