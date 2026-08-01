"""Isolation/characterization sweep for the UADx dbx 160 Compressor (uaudio_dbx_160.vst3).

Loads the plugin fresh per render (state isolation), sets its enum params via a tolerant
setattr-with-nearest-valid snap (the ratio `compress` and `meter`/`sc_filter` are enums),
processes a drum-bus excerpt, and writes FLOAT32 WAVs (no peak trim) so the real level /
GR / crest survive measurement. Also renders a 1 kHz tone at a few ratios so the VCA's
harmonic signature can be read with `[L] measure-distortion`.

Prints quick numpy peak/RMS/crest per render; use the MCP meters (measure-loudness /
measure-microdynamics / measure-spectrum / measure-distortion) on the written files for the
authoritative numbers cited in docs/vst/dbx-160.md.

The dbx 160 question this answers: does a feed-forward true-RMS VCA comp ADD or REDUCE crest
on drums? (RMS detection + program-dependent release is famous for keeping/adding punch.)

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/dbx160_sweep.py
"""
import os
import re
import numpy as np
import soundfile as sf
from pedalboard import load_plugin, Pedalboard
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

ROOT = repo_root()

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_dbx_160.vst3"
SRC = f"{ROOT}/projects/watercolors/mix/bus_warm.wav"
OUT = f"{ROOT}/artifacts/dbx160"
EXCERPT_S = 20.0


def first_num(x):
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace("∞", "inf").replace("Inf", "inf"))
    return float(m.group()) if m else None


def set_param(p, name, value):
    """Exact setattr first; else snap a numeric target to the nearest numeric valid_value
    (handles ' 4.0:1' -> 4.0, '10.0:1', etc.). Returns a note when it snaps/fails."""
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


# Base settings; each render overrides a subset. meter is display-only, gain 0 = no makeup
# (so the RMS drop = the real gain reduction; make up later). thresh is in dBFS on the plugin.
BASE = dict(thresh=-30.0, compress=" 4.0:1", gain=0.0, meter="GC",
            sc_filter=False, mix=100.0, power=True, master_bypass=False)

RENDERS = []
RENDERS.append(("_bypass", {**BASE, "master_bypass": True}))
# A: ratio sweep (the signature control) at a fixed engaging threshold
for v in (" 1.5:1", " 2.0:1", " 4.0:1", "10.0:1", "20.0:1", "Inf:1"):
    tag = first_num(v)
    tag = "inf" if tag is None or tag > 60 else f"{tag:g}"
    RENDERS.append((f"a_ratio{tag}", {**BASE, "thresh": -30.0, "compress": v}))
# B: threshold sweep (the amount/GR) at 4:1
for v in (-40, -35, -30, -25, -20, -15):
    RENDERS.append((f"b_thr{abs(v)}", {**BASE, "compress": " 4.0:1", "thresh": float(v)}))
# C: sidechain filter (PULL/SC) off vs on, at a kick-pumping setting (6:1, lower thr)
for v in (False, True):
    RENDERS.append((f"c_sc{'on' if v else 'off'}", {**BASE, "thresh": -33.0, "compress": " 6.0:1", "sc_filter": v}))
# D: parallel mix at a heavy setting (20:1, low thr)
for v in (100, 50, 25):
    RENDERS.append((f"d_mix{v}", {**BASE, "thresh": -36.0, "compress": "20.0:1", "mix": float(v)}))
# E: gain makeup linearity at 1:1 (no compression -> pure makeup)
for v in (-6, 0, 6):
    RENDERS.append((f"e_gain{v:+d}", {**BASE, "compress": " 1.0:1", "thresh": -30.0, "gain": float(v)}))


def tone(freq, sec, sr, dbfs):
    t = np.arange(int(sec * sr)) / sr
    a = 10 ** (dbfs / 20.0)
    s = (a * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([s, s], 0)


def drum_sweep(x, sr):
    sf.write(f"{OUT}/_src.wav", x.T, sr, subtype="FLOAT")
    sp, sr_, scr = metrics(x)
    print(f"{'name':12} {'peak':>7} {'rms':>7} {'crest':>6}   params")
    print(f"{'_src':12} {sp:7.2f} {sr_:7.2f} {scr:6.2f}")
    for name, params in RENDERS:
        p = load_plugin(PLUG)
        notes = [set_param(p, k, v) for k, v in params.items()]
        notes = [s for s in notes if s]
        y = Pedalboard([p])(x, sr)
        sf.write(f"{OUT}/{name}.wav", y.T, sr, subtype="FLOAT")
        pk, rm, cr = metrics(y)
        key = {k: params[k] for k in ("thresh", "compress", "sc_filter", "mix", "gain") if params[k] != BASE[k]}
        if params.get("master_bypass"):
            key = {"bypass": True}
        warn = ("  WARN " + "; ".join(notes)) if notes else ""
        print(f"{name:12} {pk:7.2f} {rm:7.2f} {cr:6.2f}   {key}{warn}")


def tone_probe(sr=48000):
    """Render a 1 kHz tone at -12 dBFS through the dbx at 1:1 (clean ref), 4:1, and Inf:1
    (limiting). Measure THD on these with measure-distortion to read the VCA color."""
    x = tone(1000.0, 3.0, sr, -12.0)
    sf.write(f"{OUT}/tone_src.wav", x.T, sr, subtype="FLOAT")
    cases = [("tone_ratio1", " 1.0:1", -30.0), ("tone_ratio4", " 4.0:1", -36.0), ("tone_inf", "Inf:1", -36.0)]
    print("\n-- 1 kHz tone renders (measure THD with measure-distortion) --")
    for name, comp, thr in cases:
        p = load_plugin(PLUG)
        for k, v in dict(thresh=thr, compress=comp, gain=0.0, meter="GC",
                         sc_filter=False, mix=100.0, power=True, master_bypass=False).items():
            set_param(p, k, v)
        y = Pedalboard([p])(x, sr)
        sf.write(f"{OUT}/{name}.wav", y.T, sr, subtype="FLOAT")
        pk, rm, cr = metrics(y)
        print(f"{name:12} {pk:7.2f} {rm:7.2f} {cr:6.2f}   compress={comp} thr={thr}")


def main():
    os.makedirs(OUT, exist_ok=True)
    audio, sr = sf.read(SRC, dtype="float32", always_2d=True)
    x = audio.T.copy()
    n = int(EXCERPT_S * sr)
    x = x[:, :n] if x.shape[1] > n else x
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    drum_sweep(x, sr)
    tone_probe(sr)


if __name__ == "__main__":
    raise SystemExit(main())
