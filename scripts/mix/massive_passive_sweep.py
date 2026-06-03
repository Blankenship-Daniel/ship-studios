"""Measure the UADx Manley Massive Passive's REAL curves headless via Pedalboard.

Companion measurement rig for docs/vst/manley-massive-passive.md + the [[manley-massive-passive]] skill.
Renders white noise through the plugin to extract LTI transfer functions (Welch cross-spectral H
estimate) for every control, and a 1 kHz sine to read the passive-EQ + tube/MOSFET make-up-amp colour.

The Massive Passive is a 4-band PASSIVE EQ. Every band defaults to enable='OUT' (out of circuit) —
you MUST switch a band to 'BOOST' or 'CUT' for its gain knob to do anything (this is why probe_plugin
false-flags it as passthrough). All 51 params are enums; the gain/bw/freq are numeric enums, the
enable/shape/lopass/hipass/link/power are STRING/bool enums.

Run with the stemmy-loops vst venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/massive_passive_sweep.py        # standard
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/massive_passive_sweep.py mst    # MST (mastering)
"""
import sys
import numpy as np
from pedalboard import load_plugin

ARGS = [a.lower() for a in sys.argv[1:]]
MST = "mst" in ARGS
SR = next((int(a) for a in ARGS if a.isdigit()), 48000)   # `… mst 96000` to run at 96k
PLUG = ("/Library/Audio/Plug-Ins/VST3/uaudio_manley_massive_passive_m.vst3" if MST
        else "/Library/Audio/Plug-Ins/VST3/uaudio_manley_massive_passive.vst3")
N = SR * 4

# probe grid, all < Nyquist at 48k; the HI band's 27 kHz corner only resolves at 96k (added when SR>48k)
FREQS = [20, 30, 47, 68, 100, 150, 220, 330, 470, 680, 1000,
         1500, 2200, 3300, 4700, 6800, 10000, 14000, 18000, 23000]
if SR > 48000:
    FREQS = FREQS + [27000, 32000]

BANDS = ("lo", "lomid", "himid", "hi")
GAIN_HI = 11.0 if MST else 20.0          # max gain dial position
DEF_BW = 1.0 if MST else 2.0
GAIN_STEPS = [1, 3, 5, 8, 11] if MST else [2, 5, 10, 15, 20]
DEF_FREQ = {"lo": 150.0, "lomid": 560.0, "himid": 1500.0, "hi": 3900.0}


def base():
    """Full flat state, both channels, EQ engaged, all bands OUT, filters off, UNLINKED."""
    d = dict(power=True, master_bypass=False, ctrllink="UNLINKED")
    for ch in (1, 2):
        d[f"ch{ch}enable"] = "IN"
        d[f"ch{ch}gain"] = 0.0
        d[f"ch{ch}lopass"] = "OFF"
        d[f"ch{ch}hipass"] = "OFF"
        for b in BANDS:
            d[f"ch{ch}{b}enable"] = "OUT"
            d[f"ch{ch}{b}shape"] = "SHELF" if b in ("lo", "hi") else "BELL"
            d[f"ch{ch}{b}gain"] = 0.0
            d[f"ch{ch}{b}bw"] = DEF_BW
            d[f"ch{ch}{b}freq"] = DEF_FREQ[b]
    return d


def band(b, *, enable="BOOST", shape=None, gain=10.0, bw=None, freq=None):
    """Compact per-band override applied to BOTH channels."""
    out = {}
    for ch in (1, 2):
        out[f"ch{ch}{b}enable"] = enable
        if shape is not None:
            out[f"ch{ch}{b}shape"] = shape
        out[f"ch{ch}{b}gain"] = gain
        if bw is not None:
            out[f"ch{ch}{b}bw"] = bw
        if freq is not None:
            out[f"ch{ch}{b}freq"] = freq
    return out


def snap(par, v):
    """Snap a numeric target to the nearest valid enum value (gain/bw/freq are discrete)."""
    vv = list(getattr(par, "valid_values", []) or [])
    if not vv or not isinstance(v, (int, float)):
        return v
    def num(s):
        try:
            return float(str(s))
        except Exception:
            return None
    cand = [(abs(num(s) - v), s) for s in vv if num(s) is not None]
    return min(cand, key=lambda t: t[0])[1] if cand else v


def setp(p, *overrides, **kw):
    d = base()
    for o in overrides:
        d.update(o)
    d.update(kw)
    for k, v in d.items():
        setattr(p, k, snap(p.parameters[k], v) if isinstance(v, (int, float)) else v)


def white():
    rng = np.random.default_rng(7)
    x = rng.standard_normal((2, N)).astype(np.float32)
    x *= (10 ** (-18 / 20)) / np.sqrt(np.mean(x ** 2))
    return x


def transfer(p, x, ch=0):
    y = np.asarray(p(x, SR))
    L = 16384
    win = np.hanning(L)
    f = np.fft.rfftfreq(L, 1 / SR)
    Sxy = np.zeros(L // 2 + 1, complex)
    Sxx = np.zeros(L // 2 + 1)
    hop = L // 2
    xi, yi = x[ch], y[ch]
    for s in range(0, len(xi) - L, hop):
        X = np.fft.rfft(xi[s:s + L] * win)
        Y = np.fft.rfft(yi[s:s + L] * win)
        Sxy += Y * np.conj(X)
        Sxx += np.abs(X) ** 2
    H = Sxy / (Sxx + 1e-20)
    mag = 20 * np.log10(np.abs(H) + 1e-12)
    return [float(mag[np.argmin(np.abs(f - fc))]) for fc in FREQS], y


def thd(level_db=-12.0, *overrides, **kw):
    p2 = load_plugin(PLUG)
    setp(p2, *overrides, **kw)
    t = np.arange(N) / SR
    s = (np.sin(2 * np.pi * 1000 * t)).astype(np.float32) * (10 ** (level_db / 20))
    y = np.asarray(p2(np.stack([s, s]), SR))[0]
    L = 1 << 16
    c = len(y) // 2
    seg = y[c - L // 2:c + L // 2] * np.hanning(L)
    Y = np.abs(np.fft.rfft(seg))
    f = np.fft.rfftfreq(L, 1 / SR)

    def bm(fc):
        i = np.argmin(np.abs(f - fc))
        return float(np.sqrt(np.sum(Y[i - 2:i + 3] ** 2)))
    fund = bm(1000)
    harm = np.sqrt(sum(bm(1000 * k) ** 2 for k in range(2, 9)))
    h2, h3 = bm(2000), bm(3000)
    return (100 * harm / (fund + 1e-20),
            20 * np.log10(h2 / fund + 1e-20),
            20 * np.log10(h3 / fund + 1e-20))


def row(label, vals):
    print(f"{label:26}" + "".join(f"{v:+6.1f}" for v in vals))


def header():
    print(f"{'dB @ Hz':26}" + "".join(f"{fc:>6}" for fc in FREQS))


def peak_db(vals):
    return max(vals)


def main():
    print(f"=== {'MST (Mastering)' if MST else 'Standard'} build: {PLUG}")
    x = white()
    p = load_plugin(PLUG)
    print(f"loaded: {getattr(p,'name','?')}  (gain dial max = {GAIN_HI}, default bw = {DEF_BW})\n")

    # ---- 0. RENDER PROOF + LINK behavior ----
    print("== RENDER PROOF: LO band BOOST shelf gain=max @68 Hz (should NOT be flat) ==")
    header()
    setp(p, band("lo", enable="BOOST", shape="SHELF", gain=GAIN_HI, freq=68.0))
    m, y = transfer(p, x)
    row("lo BOOST max", m)
    print(f"   ch0 vs ch1 max-abs diff = {float(np.max(np.abs(y[0]-y[1]))):.2e} (UNLINKED, both set => same)\n")

    print("== LINK TEST: ctrllink=LINKED, set ONLY ch1 lo BOOST — does ch2 follow? ==")
    p2 = load_plugin(PLUG)
    d = base(); d["ctrllink"] = "LINKED"
    d["ch1loenable"] = "BOOST"; d["ch1loshape"] = "SHELF"; d["ch1logain"] = GAIN_HI; d["ch1lofreq"] = 68.0
    for k, v in d.items():
        setattr(p2, k, snap(p2.parameters[k], v) if isinstance(v, (int, float)) else v)
    m0, _ = transfer(p2, x, ch=0)
    m1, _ = transfer(p2, x, ch=1)
    print(f"   ch0 peak {peak_db(m0):+.1f} dB @low, ch1 peak {peak_db(m1):+.1f} dB  -> ", end="")
    print("LINK mirrors ch1->ch2" if peak_db(m1) > 1.0 else "LINK does NOT mirror via API (must set BOTH channels)")
    print()

    # ---- 1. FLAT / BYPASS NULL ----
    print("== FLAT null: EQ engaged (IN) all bands OUT  vs  ch enable=OUT  vs  master_bypass ==")
    header()
    setp(p)
    m, _ = transfer(p, x); row("engaged flat (IN)", m)
    setp(p, ch1enable="OUT", ch2enable="OUT")
    m, _ = transfer(p, x); row("ch enable=OUT", m)
    setp(p, master_bypass=True)
    m, _ = transfer(p, x); row("master_bypass", m)
    print()

    # ---- 2. PER-BAND GAIN CALIBRATION (BELL, center freq) ----
    centers = {"lo": 68.0, "lomid": 560.0, "himid": 1500.0, "hi": 5600.0}
    for b in BANDS:
        print(f"== {b.upper()} band BOOST as BELL @ {centers[b]:g} Hz — gain dial -> actual peak dB ==")
        for g in GAIN_STEPS:
            setp(p, band(b, enable="BOOST", shape="BELL", gain=float(g), bw=DEF_BW, freq=centers[b]))
            m, _ = transfer(p, x)
            print(f"  gain {g:>4}   peak {peak_db(m):+6.2f} dB  | " + "".join(f"{v:+6.1f}" for v in m))
        print()

    # ---- 3. SHELF vs BELL + resonant overshoot (LO and HI bands) ----
    for b, f0 in [("lo", 68.0), ("hi", 12000.0)]:
        print(f"== {b.upper()} band BOOST gain=10 @ {f0:g} Hz: SHELF vs BELL (look for shelf overshoot bump) ==")
        header()
        setp(p, band(b, enable="BOOST", shape="SHELF", gain=10.0, freq=f0))
        m, _ = transfer(p, x); row("  SHELF", m)
        setp(p, band(b, enable="BOOST", shape="BELL", gain=10.0, freq=f0))
        m, _ = transfer(p, x); row("  BELL", m)
        print()

    # ---- 4. BANDWIDTH effect on a BELL and on a SHELF (the resonance trick) ----
    print("== BANDWIDTH on a BELL: himid BOOST gain=10 @1.5k, bw 1.0 / 2.0 / 3.0 ==")
    header()
    for bw in [1.0, 2.0, 3.0]:
        setp(p, band("himid", enable="BOOST", shape="BELL", gain=10.0, bw=bw, freq=1500.0))
        m, _ = transfer(p, x); row(f"  bw {bw}", m)
    print()
    print("== BANDWIDTH on a HI SHELF: hi BOOST gain=10 @12k, bw 1.0 / 2.0 / 3.0 (overshoot bump?) ==")
    header()
    for bw in [1.0, 2.0, 3.0]:
        setp(p, band("hi", enable="BOOST", shape="SHELF", gain=10.0, bw=bw, freq=12000.0))
        m, _ = transfer(p, x); row(f"  bw {bw}", m)
    print()
    print("== BANDWIDTH on a LOW SHELF: lo BOOST gain=10 @68, bw 1.0 / 2.0 / 3.0 ==")
    header()
    for bw in [1.0, 2.0, 3.0]:
        setp(p, band("lo", enable="BOOST", shape="SHELF", gain=10.0, bw=bw, freq=68.0))
        m, _ = transfer(p, x); row(f"  bw {bw}", m)
    print()

    # ---- 5. The BOOST + adjacent CUT trick (Pultec-style) ----
    print("== LOW TRICK: lo SHELF BOOST @47 + lomid BELL CUT @180 (big tight bottom) ==")
    header()
    setp(p, band("lo", enable="BOOST", shape="SHELF", gain=12.0, freq=47.0))
    m, _ = transfer(p, x); row("  boost only", m)
    setp(p,
         band("lo", enable="BOOST", shape="SHELF", gain=12.0, freq=47.0),
         band("lomid", enable="CUT", shape="BELL", gain=8.0, bw=DEF_BW, freq=180.0))
    m, _ = transfer(p, x); row("  +lomid cut", m)
    print()
    print("== AIR TRICK: hi SHELF BOOST @16k + himid BELL CUT @3.3k (air, de-harsh) ==")
    header()
    setp(p, band("hi", enable="BOOST", shape="SHELF", gain=10.0, freq=16000.0))
    m, _ = transfer(p, x); row("  air only", m)
    setp(p,
         band("hi", enable="BOOST", shape="SHELF", gain=10.0, freq=16000.0),
         band("himid", enable="CUT", shape="BELL", gain=8.0, bw=DEF_BW, freq=3300.0))
    m, _ = transfer(p, x); row("  +himid cut", m)
    print()
    print("== SUPERSONIC AIR: hi SHELF BOOST gain=max @27000 (audible-range lift from a >Nyquist-ish corner) ==")
    header()
    setp(p, band("hi", enable="BOOST", shape="SHELF", gain=GAIN_HI, bw=3.0, freq=27000.0))
    m, _ = transfer(p, x); row("  hi shelf @27k", m)
    print()

    # ---- 6. CUT calibration + symmetry ----
    print("== CUT depth: lomid BELL CUT @560, gain dial -> actual dip dB (vs BOOST symmetry) ==")
    mid = [i for i, fc in enumerate(FREQS) if 120 <= fc <= 6000]   # exclude the engaged-flat top presence/rolloff
    for g in GAIN_STEPS:
        setp(p, band("lomid", enable="CUT", shape="BELL", gain=float(g), freq=560.0))
        m, _ = transfer(p, x)
        setp(p, band("lomid", enable="BOOST", shape="BELL", gain=float(g), freq=560.0))
        mb, _ = transfer(p, x)
        print(f"  dial {g:>4}   CUT dip {min(m[i] for i in mid):+6.2f}   BOOST peak {max(mb[i] for i in mid):+6.2f}")
    print()

    # ---- 7. HP / LP filters ----
    print("== HIGH-PASS filter corners (ch?hipass) ==")
    header()
    hp_vals = (['12 Hz', '16 Hz', '23 Hz', '30 Hz', '39 Hz'] if MST
               else ['22 Hz', '39 Hz', '68 Hz', '120 Hz', '220 Hz'])
    for v in hp_vals:
        setp(p, ch1hipass=v, ch2hipass=v)
        m, _ = transfer(p, x); row(f"  HP {v}", m)
    print()
    print("== LOW-PASS filter corners (ch?lopass) ==")
    header()
    lp_vals = (['52 kHz', '40 kHz', '27 kHz', '20 kHz', '15 kHz'] if MST
               else ['18 kHz', '12 kHz', '9 kHz', '7.5 kHz', '6 kHz'])
    for v in lp_vals:
        setp(p, ch1lopass=v, ch2lopass=v)
        m, _ = transfer(p, x); row(f"  LP {v}", m)
    print()

    # ---- 8. Master gain trim ----
    print("== MASTER GAIN trim (ch?gain) linearity ==")
    header()
    gains = [-2.5, 0.0, 2.5] if MST else [-6.0, -3.0, 0.0, 4.0]
    for g in gains:
        setp(p, ch1gain=g, ch2gain=g)
        m, _ = transfer(p, x); row(f"  trim {g:+g} dB", m)
    print()

    # ---- 8b. PARALLEL-BAND NON-ADDITIVITY (passive bands interact) ----
    print("== PARALLEL-BAND NON-ADDITIVITY: lo BELL g10@150  +  himid BELL g10@1500 ==")
    setp(p, band("lo", enable="BOOST", shape="BELL", gain=10.0, freq=150.0))
    loA, _ = transfer(p, x)
    setp(p, band("himid", enable="BOOST", shape="BELL", gain=10.0, freq=1500.0))
    hiA, _ = transfer(p, x)
    setp(p,
         band("lo", enable="BOOST", shape="BELL", gain=10.0, freq=150.0),
         band("himid", enable="BOOST", shape="BELL", gain=10.0, freq=1500.0))
    both, _ = transfer(p, x)
    idx = {fc: i for i, fc in enumerate(FREQS)}
    for fc in [150, 470, 680, 1000, 1500]:
        i = idx[fc]
        s = loA[i] + hiA[i]
        print(f"  @{fc:>4}: lo {loA[i]:+5.2f} + himid {hiA[i]:+5.2f} = sum {s:+5.2f} | BOTH {both[i]:+5.2f} "
              f"(interaction {both[i]-s:+5.2f})")
    print()

    # ---- 9. THD / make-up-amp colour ----
    print("== THD @ 1 kHz (tube/MOSFET make-up colour).  thd%, H2 dB, H3 dB ==")
    for label, ov, kw in [
        ("bypass", (), dict(master_bypass=True)),
        ("engaged flat", (), {}),
        ("lo BOOST10@100 BELL", (band("lo", enable="BOOST", shape="BELL", gain=10.0, freq=100.0),), {}),
        ("himid BOOST max@1k BELL", (band("himid", enable="BOOST", shape="BELL", gain=GAIN_HI, freq=1000.0),), {}),
        ("master trim +max", (), dict(ch1gain=(2.5 if MST else 4.0), ch2gain=(2.5 if MST else 4.0))),
    ]:
        for lvl in [-18.0, -6.0, 0.0]:
            t, h2, h3 = thd(lvl, *ov, **kw)
            print(f"  {label:24} in {lvl:+5.0f} dBFS:  THD {t:6.3f}%   H2 {h2:6.1f}   H3 {h3:6.1f}")
    print()


if __name__ == "__main__":
    main()
