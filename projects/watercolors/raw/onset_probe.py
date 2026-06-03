#!/usr/bin/env python3
"""Onset density + rhythmic regularity per channel over a loud 30s window.
Snare = many regular onsets (backbeats); toms = sparse/bursty; hat = very dense."""
import glob, os
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

RAW = os.path.dirname(os.path.abspath(__file__))
START, DUR, SR = 180, 30, 48000
files = sorted(glob.glob(os.path.join(RAW, "*.wav")))

def onset_env(x, sr, fmin=200, fmax=8000):
    sos = butter(2, [fmin, min(fmax, sr/2-1)], btype="band", fs=sr, output="sos")
    xf = sosfilt(sos, x)
    # energy envelope, 10ms hops
    hop = int(0.005*sr); win = int(0.02*sr)
    env = np.array([np.sqrt(np.mean(xf[i:i+win]**2)) for i in range(0, len(xf)-win, hop)])
    return env, sr/hop  # env, frames per sec

def peaks(env, fps, thresh_rel=0.30, min_gap_s=0.08):
    if env.max() <= 0: return []
    e = env/env.max()
    # spectral-flux-ish: positive diff
    d = np.diff(e, prepend=e[0]); d[d<0]=0
    cand = np.where((e[1:-1] > thresh_rel) & (e[1:-1] >= e[:-2]) & (e[1:-1] >= e[2:]))[0]+1
    onsets=[]; last=-1e9
    for c in cand:
        t = c/fps
        if t-last >= min_gap_s:
            onsets.append(t); last=t
    return onsets

print(f"window {START}-{START+DUR}s")
print(f"{'channel':14} {'onsets/30s':>10} {'/sec':>6} {'IOI_med':>8} {'IOI_cv':>7}  pattern")
print("-"*72)
for f in files:
    name = os.path.basename(f).replace('.wav','')
    if name == 'a_adat4': continue
    x, sr = sf.read(f, start=START*SR, frames=DUR*SR, always_2d=True)
    x = x.mean(axis=1)
    env, fps = onset_env(x, sr)
    on = peaks(env, fps)
    n = len(on)
    if n >= 3:
        ioi = np.diff(on)
        med = np.median(ioi); cv = np.std(ioi)/(np.mean(ioi)+1e-9)
    else:
        med = cv = float('nan')
    persec = n/DUR
    pat = ("dense/hat-like" if persec>3.5 else
           "regular/snare-like" if (1.0<=persec<=3.5 and cv==cv and cv<0.9) else
           "sparse/tom-like" if persec<1.2 else "mixed")
    print(f"{name:14} {n:10d} {persec:6.2f} {med:8.3f} {cv:7.2f}  {pat}")
