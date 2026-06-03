"""Measured isolation sweep for the UADx LA-6176 Signature Channel Strip.

Characterises the three sections separately so the docs/skill are grounded in numbers, not lore:
  - PREAMP : 610 tube/transformer drive — THD% + H2/H3 on a 1 kHz tone across Line / Mic / Hi-Z paths,
             input_gain and the -15 dB pad; loop crest/centroid for the colour.
  - EQ     : the 610 2-band shelves — per-band dB delta vs EQ-bypassed (same preamp), confirms shelf
             shape, the gain-enum mapping, and the freq labels.
  - DYN    : 1176 (FET, fast, ratios incl ALL) vs LA2A (opto, slow) — loop crest/centroid + tone GR.

Run with the stemmy-loops `vst` venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/la6176_sweep.py [preamp|eq|dyn|all]

All 26 params are enums; we setattr exact strings/on-grid floats (snap numeric to nearest valid).
"""
import sys
import numpy as np
import soundfile as sf
from pedalboard import load_plugin, Pedalboard

PLUGIN = "/Library/Audio/Plug-Ins/VST3/uaudio_la_6176.vst3"
LOOP = "artifacts/watercolors-loops/seam/watercolors_drums_104bpm_4bar_a.wav"
SR = 48000

# ---------- helpers ----------

def fresh():
    return load_plugin(PLUGIN)


def setp(p, name, value):
    try:
        setattr(p, name, value)
        return
    except Exception:
        par = p.parameters[name]
        vv = list(getattr(par, "valid_values", []) or [])
        def num(x):
            try:
                return float(str(x).replace("∞", "inf"))
            except Exception:
                return None
        tn = num(value)
        cand = [(abs(num(v) - tn), v) for v in vv if num(v) is not None]
        if tn is not None and cand:
            setattr(p, name, min(cand, key=lambda t: t[0])[1])
        else:
            raise


def render(cfg, x):
    p = fresh()
    for k, v in cfg.items():
        setp(p, k, v)
    y = Pedalboard([p])(x.astype(np.float32), SR)
    return y[0] if y.ndim == 2 else y  # mono in -> take L


def tone(freq=1000.0, dbfs=-12.0, dur=1.0):
    t = np.arange(int(SR * dur)) / SR
    a = 10 ** (dbfs / 20.0)
    return (a * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def loop():
    x, sr = sf.read(LOOP, dtype="float32", always_2d=True)
    return x[:, 0]


def thd(y, f0=1000.0):
    """THD% + H2/H3 dB on a steady tone (skip edges for latency/transient)."""
    n = len(y)
    s = y[int(0.15 * n):int(0.9 * n)]
    s = s * np.hanning(len(s))
    sp = np.abs(np.fft.rfft(s))
    fr = np.fft.rfftfreq(len(s), 1 / SR)
    def amp(fc):
        k = np.argmin(np.abs(fr - fc))
        return float(np.max(sp[max(0, k - 3):k + 4]))
    fund = amp(f0)
    if fund <= 0:
        return float("nan"), float("nan"), float("nan")
    harms = [amp(f0 * h) for h in range(2, 11)]
    thd_pct = 100.0 * np.sqrt(np.sum(np.square(harms))) / fund
    h2 = 20 * np.log10(harms[0] / fund + 1e-12)
    h3 = 20 * np.log10(harms[1] / fund + 1e-12)
    return thd_pct, h2, h3


def specmetrics(y):
    """crest (dB), rms (dBFS), centroid (Hz), 5-band % of energy."""
    peak = float(np.max(np.abs(y))) + 1e-12
    rms = float(np.sqrt(np.mean(y ** 2))) + 1e-12
    crest = 20 * np.log10(peak / rms)
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    fr = np.fft.rfftfreq(len(y), 1 / SR)
    tot = np.sum(sp) + 1e-12
    centroid = float(np.sum(fr * sp) / tot)
    def band(lo, hi):
        return 100.0 * float(np.sum(sp[(fr >= lo) & (fr < hi)])) / tot
    return dict(crest=crest, rms=20 * np.log10(rms), centroid=centroid,
                low=band(0, 250), lomid=band(250, 500), mid=band(500, 2000),
                himid=band(2000, 6000), high=band(6000, 24000))


# clean reference: bypass everything
BYP = dict(master_bypass=True)
# unity-ish preamp pass (no EQ, no dyn) — input path/gain/pad/level vary per test
PRE = dict(eq_bypass="EQ Byp", dyn_bypass="Dyn Byp", input_select="Line",
           input_gain=0.0, input_pad="Off", cut_filter="Off", level=6.0)


def merge(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


# ---------- PREAMP ----------

def run_preamp():
    print("\n=== PREAMP  (1 kHz @ -12 dBFS tone -> THD;  drum loop -> crest/centroid)\n")
    x = tone()
    lx = loop()
    configs = {
        "bypass(null)": BYP,
        "Line g0": merge(PRE),
        "Line g+10": merge(PRE, dict(input_gain=10.0)),
        "Mic500 g0": merge(PRE, dict(input_select="(Mic) 500")),
        "Mic500 g+10": merge(PRE, dict(input_select="(Mic) 500", input_gain=10.0)),
        "Mic500 g+10 +pad": merge(PRE, dict(input_select="(Mic) 500", input_gain=10.0, input_pad="-15 dB")),
        "Mic2.0k g+10": merge(PRE, dict(input_select="(Mic) 2.0k", input_gain=10.0)),
        "Hi-Z47k g+10": merge(PRE, dict(input_select="(Hi-Z) 47k", input_gain=10.0)),
        "75Hz cut (Line g0)": merge(PRE, dict(cut_filter="75Hz")),
    }
    print(f"{'config':22} {'THD%':>7} {'H2dB':>7} {'H3dB':>7}   {'crest':>6} {'cent':>6} {'low%':>6} {'mid%':>6} {'high%':>6}")
    for name, cfg in configs.items():
        td, h2, h3 = thd(render(cfg, x))
        m = specmetrics(render(cfg, lx))
        print(f"{name:22} {td:7.3f} {h2:7.1f} {h3:7.1f}   {m['crest']:6.1f} {m['centroid']:6.0f} "
              f"{m['low']:6.1f} {m['mid']:6.1f} {m['high']:6.1f}")


# ---------- EQ ----------

def run_eq():
    print("\n=== EQ  (per-band dB delta vs EQ-bypassed, same Line g0 preamp; pink-ish noise probe)\n")
    rng = np.random.default_rng(7)
    # pinkish: filter white by 1/sqrt(f)
    w = rng.standard_normal(SR * 2).astype(np.float32)
    W = np.fft.rfft(w)
    fr = np.fft.rfftfreq(len(w), 1 / SR)
    W[1:] /= np.sqrt(fr[1:])
    probe = np.fft.irfft(W).astype(np.float32)
    probe *= 0.1 / (np.std(probe) + 1e-12)
    base = render(merge(PRE), probe)
    bands = [31, 63, 70, 100, 125, 200, 250, 500, 1000, 2000, 4000, 4500, 7000, 8000, 10000, 12500, 16000]

    def delta(cfg):
        y = render(merge(PRE, dict(eq_bypass="EQ In"), cfg), probe)
        n = min(len(y), len(base))
        Y = np.abs(np.fft.rfft(y[:n] * np.hanning(n)))
        B = np.abs(np.fft.rfft(base[:n] * np.hanning(n)))
        f = np.fft.rfftfreq(n, 1 / SR)
        out = []
        for bc in bands:
            k = (f >= bc / 1.06) & (f < bc * 1.06)
            out.append(20 * np.log10((np.sum(Y[k]) + 1e-9) / (np.sum(B[k]) + 1e-9)))
        return out

    tests = {
        "hi 10k +6": dict(eq_hi_freq=10000.0, eq_hi_gain=6.0),
        "hi 10k -6": dict(eq_hi_freq=10000.0, eq_hi_gain=-6.0),
        "hi 7k +6": dict(eq_hi_freq=7000.0, eq_hi_gain=6.0),
        "hi 4.5k +6": dict(eq_hi_freq=4500.0, eq_hi_gain=6.0),
        "lo 100 +6": dict(eq_lo_freq=100.0, eq_lo_gain=6.0),
        "lo 100 -6": dict(eq_lo_freq=100.0, eq_lo_gain=-6.0),
        "lo 70 +6": dict(eq_lo_freq=70.0, eq_lo_gain=6.0),
        "lo 200 +6": dict(eq_lo_freq=200.0, eq_lo_gain=6.0),
        "hi10k+9 lo70+6": dict(eq_hi_freq=10000.0, eq_hi_gain=9.0, eq_lo_freq=70.0, eq_lo_gain=6.0),
    }
    hdr = "config".ljust(16) + "".join(f"{b:>7}" for b in bands)
    print(hdr)
    for name, cfg in tests.items():
        d = delta(cfg)
        print(name.ljust(16) + "".join(f"{v:7.1f}" for v in d))


# ---------- DYN ----------

def run_dyn():
    print("\n=== DYN  (drum loop -> crest/centroid/bands;  tone GR vs preamp-ref)\n")
    lx = loop()
    x = tone(dbfs=-10.0)
    ref = specmetrics(render(merge(PRE), lx))
    # tone level through preamp-only (dyn byp) at the SAME output path, to compute GR
    pre_tone_rms = specmetrics(render(merge(PRE), x))["rms"]
    print(f"preamp-ref (dyn byp): crest {ref['crest']:.1f}  cent {ref['centroid']:.0f}  "
          f"low {ref['low']:.1f} mid {ref['mid']:.1f} high {ref['high']:.1f}\n")
    DI = dict(eq_bypass="EQ Byp", input_select="Line", input_gain=0.0, input_pad="Off",
              cut_filter="Off", level=6.0, dyn_bypass="Dyn In")

    def row(name, cfg):
        m = specmetrics(render(cfg, lx))
        # GR proxy: tone RMS drop vs preamp-ref at matched makeup (output/gain knob held at preamp level)
        tr = specmetrics(render(cfg, x))["rms"]
        gr = pre_tone_rms - tr
        print(f"{name:26} crest {m['crest']:6.1f}  cent {m['centroid']:6.0f}  "
              f"low {m['low']:5.1f} mid {m['mid']:5.1f} high {m['high']:5.1f}  toneΔ {gr:+5.1f}dB")

    print("-- 1176 mode (output held 6.0 = same as preamp level for the GR proxy) --")
    base76 = merge(DI, dict(dyn_mode="1176", **{"1176_output": 6.0, "1176_mix": 10.0,
                                                  "1176_atk": 5.0, "1176_rel": 5.0, "1176_sc_filt": False}))
    row("1176 in3 4:1", merge(base76, {"1176_input": 3.0, "1176_ratio": "4:1"}))
    row("1176 in6 8:1", merge(base76, {"1176_input": 6.0, "1176_ratio": "8:1"}))
    row("1176 in8 12:1", merge(base76, {"1176_input": 8.0, "1176_ratio": "12:1"}))
    row("1176 in6 20:1", merge(base76, {"1176_input": 6.0, "1176_ratio": "20:1"}))
    row("1176 in6 ALL", merge(base76, {"1176_input": 6.0, "1176_ratio": "ALL"}))
    row("1176 in8 ALL", merge(base76, {"1176_input": 8.0, "1176_ratio": "ALL"}))
    row("1176 in6 8:1 atk0(slow?)", merge(base76, {"1176_input": 6.0, "1176_ratio": "8:1", "1176_atk": 0.0}))
    row("1176 in6 8:1 atk10(fast?)", merge(base76, {"1176_input": 6.0, "1176_ratio": "8:1", "1176_atk": 10.0}))
    row("1176 in6 8:1 rel0", merge(base76, {"1176_input": 6.0, "1176_ratio": "8:1", "1176_rel": 0.0}))
    row("1176 in6 8:1 rel10", merge(base76, {"1176_input": 6.0, "1176_ratio": "8:1", "1176_rel": 10.0}))
    row("1176 in8 8:1 mix5(par)", merge(base76, {"1176_input": 8.0, "1176_ratio": "8:1", "1176_mix": 5.0}))
    row("1176 in8 8:1 scfilt", merge(base76, {"1176_input": 8.0, "1176_ratio": "8:1", "1176_sc_filt": True}))

    print("\n-- LA2A mode (gain held 6.0 for the GR proxy) --")
    base2a = merge(DI, dict(dyn_mode="LA2A", la2a_gain=6.0))
    row("LA2A Comp pk3", merge(base2a, {"la2a_ratio": "Comp", "la2a_pk_red": 3.0}))
    row("LA2A Comp pk6", merge(base2a, {"la2a_ratio": "Comp", "la2a_pk_red": 6.0}))
    row("LA2A Comp pk9", merge(base2a, {"la2a_ratio": "Comp", "la2a_pk_red": 9.0}))
    row("LA2A Limit pk6", merge(base2a, {"la2a_ratio": "Limit", "la2a_pk_red": 6.0}))
    row("LA2A Limit pk9", merge(base2a, {"la2a_ratio": "Limit", "la2a_pk_red": 9.0}))

    print("\n-- bare default load (NOT neutral — proves load != bypass) --")
    row("default load (no overrides)", {})


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("preamp", "all"):
        run_preamp()
    if mode in ("eq", "all"):
        run_eq()
    if mode in ("dyn", "all"):
        run_dyn()
