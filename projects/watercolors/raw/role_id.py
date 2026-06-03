#!/usr/bin/env python3
"""Signal-based role ID for the Watercolors raw drum channels.
Computes per-channel spectral centroid, band energy ratios, crest, onset density,
plus a cross-channel correlation matrix (to find OH/room pairs)."""
import glob, os
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

RAW = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(RAW, "*.wav")))

def band_energy(x, sr, lo, hi):
    if hi >= sr/2: hi = sr/2 - 1
    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    return float(np.mean(sosfilt(sos, x)**2))

def centroid(x, sr):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) if len(x) < 1<<22 else None
    # use Welch-ish: chunked average to keep memory sane
    n = 1<<15
    acc = np.zeros(n//2+1); cnt=0
    for i in range(0, len(x)-n, n):
        seg = x[i:i+n]*np.hanning(n)
        acc += np.abs(np.fft.rfft(seg)); cnt+=1
    if cnt==0: return 0.0
    mag = acc/cnt
    freqs = np.fft.rfftfreq(n, 1/sr)
    if mag.sum()==0: return 0.0
    return float((freqs*mag).sum()/mag.sum())

def analyze(path):
    x, sr = sf.read(path, always_2d=True)
    x = x.mean(axis=1)  # mono for analysis
    peak = np.max(np.abs(x))+1e-12
    rms = np.sqrt(np.mean(x**2))+1e-12
    crest = 20*np.log10(peak/rms)
    tot = float(np.mean(x**2))+1e-15
    sub  = band_energy(x, sr, 20, 60)/tot
    low  = band_energy(x, sr, 60, 150)/tot
    lmid = band_energy(x, sr, 150, 500)/tot
    mid  = band_energy(x, sr, 500, 2000)/tot
    hmid = band_energy(x, sr, 2000, 6000)/tot
    high = band_energy(x, sr, 6000, 16000)/tot
    cen = centroid(x, sr)
    return dict(name=os.path.basename(path), sr=sr, peak_db=20*np.log10(peak),
                rms_db=20*np.log10(rms), crest=crest, centroid=cen,
                sub=sub, low=low, lmid=lmid, mid=mid, hmid=hmid, high=high)

rows = [analyze(f) for f in files]
print(f"{'channel':16} {'cen_Hz':>7} {'crest':>6} | {'sub':>5} {'low':>5} {'lmid':>5} {'mid':>5} {'hmid':>5} {'high':>5}")
print("-"*80)
for r in rows:
    print(f"{r['name'].replace('.wav',''):16} {r['centroid']:7.0f} {r['crest']:6.1f} | "
          f"{r['sub']:5.2f} {r['low']:5.2f} {r['lmid']:5.2f} {r['mid']:5.2f} {r['hmid']:5.2f} {r['high']:5.2f}")

# correlation matrix on a loud 30s window (downsampled envelope for speed)
print("\n=== cross-channel correlation (|r| of 30s envelope, finds pairs) ===")
sigs = {}
for f in files:
    x, sr = sf.read(f, start=int(60*48000), frames=int(30*48000), always_2d=True)
    sigs[os.path.basename(f).replace('.wav','')] = np.abs(x.mean(axis=1))
names = list(sigs.keys())
print(f"{'':14}" + "".join(f"{n[:7]:>8}" for n in names))
for a in names:
    line = f"{a[:13]:14}"
    for b in names:
        r = np.corrcoef(sigs[a], sigs[b])[0,1]
        line += f"{r:8.2f}"
    print(line)
