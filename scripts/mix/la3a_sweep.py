"""Isolation sweep for the UADx Teletronix LA-3A — measure what each control actually does, headless.

Renders a drum-bus excerpt (and a 1 kHz tone) through `uaudio_la3a.vst3` at a matrix of settings,
RAW (no normalization) so gain-reduction / crest / level are readable, and prints a table per sweep:
RMS, sample-peak, crest, 4-band spectral ratios, centroid, and (for the tone) THD%.

The LA-3A param surface (Pedalboard, all 8 enums): peak_reduction 0..10, gain 0..10 (makeup),
comp_limit 'Comp'/'Limit', meter 'Off'/'GR'/'Output' (display only), hf_emphasis 0..100 (sidechain
HF), mix 0..100 (parallel), power, master_bypass. apply-vst-chain's float dict CAN set the numeric
enums but NOT the strings (comp_limit/meter) -> the preset harness owns those.

Usage:
    python la3a_sweep.py [in.wav] [excerpt_seconds]
Run with the stemmy-loops `vst` venv (has pedalboard).
"""
import sys
import numpy as np
import soundfile as sf
from pedalboard import load_plugin

PLUGIN = "/Library/Audio/Plug-Ins/VST3/uaudio_la3a.vst3"
IN = sys.argv[1] if len(sys.argv) > 1 else \
    "/Users/ship/Documents/code/ship-studios/projects/watercolors/mix/bus_warm.wav"
EXCERPT = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

DEFAULTS = dict(peak_reduction=3.6, gain=5.0, comp_limit="Comp", meter="GR",
                hf_emphasis=0.0, mix=100.0, power=True, master_bypass=False)


def render(x, sr, **over):
    p = load_plugin(PLUGIN)
    for k, v in {**DEFAULTS, **over}.items():
        setattr(p, k, v)
    return p(x, sr)


def stats(y):
    m = y if y.ndim == 1 else y.mean(0)
    rms = float(np.sqrt(np.mean(m ** 2)))
    pk = float(np.max(np.abs(m)))
    rdb = 20 * np.log10(rms + 1e-12)
    pdb = 20 * np.log10(pk + 1e-12)
    return rdb, pdb, pdb - rdb


def bands(y, sr):
    """4-band energy ratios (sub/low <120, low-mid 120-2k, presence 2k-8k, air >8k) + centroid."""
    m = y if y.ndim == 1 else y.mean(0)
    f = np.fft.rfftfreq(len(m), 1 / sr)
    P = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    tot = P.sum() + 1e-20
    edges = [0, 120, 2000, 8000, sr / 2]
    r = [P[(f >= edges[i]) & (f < edges[i + 1])].sum() / tot for i in range(4)]
    cen = float((f * P).sum() / tot)
    return r, cen


def thd(y, sr, f0=1000.0):
    """THD% of a tone: sqrt(sum harmonic^2)/fundamental, from the Welch-ish single FFT."""
    m = y if y.ndim == 1 else y.mean(0)
    n = len(m)
    w = np.hanning(n)
    P = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(n, 1 / sr)
    def amp(fc):
        k = np.argmin(np.abs(f - fc))
        return P[max(0, k - 2):k + 3].max()
    fund = amp(f0)
    harm = np.sqrt(sum(amp(f0 * h) ** 2 for h in range(2, 9)))
    return 100 * harm / (fund + 1e-20)


def main():
    audio, sr = sf.read(IN, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    x = x[:, : int(EXCERPT * sr)]
    rdb0, pdb0, cr0 = stats(x)
    r0, c0 = bands(x, sr)
    print(f"SOURCE ({IN.split('/')[-1]}, {EXCERPT:g}s): RMS {rdb0:.1f}  peak {pdb0:.1f}  crest {cr0:.1f}  "
          f"centroid {c0:.0f}  bands {[round(v,3) for v in r0]}")

    def row(label, y, ref_rms=None):
        rdb, pdb, cr = stats(y)
        r, c = bands(y, sr)
        gr = f"  Δrms {rdb-ref_rms:+.1f}" if ref_rms is not None else ""
        print(f"  {label:26} RMS {rdb:6.1f}  peak {pdb:6.1f}  crest {cr:5.1f}  cen {c:5.0f}  "
              f"bands {[round(v,3) for v in r]}{gr}")
        return rdb

    print("\n== PEAK REDUCTION sweep (comp, gain 5, hf 0) — Δrms vs pr0 = leveling ==")
    base = None
    for pr in [0, 2, 4, 6, 8, 10]:
        y = render(x, sr, peak_reduction=float(pr))
        rdb = row(f"pr {pr}", y, base)
        if pr == 0:
            base = rdb

    print("\n== COMP vs LIMIT (pr 6, gain 5, hf 0) ==")
    for mode in ["Comp", "Limit"]:
        row(f"{mode} pr6", render(x, sr, peak_reduction=6.0, comp_limit=mode))
    print("   (also at pr 8)")
    for mode in ["Comp", "Limit"]:
        row(f"{mode} pr8", render(x, sr, peak_reduction=8.0, comp_limit=mode))

    print("\n== HF EMPHASIS sweep (comp, pr 6, gain 5) — watch centroid + presence/air bands ==")
    for hf in [0, 25, 50, 75, 100]:
        row(f"hf {hf}", render(x, sr, peak_reduction=6.0, hf_emphasis=float(hf)))

    print("\n== GAIN (makeup) linearity (pr 0, comp, hf 0) ==")
    for g in [3, 5, 7]:
        row(f"gain {g}", render(x, sr, peak_reduction=0.0, gain=float(g)))

    print("\n== MIX / parallel (Limit pr 9, gain 5) ==")
    for mx in [100, 50, 25, 0]:
        row(f"mix {mx}", render(x, sr, peak_reduction=9.0, comp_limit="Limit", mix=float(mx)))

    print("\n== REST state: true-bypass vs engaged-flat (does it color/level at rest?) ==")
    row("master_bypass", render(x, sr, master_bypass=True))
    row("power off", render(x, sr, power=False))
    row("engaged pr0 gain5", render(x, sr, peak_reduction=0.0, gain=5.0))

    print("\n== 1 kHz tone THD (-12 dBFS) — harmonic signature (solid-state opto: clean?) ==")
    t = np.arange(int(2.0 * sr)) / sr
    tone = (10 ** (-12 / 20) * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    tone = np.stack([tone, tone], 0)
    print(f"  tone source THD {thd(tone, sr):.3f}%")
    for label, kw in [("bypass", dict(master_bypass=True)),
                      ("comp pr3", dict(peak_reduction=3.0)),
                      ("comp pr6", dict(peak_reduction=6.0)),
                      ("comp pr9", dict(peak_reduction=9.0)),
                      ("limit pr9", dict(peak_reduction=9.0, comp_limit="Limit"))]:
        y = render(tone, sr, **kw)
        _, _, _ = stats(y)
        print(f"  tone {label:12} THD {thd(y, sr):.3f}%   rms {stats(y)[0]:.1f}")


if __name__ == "__main__":
    main()
