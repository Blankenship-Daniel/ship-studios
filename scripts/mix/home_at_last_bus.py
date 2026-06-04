"""Steely Dan "Home at Last" (Aja, 1977 / Bernard Purdie half-time shuffle) drum-bus tone chain.

    python home_at_last_bus.py <in_bus.wav> <out_bus.wav>
        [--pul-lf-boost 5] [--pul-lf-atten 4] [--pul-low-freq "60 CPS"]
        [--pul-hf-boost 4] [--pul-hf-q 8] [--pul-hf-freq "16 KCS"]
        [--pul-hf-atten 2] [--pul-hf-atten-freq "5 KCS"] [--no-pultec]
        [--mu-thresh 5] [--mu-input 6] [--mu-attack 3] [--mu-recovery Med]
        [--mu-comp-lim Comp] [--no-manley]
        [--ips "30 IPS"] [--repro-hf 5] [--tape-in 1.5] [--cal 6] [--no-tape]
        [--hpf 30] [--low-shelf 0.5] [--demud -1.0] [--deharsh -1.0] [--air 0.5]
        [--width 1.0] [--mono-below 0]

Applies, to an ALREADY balanced (clean, snare/kit-forward) drum bus (see presets/mix/home-at-last.json),
the Home-at-Last chain:
  A. apply_eq             — HPF 30 Hz zero-phase (gentle subsonic; KEEP the round low end)
  B. Pultec EQP-1A        — the Aja tonal signature: LOW-END TRICK (boost+atten @60 CPS = big-but-TIGHT
                            round bottom + low-mid scoop) + AIR-WITHOUT-FIZZ (16 KCS boost, 5 KCS atten =
                            silky extended top, harshness shaved). Passive tube/transformer colour, NOT drive.
  C. Manley Variable Mu   — CLEAN vari-mu tube glue that PRESERVES the ghost-note dynamics: Comp (1.5:1),
                            slow attack, Med recovery, HP-SC In -> levels macro-dynamics while crest HOLDS/RISES.
  D. Studer A800 30 IPS NAB — TIGHT, clean, warm tape glue (30 IPS = controlled low end + detailed top).
  E. apply_eq             — gentle zero-phase polish: subtle weight + de-box + smoothness guard + clean sheen.
  F. (opt) adjust_stereo  — width (default 1.0 = NATURAL, no-op); Aja drums are balanced, not mono, not hyper-wide.
then peak-normalize to -1 dBFS.

THE SOUND vs Bonham/fool-in-the-rain AND Beatles/tomorrow-never-knows (the THIRD axis): CLEAN/hi-fi (not
warm-dark, not lo-fi), DYNAMIC with the ghost-note dynamics PRESERVED (crest held/UP — NOT breathing glue,
NOT crush), TIGHT/ROUND low end (30 IPS, the INVERSE of Bonham's 15 IPS bloom), SILKY EXTENDED top (no
harshness, no roll-off-to-dark), NATURAL balanced width (not wide-room, not mono). It chases the studio
TONE, not Bernard Purdie's performed shuffle GROOVE.

DELIBERATE INVERSIONS (do NOT "fix" them):
  * 30 IPS, not 15 — the smaller head-bump TIGHTENS the lows = the controlled Aja bottom (15 IPS BLOOMS = Bonham).
  * Manley COMP (not LIMIT) + slow attack + HP-SC In — leveling that KEEPS transients; crest must not collapse.
    (If crest drops a lot you over-compressed — back the threshold UP. The Purdie shuffle IS its dynamics.)
  * width default 1.0 — keep the natural studio image; do NOT narrow (that's TNK) or hyper-widen (that's room).

The DEFAULTS reproduce the approved Home-at-Last signature; a bare invocation is unchanged. All enum/float
VST params are set via the tolerant set_param (nearest-valid snap), so e.g. --pul-low-freq snaps to the nearest
valid Pultec CPS. Run with the stemmy-loops `vst` venv.

Honest proxy: the exact Aja drum signal path (engineer Roger Nichols, prod. Gary Katz, 1977 LA studios) is not
fully documented; this is an era-appropriate chase of the clean/warm/DYNAMIC tone (Pultec passive EQ + vari-mu
tube glue + Studer multitrack tape), NOT a claim of the literal gear. See presets/mix/home-at-last.json.
"""
import argparse, os, sys

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter w/ nearest-valid snap)

PULTEC = "/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3"
MANLEY = "/Library/Audio/Plug-Ins/VST3/uaudio_manley_variable_mu.vst3"
STUDER = "/Library/Audio/Plug-Ins/VST3/uaudio_studer_a800.vst3"
OUT_PEAK_DBFS = -1.0


def _m(tag, f):
    from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
    from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
    from stemmy.loops_mcp.tools.measure_stereo import measure_stereo
    L = measure_loudness(f).model_dump(); S = measure_spectrum(f).model_dump(); T = measure_stereo(f).model_dump()
    print(f"  {tag:<10} centroid {S['spectral_centroid_hz']:5.0f} | tilt {S['spectral_tilt_db_per_octave']:+.2f} "
          f"| crest {L['crest_factor_db']:5.1f} | LUFS {L['integrated_lufs']:6.1f} | corr {T['correlation']:.3f}")


def _set_all(p, params):
    for k, v in params.items():
        note = set_param(p, k, v)
        if note:
            print(f"warn: {note}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Steely Dan 'Home at Last' clean/dynamic drum-bus chain "
                                             "(Pultec EQP-1A -> Manley Variable Mu -> Studer 30 IPS -> EQ).")
    ap.add_argument("src"); ap.add_argument("out")
    # Pultec EQP-1A (the Aja tone: tight round low + silky air) -----------------------------------
    ap.add_argument("--pul-low-freq", default="60 CPS", help="Pultec low CPS (low-end trick corner: 20/30/60/100 CPS)")
    ap.add_argument("--pul-lf-boost", type=float, default=5.0, help="Pultec low Boost dial 0..10 (NONLINEAR, ~+11 dB @60 knob6); round weight")
    ap.add_argument("--pul-lf-atten", type=float, default=4.0, help="Pultec low Atten dial 0..10; the low-end-TRICK scoop (tightens = no mud)")
    ap.add_argument("--pul-hf-freq", default="16 KCS", help="Pultec HF Boost KCS (3/4/5/8/10/12/16); 16 = pure air")
    ap.add_argument("--pul-hf-boost", type=float, default=4.0, help="Pultec HF Boost dial 0..10; silky extended top")
    ap.add_argument("--pul-hf-q", type=float, default=8.0, help="Pultec HF bandwidth 0..10 (0=SHARP, 10=BROAD); 8 = broad/musical air")
    ap.add_argument("--pul-hf-atten-freq", default="5 KCS", help="Pultec HF Atten SEL (5/10/20 KCS); 5 = de-harsh the 3-8k fizz")
    ap.add_argument("--pul-hf-atten", type=float, default=2.0, help="Pultec HF Atten dial 0..10; shave harshness ('air without fizz')")
    ap.add_argument("--no-pultec", action="store_true", help="skip the Pultec tonal stage")
    # Manley Variable Mu (clean glue that PRESERVES dynamics) -------------------------------------
    ap.add_argument("--mu-thresh", type=float, default=5.0, help="Manley threshold 0..10 (LOWER = MORE GR; default 5 = gentle ~2-3 dB)")
    ap.add_argument("--mu-input", type=float, default=6.0, help="Manley DUAL INPUT drive 0..10 (hits the tubes for even-harmonic warmth)")
    ap.add_argument("--mu-attack", type=float, default=3.0, help="Manley attack 0..10 (0=SLOW=keep transients/ghost-notes; KEEP low for dynamics)")
    ap.add_argument("--mu-recovery", default="Med", help="Manley recovery (Slo/Med Slo/Med/Med Fast/Fast); Med = most open/transparent")
    ap.add_argument("--mu-comp-lim", default="Comp", help="Manley Comp (1.5:1 glue) vs Limit (4:1 crush); Comp preserves the shuffle dynamics")
    ap.add_argument("--no-manley", action="store_true", help="skip the Manley glue stage")
    # Studer A800 (tight clean warm tape) --------------------------------------------------------
    ap.add_argument("--ips", default="30 IPS", help="Studer tape speed ('30 IPS' TIGHTENS lows = Aja; '15 IPS' blooms = Bonham)")
    ap.add_argument("--repro-hf", type=float, default=5.0, help="Studer repro_hf_eq 0..10 (HIGHER = brighter/more detailed top; Aja keeps detail)")
    ap.add_argument("--tape-in", type=float, default=1.5, help="Studer input_level dB (GENTLE drive — warmth/glue without grit; Aja is clean)")
    ap.add_argument("--cal", type=float, default=6.0, help="Studer cal_level {3,6,7.5,9}")
    ap.add_argument("--no-tape", action="store_true", help="skip the Studer tape stage")
    # tonal polish (zero-phase, after the VSTs) --------------------------------------------------
    ap.add_argument("--hpf", type=float, default=30.0, help="pre-chain HPF Hz (gentle subsonic; keep the round bottom)")
    ap.add_argument("--low-shelf", type=float, default=0.5, help="post low_shelf @100 gain dB (subtle weight; Pultec does the bulk)")
    ap.add_argument("--demud", type=float, default=-1.0, help="post bell @400 gain dB (gentle de-box; keep it clean)")
    ap.add_argument("--deharsh", type=float, default=-1.0, help="post bell @3k gain dB (smoothness guard; Aja is never harsh)")
    ap.add_argument("--air", type=float, default=0.5, help="post high_shelf @12k gain dB (clean sheen/detail, NOT bright)")
    # natural width (default 1.0 = no-op) --------------------------------------------------------
    ap.add_argument("--width", type=float, default=1.0, help="M/S width 0..1+ (1.0=NATURAL/no-op; Aja is balanced, not mono, not hyper-wide)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF (keep rumble out of the tape; gentle so the round low end survives)
    e1 = src + ".hal1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-D — Pultec -> Manley -> Studer, one chained render (shape -> glue -> tape)
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)   # ensure stereo for the Manley / bus image
    chain = []
    if not a.no_pultec:
        p = load_plugin(PULTEC)
        _set_all(p, {"power": True, "master_bypass": False, "enable": "In", "output": "0.0 dB",
                     "low_freq": a.pul_low_freq, "lf_boost": a.pul_lf_boost, "lf_atten": a.pul_lf_atten,
                     "high_freq": a.pul_hf_freq, "hf_boost": a.pul_hf_boost, "hf_q": a.pul_hf_q,
                     "hf_atten_freq": a.pul_hf_atten_freq, "hf_atten": a.pul_hf_atten})
        chain.append(p)
    if not a.no_manley:
        mu = load_plugin(MANLEY)
        _set_all(mu, {"power": True, "master_bypass": False, "dual_input": a.mu_input,
                      "l_thresh": a.mu_thresh, "r_thresh": a.mu_thresh,
                      "l_attack": a.mu_attack, "r_attack": a.mu_attack,
                      "l_recovery": a.mu_recovery, "r_recovery": a.mu_recovery,
                      "l_output": 5.0, "r_output": 5.0,
                      "l_comp_lim": a.mu_comp_lim, "r_comp_lim": a.mu_comp_lim,
                      "l_hp_sc_filt": "In", "r_hp_sc_filt": "In",
                      "l_bypass": "In", "r_bypass": "In",
                      "in_matrix": "L-R", "out_matrix": "L-R", "sc_link": "Link", "ctrl_link": "Link",
                      "mix": 100.0, "headroom": 16.0})
        chain.append(mu)
    if not a.no_tape:
        t = load_plugin(STUDER)
        _set_all(t, {"power": True, "path_select": "Repro", "ips": a.ips, "tape_type": "456",
                     "emphasis_eq": "NAB", "cal_level": a.cal, "auto_cal": True, "noise": False,
                     "input_level": a.tape_in, "repro_hf_eq": a.repro_hf, "output_level": 0.0})
        chain.append(t)
    y = Pedalboard(chain)(x, sr) if chain else x
    e2 = src + ".hal2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage E — tonal polish (zero-phase)
    e3 = src + ".hal3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=100, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=400, gain_db=a.demud, q=1.0),
        EqBand(type="bell", freq_hz=3000, gain_db=a.deharsh, q=1.2),
        EqBand(type="high_shelf", freq_hz=12000, gain_db=a.air, q=0.7)], phase="zero")

    # Stage F — natural width (default 1.0 = no-op; only render adjust_stereo if it actually changes the image)
    cur = e3
    e4 = None
    if abs(a.width - 1.0) > 1e-6 or a.mono_below > 0:
        e4 = src + ".hal4.wav"
        adjust_stereo(e3, e4, width=a.width, mono_below_hz=a.mono_below)
        cur = e4

    z, sr = sf.read(cur, dtype="float32", always_2d=True)
    zz = peak_normalize(z.T, OUT_PEAK_DBFS)   # shared core; same -1 dBFS invariant
    sf.write(out, zz.T, sr, subtype="PCM_24")
    for f in (e1, e2, e3, e4):
        if not f:
            continue
        try:
            os.remove(f)
        except OSError:
            pass
    _m("FINAL", out)
    print(f"home-at-last bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
