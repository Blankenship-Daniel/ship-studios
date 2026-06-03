"""Dry, tight, PUNCHY drum-bus tone chain (the forward-American-console counterpart to warm_bus.py).

    python punchy_bus.py <in_bus.wav> <out_bus.wav>
        [--no-shape] [--lo-trans 0.35] [--mid-trans 0.20] [--mid-gain 0.0]
        [--hi-trans 0.10] [--hi-gain 0.5] [--hpf 35]
        [--in-gain 6] [--api-hp 50] [--comp-thresh -10] [--comp-ratio 4]
        [--comp-attack Slow] [--lf-gain 3.0] [--lmf-gain -2.0] [--width 0.95]

Applies, to an already-balanced DRY drum bus (room + reverb out — see balance_punchy.spec.json), the chain:
  1. apply_eq   — HPF (clear subsonic rumble), zero-phase. No tonal EQ; the API 550 owns tone.
  2. shape_bands — multiband transient design = PUNCH: lift the attack on the kick (low), snare (mid),
                   and cymbal/snare-top snap (high) BEFORE the comp, so the slow-attack comp lets the
                   exaggerated transients through. Skip with --no-shape (API-225 punch only).
  3. API Vision Channel Strip (uaudio_api_vision_channel_strip.vst3) — tighten + punch + 70s console tone
       in one box, driven by --in-gain dB:
         * 215 HPF @ --api-hp  -> tightens the sub (controlled bottom)
         * 225 comp, Old (FB) topology -> PUNCH: it raises crest. Attack: the isolation deep-dive
           ([[api-vision-channel-strip]]) found MEDIUM maxes crest, NOT Slow — confirmed here (Medium
           25.8 > Slow 24.5 > Fast 23.1). BUT Medium's harder envelope pumped up this hiss-y live
           source's noise floor (between hits / in the tail) + a touch of kick box, so the DEFAULT is
           Slow (verified clean, crest 24.5 — still hugely punchy). thresh/ratio = how hard.
         * 550 EQ: lf +gain @100 Peak (low thump) + lmf -gain @500 (clean the box). NO top boost —
           that is what keeps a punchy bus from turning harsh (a boosted 2-5 kHz reads brittle).
  4. M/S narrow toward --width (slight) + peak trim to -1 dBFS.

The DEFAULTS reproduce the APPROVED watercolors dry/tight/punchy bus (the API 225 comp owns the punch —
see tight-70s-api.json: highest crest, tightest correlation, neutral top — with only a GENTLE shape_bands
lift on top), adapted for the darker watercolors kit (width 0.95 not 0.92 — the OH is now the only stereo
source, so don't over-narrow). PUNCHY = crest should RISE vs the input and stay HIGH.

HARD-WON: the transient shaper stacks on top of the 225 comp, which ALREADY emphasizes transients — so
heavy shaping double-dips. The first pass (--mid-trans 0.40 --hi-trans 0.30) made the snare clicky/spitty
(a meter-grounded detect-mix-issues flagged "excessive transient shaping"; the meters showed NO clipping,
so it was a transient/tone defect, not level). Easing to 0.20/0.10 cleared it with ~no crest loss
(24.7 -> 24.5) — proof the punch was the comp, not the shaper. Keep mid/hi-trans gentle. For more snap
WITHOUT harshness, lower --comp-thresh or raise --comp-ratio — never boost the top, never crank the shaper.

Run with the stemmy-loops vst venv (../stemmy-loops-mcp/.venv/bin/python). Pair upstream with the dry
measured balance (close mics forward, OH under, ambience out) — scripts/mix/balance_stems.py.
"""
import sys, os, argparse
import numpy as np, soundfile as sf
from pedalboard import load_plugin, Pedalboard
from stemmy.loops_mcp.tools.apply_eq import apply_eq, EqBand
from stemmy.loops_mcp.tools.shape_bands import shape_bands
from stemmy.loops_mcp._dsp.multiband import BandShape
from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
from stemmy.loops_mcp.tools.measure_stereo import measure_stereo

API = "/Library/Audio/Plug-Ins/VST3/uaudio_api_vision_channel_strip.vst3"
OUT_PEAK_DBFS = -1.0


def _m(tag, f):
    L = measure_loudness(f).model_dump(); S = measure_spectrum(f).model_dump(); T = measure_stereo(f).model_dump()
    print(f"  {tag:<10} centroid {S['spectral_centroid_hz']:5.0f} | tilt {S['spectral_tilt_db_per_octave']:+.2f} "
          f"| crest {L['crest_factor_db']:5.1f} | LUFS {L['integrated_lufs']:6.1f} | corr {T['correlation']:.3f}")


def main():
    ap = argparse.ArgumentParser(description="Dry/tight/punchy drum-bus chain (HPF -> shape_bands punch -> API Vision strip).")
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--no-shape", dest="shape", action="store_false", help="skip the shape_bands transient stage (API-225 punch only)")
    ap.add_argument("--hpf", type=float, default=35.0, help="subsonic HPF Hz (zero-phase)")
    ap.add_argument("--lo-trans", type=float, default=0.35, help="low-band transient lift (kick attack)")
    ap.add_argument("--mid-trans", type=float, default=0.20, help="mid-band transient lift (snare crack); GENTLE — see note")
    ap.add_argument("--mid-gain", type=float, default=0.0, help="mid-band gain dB (negative = drier/less box)")
    ap.add_argument("--hi-trans", type=float, default=0.10, help="high-band transient lift (cymbal/snare snap); GENTLE — see note")
    ap.add_argument("--hi-gain", type=float, default=0.5, help="high-band gain dB")
    ap.add_argument("--xover-lo", type=float, default=120.0); ap.add_argument("--xover-hi", type=float, default=3000.0)
    ap.add_argument("--in-gain", type=float, default=6.0, help="pre-API drive dB (drives the 225 comp)")
    ap.add_argument("--api-hp", type=float, default=50.0, help="API 215 HPF Hz (tighten the sub)")
    ap.add_argument("--comp-thresh", type=float, default=-10.0, help="API 225 threshold (lower = more punch)")
    ap.add_argument("--comp-ratio", type=float, default=4.0, help="API 225 ratio")
    ap.add_argument("--comp-attack", default="Slow", help="API 225 attack; MEDIUM maxes crest (per [[api-vision-channel-strip]]) but pumped the noise floor on this source, so default Slow (clean)")
    ap.add_argument("--comp-release", default="0.10 s", help="API 225 release")
    ap.add_argument("--comp-type", default="Old (FB)", help="API 225 topology ('Old (FB)' = smoother feedback)")
    ap.add_argument("--lf-gain", type=float, default=3.0, help="API 550 LF @100 gain dB (low thump)")
    ap.add_argument("--lmf-gain", type=float, default=-2.0, help="API 550 LMF @500 gain dB (clean box)")
    ap.add_argument("--width", type=float, default=0.95, help="M/S width (slight narrow; 1.0 = unchanged)")
    a = ap.parse_args()
    src, out = a.src, a.out
    tmps = []

    _m("in", src)

    # 1. subsonic HPF (zero-phase) — keep the body, just clear rumble; the API 215 owns the tightening
    e1 = src + ".p1.wav"; tmps.append(e1)
    apply_eq(src, e1, bands=[EqBand(type='high_pass', freq_hz=a.hpf, gain_db=0, q=0.707)], phase='zero')
    cur = e1

    # 2. shape_bands transient design = PUNCH (before the comp)
    if a.shape:
        e2 = src + ".p2.wav"; tmps.append(e2)
        shape_bands(cur, e2, crossovers_hz=[a.xover_lo, a.xover_hi], bands=[
            BandShape(transient=a.lo_trans, gain_db=0.0),
            BandShape(transient=a.mid_trans, gain_db=a.mid_gain),
            BandShape(transient=a.hi_trans, gain_db=a.hi_gain)])
        cur = e2

    # 3. API Vision Channel Strip — tighten + slow-attack comp punch + 550 low thump/box-clean, NO top boost
    params = {
        "input_select": "Line",
        "215_on": True, "215_hp_filter": float(a.api_hp),
        "225_on": True, "225_type": a.comp_type, "225_attack": a.comp_attack,
        "225_ratio": float(a.comp_ratio), "225_thresh": float(a.comp_thresh),
        "225_knee": "Hard", "225_release": a.comp_release,
        "eq_on": True, "eq_type": "550L",
        "550_lf_freq": 100.0, "550_lf_gain": float(a.lf_gain), "550_lf_filter": "Peak",
        "550_lmf_freq": 500.0, "550_lmf_gain": float(a.lmf_gain),
    }
    audio, sr = sf.read(cur, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    x *= 10 ** (a.in_gain / 20.0)
    p = load_plugin(API)
    for k, v in params.items():
        try:
            setattr(p, k, v)
        except Exception as ex:
            print(f"warn: {k}={v!r}: {ex}", file=sys.stderr)
    y = Pedalboard([p])(x, sr)

    # 4. M/S narrow (slight) + peak trim
    if a.width != 1.0 and y.shape[0] == 2:
        mid = (y[0] + y[1]) * 0.5
        side = (y[0] - y[1]) * 0.5 * a.width
        y = np.stack([mid + side, mid - side], 0)
    pk = float(np.max(np.abs(y)))
    if pk > 0:
        y = y * ((10 ** (OUT_PEAK_DBFS / 20)) / pk)
    sf.write(out, y.T, sr, subtype="PCM_24")

    for t in tmps:
        if os.path.exists(t):
            os.remove(t)
    _m("FINAL", out)
    print(f"punchy bus -> {out}  (shape={'on' if a.shape else 'off'})")


if __name__ == "__main__":
    raise SystemExit(main())
