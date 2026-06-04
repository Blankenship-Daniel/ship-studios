"""The Beatles "Tomorrow Never Knows" (Ringo / Geoff Emerick, 1966) drum-bus tone chain.

    python tomorrow_never_knows_bus.py <in_bus.wav> <out_bus.wav>
        [--fc-input -6] [--fc-thresh 8] [--fc-tc 2] [--fc-headroom 8] [--fc-output 0] [--no-fairchild]
        [--la3a] [--la3a-pr 6] [--la3a-gain 5]
        [--ips "15 IPS"] [--repro-hf 1.5] [--tape-in 3] [--cal 6] [--no-tape]
        [--vibe] [--vibe-machine VINTAGIZE] [--vibe-drive 45]
        [--hpf 35] [--low-shelf 1.5] [--thump 2.0] [--dark -4.0]
        [--width 0.35] [--mono-below 0]

Applies, to an ALREADY tom-forward-balanced drum bus (see presets/mix/tomorrow-never-knows.json),
the TNK chain:
  A. apply_eq          — HPF 35 Hz (zero-phase)
  B. Fairchild 660     — the era/Abbey-Road compressor, driven HARD for audible PUMP (MONO tube vari-mu)
  C. (opt) LA-3A       — opto LIMIT, HF-emphasis 0, high peak-reduction = extra CRUSH + darken (--la3a)
  D. Studer A800 15 IPS NAB — dark, fat tape glue (the J37 is DAW-only, so this is the headless proxy)
  E. (opt) Vibe VINTAGIZE — lo-fi tape grit / band-limit (--vibe)
  F. apply_eq          — zero-phase DARK tilt: low-shelf weight + low-mid thump + high-shelf CUT (no air)
  G. adjust_stereo     — narrow toward MONO (the 1966 image)
then peak-normalize to -1 dBFS.

THE SOUND vs Bonham/fool-in-the-rain (the opposite axis): CRUSH not glue (crest DOWN, audible pump),
NARROW/mono not wide-room (correlation UP), DARK/lo-fi not warm-open. It chases the TONE, not Ringo's
tom GROOVE, and is TOM-FORWARD — so the source wants individual tom mics.

Honest note: the repo's Fairchild COLORS more than it crushes (it holds crest), so even driven hard it
pumps GENTLER than the over-limited 1966 original. For more crush add --la3a (opto, genuinely reduces
crest). All enum/float VST params are set via the harness set_param (nearest-valid snap). Run with the
stemmy-loops `vst` venv.
"""
import argparse, os, sys

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))
from _core import peak_normalize        # noqa: E402
from apply_vst_preset import set_param  # noqa: E402

FAIRCHILD = "/Library/Audio/Plug-Ins/VST3/uaudio_fairchild_660.vst3"
LA3A = "/Library/Audio/Plug-Ins/VST3/uaudio_la3a.vst3"
STUDER = "/Library/Audio/Plug-Ins/VST3/uaudio_studer_a800.vst3"
VIBE = "/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3"   # UADx Vibe Analog Machines (renamed Verve)
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
    ap = argparse.ArgumentParser(description="Tomorrow Never Knows drum-bus chain "
                                             "(Fairchild pump -> Studer 15 IPS dark tape -> dark EQ -> mono narrow).")
    ap.add_argument("src"); ap.add_argument("out")
    # Fairchild 660 (the pump) -------------------------------------------------------------------
    ap.add_argument("--fc-input", type=float, default=-6.0, help="Fairchild input enum (hotter = more GR/pump; -6 is hot)")
    ap.add_argument("--fc-thresh", type=float, default=8.0, help="Fairchild thresh 0..10 (HIGHER = MORE GR on this build — lore-inverted)")
    ap.add_argument("--fc-tc", type=float, default=2.0, help="Fairchild time_const 1..6 (LOWER = faster = more PUMP)")
    ap.add_argument("--fc-headroom", type=float, default=8.0, help="Fairchild headroom {4,8,12,16,20,24,28} (LOWER = hotter/more GR)")
    ap.add_argument("--fc-output", type=float, default=0.0, help="Fairchild output makeup dB")
    ap.add_argument("--fc-scfilt", default="Off", help="Fairchild sidechain filter ('Off' = full-range detection = max pump/dark)")
    ap.add_argument("--no-fairchild", action="store_true", help="skip the Fairchild")
    # LA-3A (optional extra crush) ---------------------------------------------------------------
    ap.add_argument("--la3a", action="store_true", help="add an LA-3A opto LIMIT stage for genuine crest reduction (more crush)")
    ap.add_argument("--la3a-pr", type=float, default=6.0, help="LA-3A peak_reduction 0..10")
    ap.add_argument("--la3a-gain", type=float, default=5.0, help="LA-3A makeup gain 0..10")
    # Studer A800 (dark tape) --------------------------------------------------------------------
    ap.add_argument("--ips", default="15 IPS", help="Studer tape speed (15 IPS = fat/dark)")
    ap.add_argument("--repro-hf", type=float, default=1.5, help="Studer repro_hf_eq 0..10 (LOWER = darker top)")
    ap.add_argument("--tape-in", type=float, default=3.0, help="Studer input_level dB (tape drive/glue)")
    ap.add_argument("--cal", type=float, default=6.0, help="Studer cal_level {3,6,7.5,9}")
    ap.add_argument("--no-tape", action="store_true", help="skip the Studer tape")
    # Vibe (optional lo-fi grit) -----------------------------------------------------------------
    ap.add_argument("--vibe", action="store_true", help="add Vibe Analog Machines for lo-fi grit / band-limit")
    ap.add_argument("--vibe-machine", default="VINTAGIZE", help="Vibe machine (VINTAGIZE = dark lo-fi tape)")
    ap.add_argument("--vibe-drive", type=float, default=45.0, help="Vibe param_1 drive 0..100")
    # dark EQ (zero-phase, after the VSTs) -------------------------------------------------------
    ap.add_argument("--hpf", type=float, default=35.0, help="pre-chain HPF Hz")
    ap.add_argument("--low-shelf", type=float, default=1.5, help="post low_shelf @100 gain dB (weight)")
    ap.add_argument("--thump", type=float, default=2.0, help="post bell @200 gain dB (low-mid thump / tom+kick body)")
    ap.add_argument("--dark", type=float, default=-4.0, help="post high_shelf @8k gain dB (DARK — remove air)")
    # mono narrow --------------------------------------------------------------------------------
    ap.add_argument("--width", type=float, default=0.35, help="M/S width 0..1 (1=full, 0=mono; TNK is narrow)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    a = ap.parse_args()

    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF
    e1 = src + ".tnk1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-E — Fairchild -> (LA-3A) -> Studer -> (Vibe), one chained render
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)
    chain = []
    if not a.no_fairchild:
        fc = load_plugin(FAIRCHILD)
        _set_all(fc, {"power": True, "meter": "GR", "input": a.fc_input, "thresh": a.fc_thresh,
                      "time_const": a.fc_tc, "sc_filt": a.fc_scfilt, "dc_thr": 7.5, "bal": 0.0,
                      "headroom": a.fc_headroom, "output": a.fc_output, "mix": 100.0})
        chain.append(fc)
    if a.la3a:
        la = load_plugin(LA3A)
        _set_all(la, {"power": True, "meter": "GR", "comp_limit": "Limit", "hf_emphasis": 0.0,
                      "peak_reduction": a.la3a_pr, "gain": a.la3a_gain, "mix": 100.0})
        chain.append(la)
    if not a.no_tape:
        t = load_plugin(STUDER)
        _set_all(t, {"power": True, "path_select": "Repro", "ips": a.ips, "tape_type": "456",
                     "emphasis_eq": "NAB", "cal_level": a.cal, "auto_cal": True, "noise": False,
                     "input_level": a.tape_in, "repro_hf_eq": a.repro_hf, "output_level": 0.0})
        chain.append(t)
    if a.vibe:
        v = load_plugin(VIBE)
        _set_all(v, {"power": True, "machine": a.vibe_machine, "param_1": a.vibe_drive,
                     "param_2": 0.0, "output_trim": 0.0})
        chain.append(v)
    y = Pedalboard(chain)(x, sr) if chain else x
    e2 = src + ".tnk2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage F — dark tilt EQ (zero-phase)
    e3 = src + ".tnk3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=100, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=200, gain_db=a.thump, q=0.9),
        EqBand(type="high_shelf", freq_hz=8000, gain_db=a.dark, q=0.7)], phase="zero")

    # Stage G — narrow toward mono (the TNK image)
    e4 = src + ".tnk4.wav"
    adjust_stereo(e3, e4, width=a.width, mono_below_hz=a.mono_below)

    z, sr = sf.read(e4, dtype="float32", always_2d=True)
    zz = peak_normalize(z.T, OUT_PEAK_DBFS)
    sf.write(out, zz.T, sr, subtype="PCM_24")
    for f in (e1, e2, e3, e4):
        try:
            os.remove(f)
        except OSError:
            pass
    _m("FINAL", out)
    print(f"tomorrow-never-knows bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
