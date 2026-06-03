"""Measurement provenance for the UADx Pultec MEQ-5 deep-dive (docs/vst/pultec-meq-5.md, Part A).

Welch cross-spectral transfer function on a fixed white-noise buffer (same input through every state =>
the source spectrum cancels, leaving H(f)) + a 1 kHz-sine THD sweep. Reproduces every Part A number:
render-proof, true-null, amount->dB calibration per section, curve shapes, the boost+dip overlap, the
output trim, the always-on magnitude imprint, and harmonic coloration vs input level.

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/meq5_sweep.py
"""
import numpy as np
from scipy.signal import welch
from pedalboard import load_plugin

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_pultec_meq-5.vst3"  # the UADx build that renders headless
SR = 48000
rng = np.random.default_rng(20260603)
x = rng.standard_normal(SR * 20).astype(np.float32)
x *= (10 ** (-18 / 20.0)) / (np.sqrt(np.mean(x ** 2)) + 1e-12)   # white, -18 dBFS RMS
X = np.stack([x, x], 0)

# default-engaged-flat base; override per case. 'CPS' = Hz, 'KCS' = kHz (vintage labels).
BASE = dict(power=True, master_bypass=False, enable="In",
            lm_freq="200 CPS", lm_peak=0.0, mid_freq="700 CPS", mid_dip=0.0,
            hm_freq="1.5 KCS", hm_peak=0.0, output="0.0 dB")
PROBE = [30, 50, 80, 125, 160, 200, 250, 300, 400, 500, 600, 700, 800, 1000, 1250, 1500,
         2000, 2500, 3000, 3500, 4000, 5000, 7000, 10000, 15000]


def render(over, sig=X):
    p = load_plugin(PLUG)
    for k, v in {**BASE, **over}.items():
        setattr(p, k, v)
    return p(sig, SR)[0]


def curve(y, ref, probes=PROBE):
    f, Pc = welch(y, SR, nperseg=8192); _, Pr = welch(ref, SR, nperseg=8192)
    H = 10 * np.log10((Pc + 1e-20) / (Pr + 1e-20))
    return {fr: round(float(np.interp(fr, f, H)), 2) for fr in probes}


def thd(sig):
    w = np.hanning(len(sig)); S = np.abs(np.fft.rfft(sig * w)); fr = np.fft.rfftfreq(len(sig), 1 / SR)
    band = lambda c: np.sqrt(np.sum(S[int(np.argmin(np.abs(fr - c))) - 3:int(np.argmin(np.abs(fr - c))) + 4] ** 2))
    return 100 * np.sqrt(sum(band(1000 * n) ** 2 for n in range(2, 9))) / (band(1000) + 1e-20)


yflat = render({}); ybyp = render({"master_bypass": True})
print("RENDER-PROOF  max|hm10@3k - flat| =", round(float(np.max(np.abs(render({'hm_freq':'3 KCS','hm_peak':10.0}) - yflat))), 4))
print("TRUE-NULL     max|bypass - dry|   =", round(float(np.max(np.abs(ybyp - X[0]))), 6))
print("ALWAYS-ON magnitude (enableIn0/bypass):", curve(yflat, ybyp, [30, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 15000]))

print("\nAMOUNT->dB  LOW PEAK @500:", {a: curve(render({'lm_freq':'500 CPS','lm_peak':float(a)}), yflat, [500])[500] for a in (2,4,6,8,10)})
print("AMOUNT->dB  DIP @1k:      ", {a: curve(render({'mid_freq':'1 KCS','mid_dip':float(a)}), yflat, [1000])[1000] for a in (2,4,6,8,10)})
print("AMOUNT->dB  HIGH PEAK @3k:", {a: curve(render({'hm_freq':'3 KCS','hm_peak':float(a)}), yflat, [3000])[3000] for a in (2,4,6,8,10)})

print("\nCURVE LOW PEAK @200 a10:", curve(render({'lm_freq':'200 CPS','lm_peak':10.0}), yflat))
print("CURVE LOW PEAK @1000 a10:", curve(render({'lm_freq':'1000 CPS','lm_peak':10.0}), yflat))
print("CURVE DIP @3k a10:", curve(render({'mid_freq':'3 KCS','mid_dip':10.0}), yflat))
print("CURVE HIGH PEAK @1.5k a10:", curve(render({'hm_freq':'1.5 KCS','hm_peak':10.0}), yflat))
print("CURVE HIGH PEAK @5k a10:", curve(render({'hm_freq':'5 KCS','hm_peak':10.0}), yflat))

print("\nOVERLAP boost700(lm10)+dip700(mid10):", curve(render({'lm_freq':'700 CPS','lm_peak':10.0,'mid_freq':'700 CPS','mid_dip':10.0}), yflat))
print("OUTPUT +6:", curve(render({'output':'6.0 dB'}), yflat, [100, 1000, 8000]))

print("\nTHD% by input level (1 kHz):")
t = np.arange(SR * 2) / SR
for lvl in (-18, -12, -6, 0):
    s = ((10 ** (lvl / 20.0)) * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    print(f"  {lvl:+d} dBFS  bypass={thd(render({'master_bypass':True}, np.stack([s,s],0))):.3f}  enableIn0={thd(render({}, np.stack([s,s],0))):.3f}")
