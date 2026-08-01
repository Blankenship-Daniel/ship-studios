"""Isolation/characterization sweep for the UADx Vibe Analog Machines (uaudio_verve.vst3).

The binary's internal codename is 'verve' but it reports its product name as 'UADx Vibe Analog Machines'.
Loads the plugin fresh per render (state isolation) and exercises its 6-param surface:
  machine (string enum, 10 voicings) · param_1 = DRIVE · param_2 = WARBLE · output_trim (clean dB) ·
  power / master_bypass.

It does three things:
  1) DRUM renders (per machine @ drive 40, a drive sweep, a warble setting) -> FLOAT32 WAVs in OUT/,
     so you can run the MCP meters (measure-spectrum / measure-loudness / measure-microdynamics) on them
     for the authoritative tonal/dynamic numbers cited in docs/vst/vibe-analog-machines.md.
  2) A 1 kHz TONE THD pass (computed inline) per machine + a drive sweep -> the harmonic character
     (THD %, even-vs-odd) that distinguishes the machines.
  3) A WARBLE pass on a tone -> the fundamental-concentration metric that PROVES warble is pitch
     modulation (invisible to the spectrum/crest meters; collapses 1.00 -> ~0.08 as warble 0 -> 100).

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/vibe_sweep.py
"""
import os
import numpy as np
import soundfile as sf
from pedalboard import load_plugin, Pedalboard
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

ROOT = repo_root()

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3"
SRC = f"{ROOT}/artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav"
OUT = f"{ROOT}/artifacts/vibe-char"
SR = 48000
MACHINES = ["THICKEN", "VINTAGIZE", "OVERDRIVE", "EDGE", "SPUTTER",
            "GLOW", "DISTORT", "SWEETEN", "WARM", "FIRE"]


def mk(machine="SWEETEN", drive=40.0, warble=0.0, trim=0.0, bypass=False):
    p = load_plugin(PLUG)
    p.machine = machine
    p.param_1 = float(drive)
    p.param_2 = float(warble)
    p.output_trim = float(trim)
    p.master_bypass = bypass
    p.power = True
    return p


def render(p, x):
    return Pedalboard([p])(x, SR)


def crest(y):
    pk = float(np.max(np.abs(y))) + 1e-12
    rms = float(np.sqrt(np.mean(y ** 2))) + 1e-12
    return 20 * np.log10(pk / rms)


def tone(f0=1000.0, dur=1.5, dbfs=-12.0):
    n = int(SR * dur)
    s = (10 ** (dbfs / 20) * np.sin(2 * np.pi * f0 * np.arange(n) / SR)).astype(np.float32)
    return np.stack([s, s], 0)


def thd(y, f0=1000.0):
    """THD% + even/odd balance of a steady tone (middle window, Hann)."""
    s = y[0]
    c = len(s) // 2
    w = int(0.4 * SR)
    seg = s[c - w:c + w].astype(np.float64) * np.hanning(2 * w)
    sp = np.abs(np.fft.rfft(seg))
    fr = np.fft.rfftfreq(len(seg), 1 / SR)

    def amp(f):
        k = np.argmin(np.abs(fr - f))
        return float(np.sqrt(np.sum(sp[max(0, k - 2):k + 3] ** 2)))

    f1 = amp(f0) + 1e-12
    h = np.array([amp(k * f0) for k in range(2, 13)])
    even = np.sqrt(np.sum(h[0::2] ** 2))
    odd = np.sqrt(np.sum(h[1::2] ** 2))
    return 100 * np.sqrt(np.sum(h ** 2)) / f1, ("EVEN" if even > odd else "ODD")


def fund_concentration(y, f0=1000.0):
    """1.0 = pure tone; lower = warble smears the fundamental (pitch modulation)."""
    s = y[0]
    c = len(s) // 2
    w = int(0.5 * SR)
    seg = s[c - w:c + w].astype(np.float64) * np.hanning(2 * w)
    sp = np.abs(np.fft.rfft(seg)) ** 2
    fr = np.fft.rfftfreq(len(seg), 1 / SR)
    band = (fr > f0 - 60) & (fr < f0 + 60)
    k = np.argmin(np.abs(fr - f0))
    return float(np.sum(sp[k - 1:k + 2]) / (np.sum(sp[band]) + 1e-12))


def main():
    os.makedirs(OUT, exist_ok=True)
    x, sr = sf.read(SRC, dtype="float32", always_2d=True)
    x = x.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    sf.write(f"{OUT}/_src.wav", x.T, sr, subtype="FLOAT")

    print(f"# DRUM renders (FLOAT, no peak-trim) -> {OUT}/  (run MCP meters on these)")
    print(f"{'name':22} {'crest':>6}")
    print(f"{'_src':22} {crest(x):6.2f}")
    sf.write(f"{OUT}/_bypass.wav", render(mk(bypass=True), x).T, sr, subtype="FLOAT")
    for m in MACHINES:
        y = render(mk(m, 40), x)
        sf.write(f"{OUT}/m_{m.lower()}_d40.wav", y.T, sr, subtype="FLOAT")
        print(f"{m + ' d40':22} {crest(y):6.2f}")

    print("\n# 1 kHz TONE THD per machine @ drive 40 / 80")
    print(f"{'machine':12} {'THD@40':>8} {'bal40':>5} {'THD@80':>8} {'bal80':>5}")
    for m in MACHINES:
        t40, b40 = thd(render(mk(m, 40), tone()))
        t80, b80 = thd(render(mk(m, 80), tone()))
        print(f"{m:12} {t40:7.2f}% {b40:>5} {t80:7.2f}% {b80:>5}")

    print("\n# WARBLE = pitch modulation (SWEETEN d40, tone). 1.0 pure -> lower = wobble; rms ~constant")
    for wv in (0, 15, 30, 50, 75, 100):
        y = render(mk("SWEETEN", 40, wv), tone())
        print(f"  warble {wv:3}  fund-concentration={fund_concentration(y):.4f}  "
              f"rms={float(np.sqrt(np.mean(y ** 2))):.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
