"""Measure the UADx Pultec EQP-1A's REAL curves headless via Pedalboard.

The companion measurement rig for docs/vst/pultec-eqp-1a.md + the [[pultec-eqp-1a]] skill.
Renders white noise through the plugin to extract LTI transfer functions for every control
(Welch cross-spectral H estimate), and a 1 kHz sine to read the passive-EQ + tube/output
harmonic colour. Prints dB-at-frequency tables for:

  * flat/bypass null (does the engaged-but-flat unit colour or add gain?)
  * LF BOOST per CPS (20/30/60/100), knob 2..10
  * LF ATTEN per CPS, knob 2..10
  * the famous low-end TRICK (boost + atten at the same CPS)
  * HF BOOST per KCS (3..16), knob 2..10, and BANDWIDTH (hf_q SHARP=0 vs BROAD=10)
  * HF ATTEN per ATTEN-SEL freq (5/10/20), knob 2..10
  * THD vs knob/output drive (the tube colour)

Run with the stemmy-loops vst venv:
    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/pultec_sweep.py
"""
import numpy as np
from pedalboard import load_plugin

PLUG = "/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3"
SR = 48000
N = SR * 4  # 4 s

FREQS = [30, 50, 60, 80, 100, 150, 200, 300, 500, 1000,
         2000, 3000, 5000, 8000, 10000, 12000, 16000, 20000]

FLAT = dict(power=True, master_bypass=False, enable="In",
            low_freq="30 CPS", lf_boost=0.0, lf_atten=0.0,
            high_freq="8 KCS", hf_boost=0.0, hf_q=0.0,
            hf_atten_freq="10 KCS", hf_atten=0.0, output="0.0 dB")


def setp(p, **kw):
    base = dict(FLAT)
    base.update(kw)
    for k, v in base.items():
        setattr(p, k, v)


def white():
    rng = np.random.default_rng(7)
    x = rng.standard_normal((2, N)).astype(np.float32)
    x *= (10 ** (-18 / 20)) / np.sqrt(np.mean(x ** 2))  # -18 dBFS RMS — stay ~linear
    return x


def transfer(p, x):
    """Welch cross-spectral magnitude transfer (delay-invariant), dB at FREQS."""
    y = np.asarray(p(x, SR))
    L = 16384
    win = np.hanning(L)
    f = np.fft.rfftfreq(L, 1 / SR)
    Sxy = np.zeros(L // 2 + 1, complex)
    Sxx = np.zeros(L // 2 + 1)
    hop = L // 2
    for ch in (0, 1):
        xi, yi = x[ch], y[ch]
        for s in range(0, len(xi) - L, hop):
            X = np.fft.rfft(xi[s:s + L] * win)
            Y = np.fft.rfft(yi[s:s + L] * win)
            Sxy += Y * np.conj(X)
            Sxx += np.abs(X) ** 2
    H = Sxy / (Sxx + 1e-20)
    mag = 20 * np.log10(np.abs(H) + 1e-12)
    return [float(mag[np.argmin(np.abs(f - fc))]) for fc in FREQS]


def thd(p, level_db=-12.0, **kw):
    p2 = load_plugin(PLUG)
    setp(p2, **kw)
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
    print(f"{label:24}" + "".join(f"{v:+7.1f}" for v in vals))


def header():
    print(f"{'dB @ Hz':24}" + "".join(f"{fc:>7}" for fc in FREQS))


def main():
    x = white()
    p = load_plugin(PLUG)
    print(f"loaded: {getattr(p,'name','?')}\n")

    # ---- flat / bypass null ----
    print("== FLAT (enable=In, all knobs 0) transfer — insertion gain + any passive colour ==")
    header()
    setp(p)
    row("flat In", transfer(p, x))
    setp(p, enable="Out")
    row("enable Out (bypass)", transfer(p, x))
    setp(p, master_bypass=True)
    row("master_bypass", transfer(p, x))
    print()

    # ---- LF BOOST per CPS ----
    for cps in ["20 CPS", "30 CPS", "60 CPS", "100 CPS"]:
        print(f"== LF BOOST @ {cps} (lf_boost knob) ==")
        header()
        for k in [2, 4, 6, 8, 10]:
            setp(p, low_freq=cps, lf_boost=float(k))
            row(f"  boost {k}", transfer(p, x))
        print()

    # ---- LF ATTEN per CPS ----
    for cps in ["20 CPS", "30 CPS", "60 CPS", "100 CPS"]:
        print(f"== LF ATTEN @ {cps} (lf_atten knob) ==")
        header()
        for k in [2, 4, 6, 8, 10]:
            setp(p, low_freq=cps, lf_atten=float(k))
            row(f"  atten {k}", transfer(p, x))
        print()

    # ---- the TRICK: boost + atten same CPS ----
    for cps in ["60 CPS", "100 CPS"]:
        print(f"== LOW-END TRICK @ {cps} (boost + atten together) ==")
        header()
        for b, a in [(4, 3), (5, 5), (7, 5), (8, 8), (10, 10)]:
            setp(p, low_freq=cps, lf_boost=float(b), lf_atten=float(a))
            row(f"  B{b}/A{a}", transfer(p, x))
        print()

    # ---- HF BOOST per KCS (bandwidth = mid, q=5) ----
    for kcs in ["3 KCS", "5 KCS", "8 KCS", "10 KCS", "12 KCS", "16 KCS"]:
        print(f"== HF BOOST @ {kcs} (hf_boost knob, hf_q=5 mid bandwidth) ==")
        header()
        for k in [2, 4, 6, 8, 10]:
            setp(p, high_freq=kcs, hf_boost=float(k), hf_q=5.0)
            row(f"  boost {k}", transfer(p, x))
        print()

    # ---- BANDWIDTH (hf_q) at fixed boost ----
    print("== HF BANDWIDTH (hf_q) @ 10 KCS, hf_boost=8 — SHARP(0) -> BROAD(10) ==")
    header()
    for q in [0, 2, 5, 8, 10]:
        setp(p, high_freq="10 KCS", hf_boost=8.0, hf_q=float(q))
        row(f"  q {q}", transfer(p, x))
    print()

    # ---- HF ATTEN per ATTEN-SEL ----
    for af in ["5 KCS", "10 KCS", "20 KCS"]:
        print(f"== HF ATTEN @ {af} (hf_atten knob) ==")
        header()
        for k in [2, 4, 6, 8, 10]:
            setp(p, hf_atten_freq=af, hf_atten=float(k))
            row(f"  atten {k}", transfer(p, x))
        print()

    # ---- "air without fizz": boost 16k + atten 10k ----
    print("== AIR-WITHOUT-FIZZ: hf_boost @ 16 KCS + hf_atten @ 10 KCS ==")
    header()
    setp(p, high_freq="16 KCS", hf_boost=6.0, hf_q=8.0)
    row("  boost16k(6) only", transfer(p, x))
    setp(p, high_freq="16 KCS", hf_boost=6.0, hf_q=8.0, hf_atten_freq="10 KCS", hf_atten=4.0)
    row("  +atten10k(4)", transfer(p, x))
    print()

    # ---- THD / tube colour ----
    print("== THD @ 1 kHz (tube/output colour). thd% , H2 dB , H3 dB ==")
    for label, kw in [
        ("flat In, out 0", dict()),
        ("flat, out +6", dict(output="6.0 dB")),
        ("flat, out +12", dict(output="12.0 dB")),
        ("LF boost10 @100", dict(low_freq="100 CPS", lf_boost=10.0)),
        ("HF boost10 @10k", dict(high_freq="10 KCS", hf_boost=10.0, hf_q=5.0)),
    ]:
        for lvl in [-18.0, -6.0]:
            t, h2, h3 = thd(p, level_db=lvl, **kw)
            print(f"  {label:22} in {lvl:+5.0f} dBFS:  THD {t:6.3f}%   H2 {h2:6.1f}   H3 {h3:6.1f}")
    print()


if __name__ == "__main__":
    main()
