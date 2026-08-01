"""Isolation/characterization sweep for the UADx Oxide Tape Recorder (uaudio_oxide_tape.vst3).

The simple/affordable UA tape machine (same team as the Ampex ATR-102 & Studer A800). Only 8 params:
  input_level (-12..+24 dB = the DRIVE / primary color) · output_level (-24..+12 dB = make-up) ·
  path_select Input/Repro · ips 7.5/15 IPS · emphasis_eq NAB/CCIR · noise_reduct bool ·
  power / master_bypass.

Two passes:
  1) DRUM renders (default, Input vs Repro, 7.5 vs 15, NAB vs CCIR, NR on/off, input-drive sweep) ->
     peak-normalized, reports spectral centroid / 5-pt tilt / crest so only the SHAPE is compared.
  2) 1 kHz TONE THD pass -> even-vs-odd harmonic character at a few drive levels.

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/oxide_sweep.py
"""
import os
import numpy as np
import soundfile as sf
from pedalboard import load_plugin, Pedalboard
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

ROOT = repo_root()

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_oxide_tape.vst3"
SRC = f"{ROOT}/artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav"
OUT = f"{ROOT}/artifacts/oxide-char"
SR = 48000


def mk(path="Repro", ips="15 IPS", eq="NAB", nr=False, inp=0.0, out=0.0, bypass=False):
    p = load_plugin(PLUG)
    p.path_select = path
    p.ips = ips
    p.emphasis_eq = eq
    p.noise_reduct = nr
    p.input_level = float(inp)
    p.output_level = float(out)
    p.master_bypass = bypass
    p.power = True
    return p


def render(p, x):
    return Pedalboard([p])(x, SR)


def peaknorm(y):
    return y / (np.max(np.abs(y)) + 1e-12)


def crest(y):
    pk = float(np.max(np.abs(y))) + 1e-12
    rms = float(np.sqrt(np.mean(y ** 2))) + 1e-12
    return 20 * np.log10(pk / rms)


def centroid(y):
    s = y[0].astype(np.float64)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    fr = np.fft.rfftfreq(len(s), 1 / SR)
    return float(np.sum(fr * sp) / (np.sum(sp) + 1e-12))


def bands(y):
    """LF (20-200) / HF (4k-16k) fractional energy -> tilt proxy."""
    s = y[0].astype(np.float64)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2
    fr = np.fft.rfftfreq(len(s), 1 / SR)
    tot = np.sum(sp) + 1e-12
    lo = np.sum(sp[(fr >= 20) & (fr < 200)]) / tot
    hi = np.sum(sp[(fr >= 4000) & (fr < 16000)]) / tot
    return lo, hi


def tone(f0=1000.0, dur=1.5, dbfs=-12.0):
    n = int(SR * dur)
    s = (10 ** (dbfs / 20) * np.sin(2 * np.pi * f0 * np.arange(n) / SR)).astype(np.float32)
    return np.stack([s, s], 0)


def thd(y, f0=1000.0):
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
    h = np.array([amp(k * f0) for k in range(2, 9)])
    h2, h3, h4, h5 = h[0], h[1], h[2], h[3]
    even = np.sqrt(h2 ** 2 + h4 ** 2)
    odd = np.sqrt(h3 ** 2 + h5 ** 2)
    thd_pct = 100 * np.sqrt(np.sum(h ** 2)) / f1
    db = lambda a: 20 * np.log10(a / f1 + 1e-12)
    return thd_pct, ("EVEN" if even > odd else "ODD"), db(h2), db(h3), db(h4), db(h5)


def row(name, y):
    lo, hi = bands(y)
    print(f"{name:34} cen={centroid(y):7.0f}  lo={lo:.3f} hi={hi:.4f}  crest={crest(y):5.2f}")


def main():
    os.makedirs(OUT, exist_ok=True)
    x, sr = sf.read(SRC, dtype="float32", always_2d=True)
    x = x.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    sf.write(f"{OUT}/_src.wav", x.T, sr, subtype="FLOAT")

    print(f"# DRUM renders (peak-normed; centroid/tilt/crest compare SHAPE). src crest={crest(x):.2f}\n")
    row("dry", peaknorm(x))
    row("bypass", peaknorm(render(mk(bypass=True), x)))
    row("default Repro/15/NAB +0", peaknorm(render(mk(), x)))
    row("Input mode (electronics only) +0", peaknorm(render(mk(path="Input"), x)))
    print()
    row("Repro/15/NAB +6", peaknorm(render(mk(inp=6), x)))
    row("Repro/7.5/NAB +6", peaknorm(render(mk(ips="7.5 IPS", inp=6), x)))
    row("Repro/15/CCIR +6", peaknorm(render(mk(eq="CCIR", inp=6), x)))
    row("Repro/15/NAB +6 NR-on", peaknorm(render(mk(nr=True, inp=6), x)))
    print()
    print("# INPUT DRIVE sweep (Repro/15/NAB) -> saturation + tape compression")
    for d in (0, 6, 12, 18, 24):
        y = render(mk(inp=d), x)
        row(f"drive +{d}", peaknorm(y))
        sf.write(f"{OUT}/drive_{d}.wav", y.T, sr, subtype="FLOAT")

    print("\n# 1 kHz TONE THD (Repro/15/NAB): even vs odd, dB rel fundamental")
    print(f"{'drive':8} {'THD%':>7} {'bal':>5} {'H2':>6} {'H3':>6} {'H4':>6} {'H5':>6}")
    for d in (0, 6, 12, 18, 24):
        t, bal, h2, h3, h4, h5 = thd(render(mk(inp=d), tone()))
        print(f"+{d:<7}{t:7.2f}% {bal:>5} {h2:6.1f} {h3:6.1f} {h4:6.1f} {h5:6.1f}")
    print("# Input-mode (electronics, no tape) tone @ +12 for comparison")
    t, bal, h2, h3, h4, h5 = thd(render(mk(path="Input", inp=12), tone()))
    print(f"{'Input+12':8}{t:7.2f}% {bal:>5} {h2:6.1f} {h3:6.1f} {h4:6.1f} {h5:6.1f}")


if __name__ == "__main__":
    raise SystemExit(main())
