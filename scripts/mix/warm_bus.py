"""Warm, tight/controlled-bottom drum-bus tone chain.

    python warm_bus.py <in_bus.wav> <out_bus.wav>
        [--hs-gain -4.0] [--hs-freq 6000] [--low-shelf-gain 1.5] [--bell-gain -1.5]
        [--repro-hf 2.0] [--tape-in-gain 5.0]

Applies, to an already-balanced drum bus, the validated chain:
  1. apply_eq  — HPF 35 (clean sub) + warm tilt (low-shelf +1.5@180, bell -1.5@2.5k, high-shelf -4@6k), zero-phase
  2. multiband_compress — control the LOW band (<110 Hz, 3:1) so the bottom is tight/even, no bloom
  3. Studer A800 @ 30 IPS — tape warmth + glue; 30 IPS keeps the head-bump up ~100 Hz (tight lows, no sub bloom)

The DEFAULTS reproduce the approved warm-tight signature (a bare `warm_bus.py <in> <out>` is unchanged).
The optional knobs adapt the chain to a darker/brighter source WITHOUT abandoning the recipe (see the
warm-drum-bus pitfalls): a source that over-darkens -> ease `--hs-gain` toward -2 and raise `--repro-hf`
toward 3 (more air); a result that over-glues (crest < ~20) -> lower `--tape-in-gain` toward 4.

Measured effect on a typical kit: centroid down, tilt more negative (warm), correlation up (tight),
low band controlled. Run with the stemmy-loops vst venv. Pair upstream with a warm-leaning measured
balance (bright stems down, room/body up) — see scripts/mix/balance_stems.py.
"""
import argparse, os, sys, tempfile
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import peak_normalize    # noqa: E402

STUDER = "/Library/Audio/Plug-Ins/VST3/uaudio_studer_a800.vst3"
OUT_PEAK_DBFS = -1.0


def warm_tilt_bands(hs_gain=-4.0, hs_freq=6000.0, low_shelf_gain=1.5, bell_gain=-1.5):
    """The SHIPPED warm tilt as plain dicts — the single source of truth for the recipe.

    Pulled out of main() so the approved signature is testable without pedalboard,
    stemmy, or an audio file. It is what actually renders: `_core.warm_tilt_eq` is a
    DIFFERENT algorithm (rFFT magnitude shaping) that this chain does not use, so
    tests written against it proved nothing about the bus — flipping `--hs-gain` from
    -4 to +4 turned the "warm" bus bright with the suite still green.

    Warmth here is a downward tilt: low shelf UP, presence bell DOWN, high shelf DOWN.
    """
    return [
        {"type": "high_pass",  "freq_hz": 35.0,     "gain_db": 0.0,            "q": 0.707},
        {"type": "low_shelf",  "freq_hz": 180.0,    "gain_db": low_shelf_gain, "q": 0.7},
        {"type": "bell",       "freq_hz": 2500.0,   "gain_db": bell_gain,      "q": 0.9},
        {"type": "high_shelf", "freq_hz": hs_freq,  "gain_db": hs_gain,        "q": 0.7},
    ]

def _m(tag, f):
    from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
    from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
    from stemmy.loops_mcp.tools.measure_stereo import measure_stereo
    L=measure_loudness(f).model_dump(); S=measure_spectrum(f).model_dump(); T=measure_stereo(f).model_dump()
    print(f"  {tag:<10} centroid {S['spectral_centroid_hz']:5.0f} | tilt {S['spectral_tilt_db_per_octave']:+.2f} "
          f"| crest {L['crest_factor_db']:5.1f} | LUFS {L['integrated_lufs']:6.1f} | corr {T['correlation']:.3f}")

def main():
    ap=argparse.ArgumentParser(description="Warm/tight drum-bus tone chain (zero-phase tilt -> low multiband -> Studer A800 30 IPS).")
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--hs-gain", type=float, default=-4.0, help="high-shelf gain dB (ease toward -2 for a dark source)")
    ap.add_argument("--hs-freq", type=float, default=6000.0, help="high-shelf freq Hz")
    ap.add_argument("--low-shelf-gain", type=float, default=1.5, help="low-shelf @180 gain dB")
    ap.add_argument("--bell-gain", type=float, default=-1.5, help="bell @2.5k gain dB")
    ap.add_argument("--repro-hf", type=float, default=2.0, help="Studer repro_hf_eq (raise toward 3 for more air)")
    ap.add_argument("--tape-in-gain", type=float, default=5.0, help="pre-tape drive dB (lower toward 4 for less glue / more crest)")
    a=ap.parse_args()
    # vst/tool imports are deferred to here so --help works without the vst venv (render is unchanged)
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq
    from stemmy.loops_mcp.tools.multiband_compress import multiband_compress
    src, out = a.src, a.out
    TAPE = {"path_select":"Repro","ips":"30 IPS","tape_type":"456","auto_cal":True,
            "input_level":4.0,"repro_hf_eq":a.repro_hf,"emphasis_eq":"NAB"}
    _m("in", src)
    # Intermediates go to a TemporaryDirectory, not `src + ".w1.wav"` next to the
    # user's source: those were removed only on the happy path, so any failure
    # (missing Studer, bad rate, read-only out dir) littered projects/<t>/mix/ with
    # files the next glob-based stem scan would pick up as stems — and two concurrent
    # runs on one source clobbered each other's.
    with tempfile.TemporaryDirectory(prefix="warm_bus.") as tmp:
        e1 = os.path.join(tmp, "w1.wav")
        e2 = os.path.join(tmp, "w2.wav")
        apply_eq(src, e1, phase='zero', bands=[
            EqBand(**b) for b in warm_tilt_bands(
                a.hs_gain, a.hs_freq, a.low_shelf_gain, a.bell_gain)])
        multiband_compress(e1, e2, crossovers_hz=[110,3000], threshold_db=[-24,-34,-34],
            ratio=[3.0,1.3,1.3], attack_ms=[18,30,30], release_ms=[140,150,150])
        audio,sr=sf.read(e2,dtype="float32",always_2d=True); x=audio.T.copy()*10**(a.tape_in_gain/20)
        p=load_plugin(STUDER)
        for k,v in TAPE.items():
            try: setattr(p,k,v)
            except Exception as ex: print(f"warn: {k}={v!r}: {ex}", file=sys.stderr)
        y=Pedalboard([p])(x,sr)
        y=peak_normalize(y, OUT_PEAK_DBFS)   # same math; shared core
        sf.write(out, y.T, sr, subtype="PCM_24")
    _m("FINAL", out)
    print(f"warm bus -> {out}")

if __name__=="__main__":
    raise SystemExit(main())
