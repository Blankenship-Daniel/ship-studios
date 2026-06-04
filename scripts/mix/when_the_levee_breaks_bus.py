"""Led Zeppelin "When the Levee Breaks" (Bonham / Andy Johns, Headley Grange 1971) DISTANT-CRUSH drum-bus chain.

    python when_the_levee_breaks_bus.py <in_bus.wav> <out_bus.wav>
        [--dist-ratio "10:1"] [--dist-detector HP] [--dist-audio "Dist 2"]
        [--dist-input 8] [--dist-attack 4] [--dist-release 2] [--dist-output 7] [--no-dist]
        [--dbx-ratio " 4.0:1"] [--dbx-thresh -26] [--dbx-gain 3] [--no-dbx]
        [--ips "15 IPS"] [--tape-in 3] [--repro-hf 1.5] [--cal 6] [--no-tape]
        [--echo-time 120] [--echo-feedback 0.5] [--echo-mix 0.25] [--echo-damp 3000] [--echo-taps 4] [--no-echo]
        [--hpf 35] [--low-shelf 1.5] [--thump 2.0] [--dark -4.0]
        [--width 0.6] [--mono-below 0]

Applies, to an ALREADY balanced drum bus (see presets/mix/when-the-levee-breaks.json), the Levee chain:
  A. apply_eq          — HPF zero-phase (subsonic)
  B. Distressor        — driven HARD (10:1, Dist 2) = the aggressive Helios F760 comp/limiter 'breathing'
  C. dbx 160          — tight VCA pump/cohesion under the crush
  D. Studer A800 15 IPS — dark, FAT tape (the cavernous low-mid weight)
  E. BINSON ECHO       — a deterministic numpy multi-tap, HF-damped slap = the Binson Echorec cavern
  F. apply_eq          — zero-phase DARK tilt: low weight + low-mid thump + high-shelf CUT (no air)
  G. adjust_stereo     — narrow (the two-distant-mic stairwell image, NOT a wide warm room)
then peak-normalize to -1 dBFS.

THE SOUND (a NEW axis) vs Bonham/fool-in-the-rain: that recipe is the WARM ROOM as a LAYER (wide, clean SSL
glue, big-but-open). THIS is the two-DISTANT-MIC CRUSH: only the stairwell ambience IS the kit, aggressively
compressed so it BREATHES/pumps, DARK and cavernous, NARROWER. It chases the TONE, not a groove.

DELIBERATE INVERSIONS vs fool-in-the-rain (do NOT "fix" them):
  * AGGRESSIVE crush (Distressor 10:1) not clean SSL glue — crest goes DOWN, the kit breathes/pumps.
  * DARK (15 IPS fat tape + a high-shelf CUT) not warm-open — remove the air; it's cavernous.
  * NARROWER (the two-distant-mic image) not the wide warm room.
  * a Binson-style ECHO (numpy, deterministic) adds the cavern — fool-in-the-rain has none.

The DEFAULTS reproduce the approved Levee signature; a bare invocation is unchanged. All enum/float VST
params are set via the tolerant set_param (nearest-valid snap). The echo is pure numpy (deterministic). Run
with the stemmy-loops `vst` venv.

Honest nuance: the original was Bonham at the bottom of Headley Grange's stairwell, captured by just TWO
Beyerdynamic M160 ribbons at the top, amplified/compressed through a Helios console (a pair of Helios F760
comp/limiters, set aggressively for the 'breathing'), with a Binson Echorec on the mix. This is an
era-appropriate chase of that distant/crushed/dark/cavernous TONE (Distressor + dbx + Studer 15 IPS + a
numpy Binson echo), NOT a model of the literal Headley Grange path. See presets/mix/when-the-levee-breaks.json.
"""
import argparse, os, sys

import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter w/ nearest-valid snap)

DISTRESSOR = "/Library/Audio/Plug-Ins/VST3/uaudio_distressor.vst3"
DBX = "/Library/Audio/Plug-Ins/VST3/uaudio_dbx_160.vst3"
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


def _binson_echo(x, sr, time_ms, feedback, mix, damp_hz, taps):
    """A deterministic multi-tap, HF-damped echo = the Binson Echorec cavern. x is (2,n)."""
    n = x.shape[1]
    d = int(time_ms / 1000.0 * sr)
    if d < 1 or mix <= 0 or taps < 1:
        return x
    sos = butter(1, min(damp_hz, sr * 0.49), btype="low", fs=sr, output="sos")
    wet = np.zeros_like(x)
    for t in range(1, taps + 1):
        off = t * d
        if off >= n:
            break
        shifted = np.zeros_like(x)
        shifted[:, off:] = x[:, : n - off]
        wet += sosfilt(sos, shifted).astype(np.float32) * (feedback ** t)  # each repeat darker + quieter
    return x + mix * wet


def main():
    ap = argparse.ArgumentParser(description="Led Zeppelin 'When the Levee Breaks' distant-crush drum-bus chain "
                                             "(Distressor -> dbx 160 -> Studer 15 IPS -> Binson echo -> dark -> narrow).")
    ap.add_argument("src"); ap.add_argument("out")
    # Distressor (the aggressive Helios F760 'breathing' proxy) ----------------------------------
    ap.add_argument("--dist-ratio", default="10:1", help="Distressor ratio string ('2:1'..'20:1','NUKE'); 10:1 = aggressive")
    ap.add_argument("--dist-detector", default="HP", help="Distressor detector ('HP' keeps the kick punching, 'Emp' grabs highs)")
    ap.add_argument("--dist-audio", default="Dist 2", help="Distressor audio mode ('Dist 2'/'Dist 3' = warmth/grit)")
    ap.add_argument("--dist-input", type=float, default=8.0, help="Distressor input drive (more = more GR/crush)")
    ap.add_argument("--dist-attack", type=float, default=4.0, help="Distressor attack (4 = medium-fast, dense)")
    ap.add_argument("--dist-release", type=float, default=2.0, help="Distressor release (2 = fast = aggressive pump)")
    ap.add_argument("--dist-output", type=float, default=7.0, help="Distressor output makeup")
    ap.add_argument("--no-dist", action="store_true", help="skip the Distressor")
    # dbx 160 (VCA pump/cohesion) ----------------------------------------------------------------
    ap.add_argument("--dbx-ratio", default=" 4.0:1", help="dbx ratio string (snapped); tightens under the crush")
    ap.add_argument("--dbx-thresh", type=float, default=-26.0, help="dbx threshold dBFS")
    ap.add_argument("--dbx-gain", type=float, default=3.0, help="dbx makeup gain")
    ap.add_argument("--no-dbx", action="store_true", help="skip the dbx 160")
    # Studer A800 (dark, fat 15 IPS tape) --------------------------------------------------------
    ap.add_argument("--ips", default="15 IPS", help="Studer tape speed (15 IPS = fat/dark cavern)")
    ap.add_argument("--tape-in", type=float, default=3.0, help="Studer input_level dB (tape drive/glue)")
    ap.add_argument("--repro-hf", type=float, default=1.5, help="Studer repro_hf_eq 0..10 (LOWER = darker top)")
    ap.add_argument("--cal", type=float, default=6.0, help="Studer cal_level {3,6,7.5,9}")
    ap.add_argument("--no-tape", action="store_true", help="skip the Studer tape")
    # Binson-style echo (numpy, deterministic) ---------------------------------------------------
    ap.add_argument("--echo-time", type=float, default=120.0, help="echo tap time ms (the slap/cavern spacing)")
    ap.add_argument("--echo-feedback", type=float, default=0.5, help="per-tap decay 0..1 (the cavern length)")
    ap.add_argument("--echo-mix", type=float, default=0.25, help="echo wet blend 0..1 (0 = dry)")
    ap.add_argument("--echo-damp", type=float, default=3000.0, help="echo repeat low-pass Hz (lower = darker repeats)")
    ap.add_argument("--echo-taps", type=int, default=4, help="number of echo repeats")
    ap.add_argument("--no-echo", action="store_true", help="skip the Binson echo (A/B)")
    # dark EQ (zero-phase, after the chain) ------------------------------------------------------
    ap.add_argument("--hpf", type=float, default=35.0, help="pre-chain HPF Hz (subsonic)")
    ap.add_argument("--low-shelf", type=float, default=1.5, help="post low_shelf @100 gain dB (weight)")
    ap.add_argument("--thump", type=float, default=2.0, help="post bell @200 gain dB (low-mid cavern thump)")
    ap.add_argument("--dark", type=float, default=-4.0, help="post high_shelf @7k gain dB (DARK — remove air)")
    # narrow (the distant-mic image) -------------------------------------------------------------
    ap.add_argument("--width", type=float, default=0.6, help="M/S width 0..1 (narrower than the warm room; not full mono)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF (zero-phase)
    e1 = src + ".levee1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-D — Distressor -> dbx 160 -> Studer, one chained render
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    chain = []
    if not a.no_dist:
        di = load_plugin(DISTRESSOR)
        _set_all(di, {"power": True, "master_bypass": False, "bypass": "Off", "ratio": a.dist_ratio,
                      "detector": a.dist_detector, "audio": a.dist_audio, "input": a.dist_input,
                      "attack": a.dist_attack, "release": a.dist_release, "output": a.dist_output,
                      "mix": 100.0, "headroom": 16.0})
        chain.append(di)
    if not a.no_dbx:
        d = load_plugin(DBX)
        _set_all(d, {"power": True, "master_bypass": False, "thresh": a.dbx_thresh,
                     "compress": a.dbx_ratio, "gain": a.dbx_gain, "meter": "GC",
                     "sc_filter": False, "mix": 100.0})
        chain.append(d)
    if not a.no_tape:
        t = load_plugin(STUDER)
        _set_all(t, {"power": True, "path_select": "Repro", "ips": a.ips, "tape_type": "456",
                     "emphasis_eq": "NAB", "cal_level": a.cal, "auto_cal": True, "noise": False,
                     "input_level": a.tape_in, "repro_hf_eq": a.repro_hf, "output_level": 0.0})
        chain.append(t)
    y = Pedalboard(chain)(x, sr) if chain else x

    # Stage E — Binson-style echo (numpy, deterministic)
    if not a.no_echo:
        y = _binson_echo(y, sr, a.echo_time, a.echo_feedback, a.echo_mix, a.echo_damp, a.echo_taps)
    e2 = src + ".levee2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage F — dark tilt EQ (zero-phase)
    e3 = src + ".levee3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=100, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=200, gain_db=a.thump, q=0.9),
        EqBand(type="high_shelf", freq_hz=7000, gain_db=a.dark, q=0.7)], phase="zero")

    # Stage G — narrow (the distant-mic image)
    cur = e3
    e4 = None
    if abs(a.width - 1.0) > 1e-6 or a.mono_below > 0:
        e4 = src + ".levee4.wav"
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
    print(f"when-the-levee-breaks bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
