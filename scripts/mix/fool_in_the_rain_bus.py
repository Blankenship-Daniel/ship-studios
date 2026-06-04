"""John Bonham "Fool In The Rain" room-dominant drum-bus tone chain.

    python fool_in_the_rain_bus.py <in_bus.wav> <out_bus.wav>
        [--helios-gain 40] [--helios-pad "-20 dB"] [--helios-mid 3.0] [--helios-hs 0.0]
        [--helios-level -14.0] [--no-helios]
        [--ips "15 IPS"] [--repro-hf 2.0] [--tape-in 2.0] [--cal 6.0] [--no-tape]
        [--ssl-ratio "4:1"] [--ssl-attack 30] [--ssl-thresh -10.0] [--ssl-makeup 0.0]
        [--ssl-schpf 60] [--ssl-os 2x] [--no-ssl]
        [--hpf 35] [--low-shelf 1.5] [--thump 1.5] [--deharsh -2.0] [--air 0.5]

Applies, to an ALREADY room-forward-balanced drum bus (see presets/mix/fool-in-the-rain.json), the
Bonham chain:
  A. apply_eq          — HPF 35 Hz zero-phase (keep subsonic out of the tape)
  B. Helios Type 69    — warm British transformer + EQ colour (Mic drive + 700 Hz body), NO air
  C. Studer A800 15 IPS NAB — fat ~50-70 Hz head-bump BLOOM + warmth/glue; darkens the top
  D. SSL Bus Comp 2    — clean STEREO VCA glue; slow attack = transients preserved = breathing
  E. apply_eq          — zero-phase polish: low weight + 300 Hz thump + tame 3k + gentle air
then peak-normalize to -1 dBFS.

DELIBERATE INVERSIONS vs warm_bus.py (do NOT "fix" them):
  * 15 IPS, not 30 — the bigger ~50-70 Hz head bump BLOOMS the lows = fat/boomy Bonham bottom.
  * NO low-band multiband — Bonham wants the lows to bloom, not tighten.
  * the upstream balance is room/overhead-FORWARD — the ROOM is the star (the "reverb").

The DEFAULTS reproduce the approved Bonham signature; a bare invocation is unchanged. Tune the SSL
threshold/makeup for ~2-4 dB of glue (crest held ~16-18 dB, NOT < 16 = over-glued). All enum/float
params are set via the tolerant set_param (nearest-valid snap), so e.g. --ssl-schpf 60 snaps to the
nearest valid SSL sidechain corner. Run with the stemmy-loops `vst` venv.

Honest nuance: the real track used an SSL at Polar Studios; Helios is the repo's era-appropriate
Zeppelin-warmth colour (test --no-helios in the shootout). This chases the TONE, not the shuffle GROOVE,
and needs ROOM mics in the source.
"""
import argparse, os, sys

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter w/ nearest-valid snap)

HELIOS = "/Library/Audio/Plug-Ins/VST3/uaudio_helios_type_69.vst3"
STUDER = "/Library/Audio/Plug-Ins/VST3/uaudio_studer_a800.vst3"
SSL = "/Library/Audio/Plug-Ins/VST3/SSL Native Bus Compressor 2.vst3"
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
    ap = argparse.ArgumentParser(description="Bonham 'Fool In The Rain' room-dominant drum-bus chain "
                                             "(Helios -> Studer 15 IPS -> SSL bus comp -> EQ).")
    ap.add_argument("src"); ap.add_argument("out")
    # Helios (warm colour) -----------------------------------------------------------------------
    ap.add_argument("--helios-gain", type=float, default=40.0, help="Helios Mic gain enum [20..70]; 40+pad=-20 dB = ~1.9%% THD sweet spot")
    ap.add_argument("--helios-pad", default="-20 dB", help="Helios pad ('Off' or '-20 dB'); pad lets high gain colour without going nuclear")
    ap.add_argument("--helios-mid", type=float, default=3.0, help="Helios 700 Hz Peak mid_gain (forward body)")
    ap.add_argument("--helios-hs", type=float, default=0.0, help="Helios hi_shelf_gain enum {-16,-12,-8,-4,0,4,8,12}; 0=flat, -4=darker (it only CUTS up high)")
    ap.add_argument("--helios-level", type=float, default=-14.0, help="Helios output level trim dB (compensate the Mic-gain boost feeding the tape)")
    ap.add_argument("--no-helios", action="store_true", help="skip the Helios colour stage")
    # Studer (warm tape) -------------------------------------------------------------------------
    ap.add_argument("--ips", default="15 IPS", help="Studer tape speed ('15 IPS' blooms lows = Bonham; '30 IPS' tightens)")
    ap.add_argument("--repro-hf", type=float, default=2.0, help="Studer repro_hf_eq 0..10 (lower = darker top)")
    ap.add_argument("--tape-in", type=float, default=2.0, help="Studer input_level dB (tape drive/glue)")
    ap.add_argument("--cal", type=float, default=6.0, help="Studer cal_level {3,6,7.5,9}")
    ap.add_argument("--no-tape", action="store_true", help="skip the Studer tape stage")
    # SSL (glue) ---------------------------------------------------------------------------------
    ap.add_argument("--ssl-ratio", default="4:1", help="SSL ratio enum ('1.5:1','2:1','3:1','4:1','10:1','20:1')")
    ap.add_argument("--ssl-attack", type=float, default=10.0, help="SSL attack_ms enum {0.1,0.3,1,3,10,20,30}; 10=classic drum-bus 'breathing' glue (catches peaks yet pumps). NOTE: slower (30) on a very peaky bus RAISES crest")
    ap.add_argument("--ssl-thresh", type=float, default=-14.0, help="SSL threshold_db (lower = more GR; tune for a few dB of glue. On a hyper-dynamic room source the SSL grabs little — that's the source)")
    ap.add_argument("--ssl-makeup", type=float, default=3.0, help="SSL makeup_gain_db (compensate the glue)")
    ap.add_argument("--ssl-schpf", type=float, default=60.0, help="SSL sidechain HPF Hz (keeps the kick from pumping the bus); snapped to nearest valid")
    ap.add_argument("--ssl-os", default="2x", help="SSL oversampling ('OFF','2x','4x')")
    ap.add_argument("--no-ssl", action="store_true", help="skip the SSL glue stage")
    # tonal polish (zero-phase, after the VSTs) --------------------------------------------------
    ap.add_argument("--hpf", type=float, default=35.0, help="pre-chain HPF Hz (subsonic)")
    ap.add_argument("--low-shelf", type=float, default=1.5, help="post low_shelf @120 gain dB (low weight)")
    ap.add_argument("--thump", type=float, default=1.5, help="post bell @300 gain dB (low-mid head bump/thump)")
    ap.add_argument("--deharsh", type=float, default=-2.0, help="post bell @3k gain dB (tame harshness)")
    ap.add_argument("--air", type=float, default=0.5, help="post high_shelf @10k gain dB (gentle air, NOT bright)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF (keep rumble out of the tape)
    e1 = src + ".fitr1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-D — Helios -> Studer -> SSL, one chained render
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)   # ensure stereo for the SSL / bus image
    chain = []
    if not a.no_helios:
        h = load_plugin(HELIOS)
        _set_all(h, {"power": True, "input_select": "Mic", "gain": a.helios_gain, "pad": a.helios_pad,
                     "eq_in": "In", "mid_type": "Peak", "mid_freq": 700.0, "mid_gain": a.helios_mid,
                     "hi_shelf_gain": a.helios_hs, "bass": 0.0, "polarity": "Normal", "level": a.helios_level})
        chain.append(h)
    if not a.no_tape:
        t = load_plugin(STUDER)
        _set_all(t, {"power": True, "path_select": "Repro", "ips": a.ips, "tape_type": "456",
                     "emphasis_eq": "NAB", "cal_level": a.cal, "auto_cal": True, "noise": False,
                     "input_level": a.tape_in, "repro_hf_eq": a.repro_hf, "output_level": 0.0})
        chain.append(t)
    if not a.no_ssl:
        s = load_plugin(SSL)
        _set_all(s, {"comp_bypass": False, "oversampling": a.ssl_os, "ratio": a.ssl_ratio,
                     "attack_ms": a.ssl_attack, "release_s": "AUTO", "threshold_db": a.ssl_thresh,
                     "makeup_gain_db": a.ssl_makeup, "sidechain_hpf_hz": a.ssl_schpf, "dry_wet_mix": 100.0})
        chain.append(s)
    y = Pedalboard(chain)(x, sr) if chain else x
    e2 = src + ".fitr2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage E — tonal polish (zero-phase)
    e3 = src + ".fitr3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=120, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=300, gain_db=a.thump, q=0.8),
        EqBand(type="bell", freq_hz=3000, gain_db=a.deharsh, q=1.0),
        EqBand(type="high_shelf", freq_hz=10000, gain_db=a.air, q=0.7)], phase="zero")

    z, sr = sf.read(e3, dtype="float32", always_2d=True)
    zz = peak_normalize(z.T, OUT_PEAK_DBFS)   # shared core; same -1 dBFS invariant
    sf.write(out, zz.T, sr, subtype="PCM_24")
    for f in (e1, e2, e3):
        try:
            os.remove(f)
        except OSError:
            pass
    _m("FINAL", out)
    print(f"fool-in-the-rain bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
