"""AC/DC "Back in Black" (Mutt Lange / Tony Platt, 1980) TIGHT/PUNCHY/DRY drum-bus tone chain.

    python back_in_black_bus.py <in_bus.wav> <out_bus.wav>
        [--ts-punch 2] [--ts-punch-band WIDE] [--ts-punch-type SLOW]
        [--ts-sustain -2] [--ts-sustain-band LOW] [--ts-xover 700] [--no-ts]
        [--ssl-colour Black] [--ssl-lf 3] [--ssl-debox -2] [--ssl-pres 1.5] [--ssl-air 1.5]
        [--ssl-ratio 4.0] [--ssl-thresh -16] [--ssl-release 0.15] [--ssl-fast Out] [--no-ssl]
        [--dbx-ratio " 4.0:1"] [--dbx-thresh -26] [--dbx-gain 3] [--no-dbx]
        [--hpf 35] [--low-shelf 0.5] [--debox-post -0.5] [--snap 0.5] [--present 1.0]
        [--width 1.0] [--mono-below 0]

Applies, to an ALREADY balanced drum bus (see presets/mix/back-in-black.json), the Back-in-Black chain:
  A. apply_eq                 — HPF zero-phase (tight subsonic)
  B. Softube Transient Shaper — ADD attack (punch) + tighten the low boom (sustain- on the LOW band)
  C. SSL 4K E channel strip   — clean weighty 'British console' tone (Black EQ: LF weight, de-box, presence)
                                + the grabby VCA comp with FAST attack OUT = transients PASS = punch (crest UP)
  D. dbx 160                  — light VCA punch/glue (4:1 RAISES crest on drums) for cohesion
  E. apply_eq                 — PRESENT zero-phase polish (de-box guard + snap + present top; NOT dark)
  F. (opt) adjust_stereo      — natural width (default 1.0 = no-op)
then peak-normalize to -1 dBFS.

THE SOUND (a NEW axis): TIGHT / PUNCHY / DRY / PRESENT arena rock. Not warm-room (fool-in-the-rain), not
mono-crush (tomorrow-never-knows), not the gated explosion (in-the-air-tonight): low-tuned, controlled,
upfront drums with strong transients and a PRESENT (never dark) top, captured 'dry and compact' with
minimal effects. It chases the TONE, not a groove.

DELIBERATE INVERSIONS (do NOT "fix" them):
  * NO tape and NO reverb/echo — Back in Black is DRY ('AC/DC didn't like to hear any effects'). Do not add
    a Studer/tape darkening stage (that's the Bonham/TNK move) or any ambience.
  * PRESENT, not dark — the post EQ pushes the top a touch (high-shelf BOOST), the OPPOSITE of TNK's cut.
  * SSL comp FAST attack OUT (slow) — transients PASS = crest UP = PUNCH (the measured SSL way). Engaging
    FAST would tame the punch. Keep crest HIGH; don't over-glue.
  * natural width (1.0) — don't narrow (TNK) or hyper-widen (room/gated).

The DEFAULTS reproduce the approved Back-in-Black signature; a bare invocation is unchanged. All enum/float
VST params are set via the tolerant set_param (nearest-valid snap), so e.g. --ssl-ratio 4.0 snaps to the SSL
'4.0' ratio string and --dbx-ratio snaps to ' 4.0:1'. Run with the stemmy-loops `vst` venv.

Honest nuance: 'Back in Black' was tracked at Compass Point (Nassau) to a chosen room 'sweet spot', the kit
low-tuned/muffled, overheads carrying the texture, snare via an H910 — a LIVE/dry capture with minimal
processing. This is an era-appropriate chase of the TIGHT/PUNCHY/DRY/PRESENT tone (Softube transient design
+ SSL E console + dbx VCA), NOT a model of the literal Compass Point signal path. See presets/mix/back-in-black.json.
"""
import argparse, os, sys

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter w/ nearest-valid snap)

TS = "/Library/Audio/Plug-Ins/VST3/Transient Shaper.vst3"             # Softube Transient Shaper
SSLE = "/Library/Audio/Plug-Ins/VST3/SSL 4K E.vst3"                   # SSL's SL 4000 E channel strip
DBX = "/Library/Audio/Plug-Ins/VST3/uaudio_dbx_160.vst3"             # UADx dbx 160 (native build)
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
    ap = argparse.ArgumentParser(description="AC/DC 'Back in Black' tight/punchy/dry drum-bus chain "
                                             "(Softube Transient Shaper -> SSL 4K E -> dbx 160 -> present EQ).")
    ap.add_argument("src"); ap.add_argument("out")
    # Softube Transient Shaper (punch + tighten) -------------------------------------------------
    ap.add_argument("--ts-punch", type=float, default=2.0, help="TS PUNCH dB (attack; keep modest — +3 spits)")
    ap.add_argument("--ts-punch-band", default="WIDE", help="TS punch band (LOW/WIDE/HIGH)")
    ap.add_argument("--ts-punch-type", default="SLOW", help="TS punch type (SLOW=fatter snare crack, FAST=click)")
    ap.add_argument("--ts-sustain", type=float, default=-2.0, help="TS SUSTAIN dB (negative = tighten the boom)")
    ap.add_argument("--ts-sustain-band", default="LOW", help="TS sustain band (LOW tightens kick/snare body, WIDE chokes cymbals)")
    ap.add_argument("--ts-xover", type=float, default=700.0, help="TS crossover Hz (one shared split)")
    ap.add_argument("--no-ts", action="store_true", help="skip the Transient Shaper")
    # SSL 4K E channel strip (weight + punch) ----------------------------------------------------
    ap.add_argument("--ssl-colour", default="Black", help="SSL EQ colour (Black=weighty lows; Brown=brightest; Orange=forward mids)")
    ap.add_argument("--ssl-lf", type=float, default=3.0, help="SSL LF bell gain dB @80 (weight)")
    ap.add_argument("--ssl-debox", type=float, default=-2.0, help="SSL LMF gain dB @450 (de-box)")
    ap.add_argument("--ssl-pres", type=float, default=1.5, help="SSL HMF gain dB @3k (attack/presence)")
    ap.add_argument("--ssl-air", type=float, default=1.5, help="SSL HF shelf gain dB @10k (PRESENT top, not dark)")
    ap.add_argument("--ssl-ratio", default="4.0", help="SSL comp ratio string ('2.0'..'∞'); snapped to nearest valid")
    ap.add_argument("--ssl-thresh", type=float, default=-16.0, help="SSL comp threshold dB (lower = more GR)")
    ap.add_argument("--ssl-release", type=float, default=0.15, help="SSL comp release s")
    ap.add_argument("--ssl-fast", default="Out", help="SSL comp FAST attack ('Out'=slow=PUNCH; 'In'=~1ms=tame)")
    ap.add_argument("--no-ssl", action="store_true", help="skip the SSL 4K E strip")
    # dbx 160 (light VCA punch/glue) -------------------------------------------------------------
    ap.add_argument("--dbx-ratio", default=" 4.0:1", help="dbx ratio string (' 4.0:1' RAISES crest=punch; ' 2.0:1' levels)")
    ap.add_argument("--dbx-thresh", type=float, default=-26.0, help="dbx threshold dBFS (lower = more GR; -26 = light)")
    ap.add_argument("--dbx-gain", type=float, default=3.0, help="dbx makeup gain (peak-trim normalizes it away)")
    ap.add_argument("--no-dbx", action="store_true", help="skip the dbx 160")
    # tonal polish (zero-phase, after the VSTs) --------------------------------------------------
    ap.add_argument("--hpf", type=float, default=35.0, help="pre-chain HPF Hz (tight subsonic)")
    ap.add_argument("--low-shelf", type=float, default=0.5, help="post low_shelf @100 gain dB (a touch of weight)")
    ap.add_argument("--debox-post", type=float, default=-0.5, help="post bell @450 gain dB (gentle de-box guard)")
    ap.add_argument("--snap", type=float, default=0.5, help="post bell @3500 gain dB (stick snap)")
    ap.add_argument("--present", type=float, default=1.0, help="post high_shelf @9k gain dB (PRESENT top — NOT a cut)")
    # natural width (default 1.0 = no-op) --------------------------------------------------------
    ap.add_argument("--width", type=float, default=1.0, help="M/S width 0..1+ (1.0=NATURAL/no-op)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF (zero-phase; tight)
    e1 = src + ".bib1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-D — Transient Shaper -> SSL 4K E -> dbx 160, one chained render
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)   # ensure stereo for the bus image
    chain = []
    if not a.no_ts:
        ts = load_plugin(TS)
        _set_all(ts, {"bypass": False, "punch_db": a.ts_punch, "punch_band": a.ts_punch_band,
                      "punch_type": a.ts_punch_type, "sustain_db": a.ts_sustain,
                      "sustain_band": a.ts_sustain_band, "crossover_freq_hz": a.ts_xover,
                      "output_level_db": 0.0, "clip": False})
        chain.append(ts)
    if not a.no_ssl:
        s = load_plugin(SSLE)
        _set_all(s, {"bypass": False,
                     "filters_in": "In", "high_pass_filter_hz": "OUT", "low_pass_filter_khz": "OUT",
                     "eq_in": "In", "eq_colour": a.ssl_colour,
                     "lf_type": "Bell", "lf_frequency_hz": 80.0, "lf_gain_db": a.ssl_lf,
                     "lmf_frequency_khz": 0.45, "lmf_gain_db": a.ssl_debox, "lmf_q": 1.0,
                     "hmf_frequency_khz": 3.0, "hmf_gain_db": a.ssl_pres, "hmf_q": 1.0,
                     "hf_type": "Shelf", "hf_frequency_khz": 10.0, "hf_gain_db": a.ssl_air,
                     "dynamics_in": "In", "compressor_ratio": a.ssl_ratio,
                     "compressor_threshold_db": a.ssl_thresh, "compressor_release_s": a.ssl_release,
                     "compressor_fast_attack": a.ssl_fast, "compressor_mix": 100.0,
                     "compressor_auto_make_up": True})
        chain.append(s)
    if not a.no_dbx:
        d = load_plugin(DBX)
        _set_all(d, {"power": True, "master_bypass": False, "thresh": a.dbx_thresh,
                     "compress": a.dbx_ratio, "gain": a.dbx_gain, "meter": "GC",
                     "sc_filter": False, "mix": 100.0})
        chain.append(d)
    y = Pedalboard(chain)(x, sr) if chain else x
    e2 = src + ".bib2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage E — PRESENT tonal polish (zero-phase; top BOOST, not a cut)
    e3 = src + ".bib3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=100, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=450, gain_db=a.debox_post, q=1.0),
        EqBand(type="bell", freq_hz=3500, gain_db=a.snap, q=1.2),
        EqBand(type="high_shelf", freq_hz=9000, gain_db=a.present, q=0.7)], phase="zero")

    # Stage F — natural width (default 1.0 = no-op)
    cur = e3
    e4 = None
    if abs(a.width - 1.0) > 1e-6 or a.mono_below > 0:
        e4 = src + ".bib4.wav"
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
    print(f"back-in-black bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
