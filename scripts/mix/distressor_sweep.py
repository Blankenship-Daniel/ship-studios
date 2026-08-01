"""Isolation/characterization sweep for the UADx Empirical Labs Distressor (uaudio_distressor.vst3).

Two parts, both grounded in measurement (numbers cited in docs/vst/distressor.md):

  PART A — DRUM-BUS DYNAMICS: render the Watercolors warm drum bus through the Distressor while
  sweeping one control at a time (ratio / input-drive / attack / release / mix / detector), writing
  FLOAT32 WAVs (no peak trim, so real level + GR survive) and printing peak/RMS/crest. Crest drop =
  compression amount; crest direction across attack = punch vs clamp.

  PART B — SINE-PROBE HARMONICS: feed a steady 1 kHz tone and measure H2..H6 (dBc) + THD% for the
  AUDIO modes Norm / Dist 2 / Dist 3 at a couple of input drives, at ratio 1:1 (isolate the distortion
  stage) and 6:1 (distortion + compression). This is what proves "Dist 2 = 2nd harmonic, Dist 3 = 3rd".

Every Distressor param is an enum; ratio/detector/audio are STRING enums (the float dict can't pick
them) so we setattr with a tolerant nearest-valid snap, exactly like the preset harness.

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/distressor_sweep.py
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

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_distressor.vst3"
SRC = f"{ROOT}/projects/watercolors/mix/bus_warm.wav"
OUT = f"{ROOT}/artifacts/distressor"
SR = 48000
EXCERPT_S = 20.0

os.makedirs(OUT, exist_ok=True)


def first_num(x):
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace("∞", "inf"))
    return float(m.group()) if m else None


def set_param(p, name, value):
    """Exact setattr first; else snap a numeric target to the nearest numeric valid_value."""
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


def centroid(y, sr=SR):
    mono = y.mean(0) if y.ndim == 2 else y
    win = np.hanning(len(mono))
    mag = np.abs(np.fft.rfft(mono * win))
    f = np.fft.rfftfreq(len(mono), 1 / sr)
    return float(np.sum(f * mag) / (np.sum(mag) + 1e-12))


def render(params, x):
    p = load_plugin(PLUG)
    for k, v in params.items():
        note = set_param(p, k, v)
        if note:
            print(f"   warn: {note}")
    return Pedalboard([p])(x, SR)


# ---- PART A: drum-bus dynamics --------------------------------------------------------------
BASE = dict(bypass="Off", ratio="6:1", detector="Norm", audio="Norm",
            input=5.0, attack=5.0, release=5.0, output=6.5, mix=100.0,
            headroom=16.0, power=True, master_bypass=False)

RENDERS = [
    ("00_dry",            {}),  # special-cased: write the raw input
    ("01_default",        dict()),
    # ratio sweep at a drive that engages GR (input 8)
    ("10_ratio2_in8",     dict(ratio="2:1", input=8.0)),
    ("11_ratio4_in8",     dict(ratio="4:1", input=8.0)),
    ("12_ratio6_in8",     dict(ratio="6:1", input=8.0)),
    ("13_ratio10_in8",    dict(ratio="10:1", input=8.0)),
    ("14_ratio20_in8",    dict(ratio="20:1", input=8.0)),
    ("15_nuke_in8",       dict(ratio="NUKE", input=8.0)),
    # input drive sweep at 6:1
    ("20_in5",            dict(ratio="6:1", input=5.0)),
    ("21_in7",            dict(ratio="6:1", input=7.0)),
    ("22_in9",            dict(ratio="6:1", input=9.0)),
    ("23_in10",           dict(ratio="6:1", input=10.0)),
    # attack sweep at 10:1 in8 (does lower or higher number = faster?)
    ("30_atk0_r10",       dict(ratio="10:1", input=8.0, attack=0.0)),
    ("31_atk5_r10",       dict(ratio="10:1", input=8.0, attack=5.0)),
    ("32_atk10_r10",      dict(ratio="10:1", input=8.0, attack=10.0)),
    # release sweep at 10:1 in8
    ("40_rel0_r10",       dict(ratio="10:1", input=8.0, release=0.0)),
    ("41_rel10_r10",      dict(ratio="10:1", input=8.0, release=10.0)),
    # mix / parallel at NUKE in9 (heavy)
    ("50_nuke_mix100",    dict(ratio="NUKE", input=9.0, mix=100.0)),
    ("51_nuke_mix50",     dict(ratio="NUKE", input=9.0, mix=50.0)),
    ("52_nuke_mix30",     dict(ratio="NUKE", input=9.0, mix=30.0)),
    # detector HP (lows out of detector) vs Norm at 10:1 in8
    ("60_det_norm",       dict(ratio="10:1", input=8.0, detector="Norm")),
    ("61_det_hp",         dict(ratio="10:1", input=8.0, detector="HP")),
    ("62_det_emp",        dict(ratio="10:1", input=8.0, detector="Emp")),
    # audio Dist modes on the bus at 4:1 in7
    ("70_audio_norm",     dict(ratio="4:1", input=7.0, audio="Norm")),
    ("71_audio_dist2",    dict(ratio="4:1", input=7.0, audio="Dist 2")),
    ("72_audio_dist3",    dict(ratio="4:1", input=7.0, audio="Dist 3")),
]


def part_a():
    audio, sr = sf.read(SRC, dtype="float32", always_2d=True)
    assert sr == SR, f"expected {SR}, got {sr}"
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    x = x[:, : int(EXCERPT_S * SR)]
    pk, rm, cr = metrics(x)
    print("\n=== PART A: drum-bus dynamics (FLOAT32, no peak trim) ===")
    print(f"{'render':22} {'peak':>7} {'rms':>7} {'crest':>7} {'centHz':>7}")
    print(f"{'00_dry (input)':22} {pk:7.2f} {rm:7.2f} {cr:7.2f} {centroid(x):7.0f}")
    sf.write(f"{OUT}/00_dry.wav", x.T, SR, subtype="FLOAT")
    for name, over in RENDERS:
        if name == "00_dry":
            continue
        params = {**BASE, **over}
        y = render(params, x)
        pk, rm, cr = metrics(y)
        sf.write(f"{OUT}/{name}.wav", y.T, SR, subtype="FLOAT")
        print(f"{name:22} {pk:7.2f} {rm:7.2f} {cr:7.2f} {centroid(y):7.0f}")


# ---- PART B: sine-probe harmonics -----------------------------------------------------------
def sine(f0, secs, dbfs):
    n = int(secs * SR)
    t = np.arange(n) / SR
    a = 10 ** (dbfs / 20)
    s = (a * np.sin(2 * np.pi * f0 * t)).astype(np.float32)
    return np.stack([s, s], 0)


def harmonics(y, f0, sr=SR):
    mono = y.mean(0) if y.ndim == 2 else y
    # trim edges (settling) and window
    mono = mono[int(0.2 * sr): -int(0.2 * sr)]
    win = np.hanning(len(mono))
    mag = np.abs(np.fft.rfft(mono * win))
    freqs = np.fft.rfftfreq(len(mono), 1 / sr)

    def peak_near(f):
        idx = int(np.argmin(np.abs(freqs - f)))
        lo, hi = max(0, idx - 4), idx + 5
        return float(mag[lo:hi].max())

    fund = peak_near(f0) + 1e-12
    harms = {k: 20 * np.log10(peak_near(k * f0) / fund + 1e-12) for k in range(2, 7)}
    h_pow = sum(peak_near(k * f0) ** 2 for k in range(2, 12))
    thd = 100 * np.sqrt(h_pow) / fund
    return harms, thd


def part_b():
    f0 = 1000.0
    print("\n=== PART B: 1 kHz sine-probe harmonics (H_k in dBc relative to fundamental) ===")
    print(f"{'mode/ratio/in':28} {'H2':>7} {'H3':>7} {'H4':>7} {'H5':>7} {'THD%':>7}")
    combos = [
        ("Norm  1:1  in6", dict(ratio="1:1", audio="Norm",   input=6.0), -12),
        ("Dist2 1:1  in6", dict(ratio="1:1", audio="Dist 2", input=6.0), -12),
        ("Dist3 1:1  in6", dict(ratio="1:1", audio="Dist 3", input=6.0), -12),
        ("Norm  1:1  in10", dict(ratio="1:1", audio="Norm",   input=10.0), -12),
        ("Dist2 1:1  in10", dict(ratio="1:1", audio="Dist 2", input=10.0), -12),
        ("Dist3 1:1  in10", dict(ratio="1:1", audio="Dist 3", input=10.0), -12),
        ("Norm  6:1  in8", dict(ratio="6:1", audio="Norm",   input=8.0), -12),
        ("Dist2 6:1  in8", dict(ratio="6:1", audio="Dist 2", input=8.0), -12),
        ("Dist3 6:1  in8", dict(ratio="6:1", audio="Dist 3", input=8.0), -12),
        ("NUKE  in9", dict(ratio="NUKE", audio="Norm", input=9.0), -12),
    ]
    for label, over, dbfs in combos:
        params = {**BASE, **over, "output": 5.0}
        x = sine(f0, 2.0, dbfs)
        y = render(params, x)
        h, thd = harmonics(y, f0)
        print(f"{label:28} {h[2]:7.1f} {h[3]:7.1f} {h[4]:7.1f} {h[5]:7.1f} {thd:7.2f}")


if __name__ == "__main__":
    part_a()
    part_b()
    print(f"\nWAVs -> {OUT}/  (run MCP meters on these for authoritative LUFS/LRA/microdynamics)")
