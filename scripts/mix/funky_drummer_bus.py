"""James Brown "Funky Drummer" (Clyde Stubblefield, King Studios 1969) DRY VINTAGE-FUNK drum-bus chain.

    python funky_drummer_bus.py <in_bus.wav> <out_bus.wav>
        [--api-comp-ratio 4] [--api-comp-thresh -8] [--api-hpf 50]
        [--api-lmf 2] [--api-hmf 2] [--no-api]
        [--meq-lm 3] [--meq-dip 3] [--meq-hm 4] [--no-meq]
        [--dbx-ratio " 4.0:1"] [--dbx-thresh -22] [--dbx-gain 3] [--no-dbx]
        [--hlf-lowcut "50 CPS"] [--hlf-highcut "10 KCS"] [--no-hlf]
        [--tape] [--ips "15 IPS"] [--tape-in 2] [--repro-hf 2]
        [--hpf 35] [--low-shelf 0.5] [--snap 0.5]
        [--width 0.45] [--mono-below 0]

Applies, to an ALREADY balanced drum bus (see presets/mix/funky-drummer.json), the Funky-Drummer chain:
  A. apply_eq                  — HPF zero-phase (subsonic)
  B. API Vision channel strip  — forward American-console PUNCH (New(FF) comp) + a mid-forward EQ lift
  C. Pultec MEQ-5              — the passive MIDRANGE signature: low body + carved box + 3 kHz presence/attack
  D. dbx 160                  — tight VCA KNOCK (4:1 raises crest on drums = the funk snap)
  E. (opt) Studer A800 15 IPS — a touch of vintage tape warmth (--tape; OFF by default — funk is fairly dry)
  F. Pultec HLF-3C            — band-LIMIT (low-cut + high-cut) for the vintage, sample-ready lo-fi bandwidth
  G. apply_eq                  — light zero-phase polish (weight + snap)
  H. adjust_stereo             — NARROW toward mono (the 1969 breakbeat image)
then peak-normalize to -1 dBFS.

THE SOUND (a NEW axis): DRY / TIGHT / VINTAGE-FUNK / MONO-ish / MID-FORWARD — the most-sampled breakbeat.
Not warm-room (fool-in-the-rain), not gated-huge (in-the-air-tonight), not present-arena (back-in-black):
a dry, tight, mid-forward kit, band-limited and narrow, sample-ready. It chases the TONE, not the groove.

DELIBERATE INVERSIONS (do NOT "fix" them):
  * MID-FORWARD — the MEQ-5 BOOSTS the mids (don't scoop them); the funk presence lives in the midrange.
  * BAND-LIMITED — the HLF-3C cuts sub AND the very top (10 KCS) for the vintage/sample-ready bandwidth;
    do NOT restore full-range air/sub (that would un-vintage it).
  * MONO-ish / NARROW (width ~0.45) — the 1969 image is narrow (like tomorrow-never-knows, the opposite of
    in-the-air-tonight's wide). Do NOT widen.
  * DRY — tape is OFF by default (--tape adds a touch); no reverb/echo.

The DEFAULTS reproduce the approved Funky-Drummer signature; a bare invocation is unchanged. All enum/float
VST params are set via the tolerant set_param (nearest-valid snap), so e.g. --dbx-ratio snaps to ' 4.0:1' and
the Pultec CPS/KCS labels snap to the nearest valid corner. Run with the stemmy-loops `vst` venv.

Honest nuance: 'Funky Drummer' was cut at King Studios, Cincinnati (Nov 1969); the 8-bar break is Clyde
Stubblefield's, recorded dry/mid-forward on period gear and later sampled on 1000+ records. This is an
era-appropriate chase of the dry/tight/mid-forward/sample-ready TONE (American console + passive Pultec mid
EQ + dbx VCA + a vintage band-limit), NOT a model of the literal King Studios path. See presets/mix/funky-drummer.json.
"""
import argparse, os, sys

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter w/ nearest-valid snap)

API = "/Library/Audio/Plug-Ins/VST3/uaudio_api_vision_channel_strip.vst3"
MEQ = "/Library/Audio/Plug-Ins/VST3/uaudio_pultec_meq-5.vst3"
DBX = "/Library/Audio/Plug-Ins/VST3/uaudio_dbx_160.vst3"
HLF = "/Library/Audio/Plug-Ins/VST3/uaudio_pultec_hlf-3c.vst3"
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
    ap = argparse.ArgumentParser(description="James Brown 'Funky Drummer' dry vintage-funk drum-bus chain "
                                             "(API Vision -> Pultec MEQ-5 -> dbx 160 -> Pultec HLF-3C -> narrow).")
    ap.add_argument("src"); ap.add_argument("out")
    # API Vision channel strip (forward punch + mid-forward EQ) -----------------------------------
    ap.add_argument("--api-comp-ratio", type=float, default=4.0, help="API 225 comp ratio (forward density/punch)")
    ap.add_argument("--api-comp-thresh", type=float, default=-8.0, help="API 225 comp threshold dB (lower = more GR)")
    ap.add_argument("--api-hpf", type=float, default=50.0, help="API 215 console HPF Hz (12-596 valid; <12 bypasses)")
    ap.add_argument("--api-lmf", type=float, default=2.0, help="API 550 LMF gain dB @700 (mid-forward funk; snaps to grid)")
    ap.add_argument("--api-hmf", type=float, default=2.0, help="API 550 HMF gain dB @3k (attack; snaps to grid)")
    ap.add_argument("--no-api", action="store_true", help="skip the API Vision strip")
    # Pultec MEQ-5 (passive midrange) ------------------------------------------------------------
    ap.add_argument("--meq-lm", type=float, default=3.0, help="MEQ-5 LOW PEAK @200 CPS 0..10 (~dB; body/thump)")
    ap.add_argument("--meq-dip", type=float, default=3.0, help="MEQ-5 DIP @500 CPS 0..10 (carve the box)")
    ap.add_argument("--meq-hm", type=float, default=4.0, help="MEQ-5 HIGH PEAK @3 KCS 0..10 (~dB; presence/attack)")
    ap.add_argument("--no-meq", action="store_true", help="skip the Pultec MEQ-5 midrange stage")
    # dbx 160 (tight VCA knock) ------------------------------------------------------------------
    ap.add_argument("--dbx-ratio", default=" 4.0:1", help="dbx ratio string (' 4.0:1' RAISES crest=knock; snapped)")
    ap.add_argument("--dbx-thresh", type=float, default=-22.0, help="dbx threshold dBFS (lower = more GR/knock)")
    ap.add_argument("--dbx-gain", type=float, default=3.0, help="dbx makeup gain (peak-trim normalizes it away)")
    ap.add_argument("--no-dbx", action="store_true", help="skip the dbx 160")
    # optional Studer tape (vintage warmth; OFF by default) --------------------------------------
    ap.add_argument("--tape", action="store_true", help="add a touch of Studer 15 IPS tape warmth (funk is fairly dry)")
    ap.add_argument("--ips", default="15 IPS", help="Studer tape speed (15 IPS = vintage/warm)")
    ap.add_argument("--tape-in", type=float, default=2.0, help="Studer input_level dB (gentle vintage warmth)")
    ap.add_argument("--repro-hf", type=float, default=2.0, help="Studer repro_hf_eq 0..10 (lower = darker top)")
    # Pultec HLF-3C (band-limit = sample-ready lo-fi) --------------------------------------------
    ap.add_argument("--hlf-lowcut", default="50 CPS", help="HLF-3C low-cut corner (CPS); tightens sub")
    ap.add_argument("--hlf-highcut", default="10 KCS", help="HLF-3C high-cut corner (KCS); 10 KCS = vintage top rolloff")
    ap.add_argument("--no-hlf", action="store_true", help="skip the Pultec HLF-3C band-limit (keeps full range)")
    # tonal polish (zero-phase, after the VSTs) --------------------------------------------------
    ap.add_argument("--hpf", type=float, default=35.0, help="pre-chain HPF Hz (subsonic)")
    ap.add_argument("--low-shelf", type=float, default=0.5, help="post low_shelf @80 gain dB (a touch of weight)")
    ap.add_argument("--snap", type=float, default=0.5, help="post bell @3500 gain dB (stick snap)")
    # narrow toward mono -------------------------------------------------------------------------
    ap.add_argument("--width", type=float, default=0.45, help="M/S width 0..1 (1=full, 0=mono; funk break is narrow)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from pedalboard import Pedalboard, load_plugin
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq

    src, out = a.src, a.out
    _m("in", src)

    # Stage A — subsonic HPF (zero-phase)
    e1 = src + ".funky1.wav"
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    # Stages B-F — API -> MEQ-5 -> dbx -> (Studer) -> HLF-3C, one chained render
    audio, sr = sf.read(e1, dtype="float32", always_2d=True)
    x = audio.T.copy()
    if x.shape[0] == 1:
        x = np.repeat(x, 2, 0)   # ensure stereo for the bus image (narrowed at the end)
    chain = []
    if not a.no_api:
        p = load_plugin(API)
        params = {"input_select": "Line", "line_gain": 0.0, "sc_link": True,
                  "215_on": a.api_hpf >= 12, "225_on": True, "225_type": "New (FF)",
                  "225_attack": "Medium", "225_ratio": a.api_comp_ratio, "225_thresh": a.api_comp_thresh,
                  "225_knee": "Hard", "225_release": "0.12 s",
                  "eq_on": True, "eq_type": "550L",
                  "550_lf_freq": 100.0, "550_lf_gain": 2.0,
                  "550_lmf_freq": 700.0, "550_lmf_gain": a.api_lmf,
                  "550_hmf_freq": 3000.0, "550_hmf_gain": a.api_hmf,
                  "550_hf_freq": 5000.0, "550_hf_gain": 0.0}
        if a.api_hpf >= 12:
            params["215_hp_filter"] = a.api_hpf
        _set_all(p, params)
        chain.append(p)
    if not a.no_meq:
        mq = load_plugin(MEQ)
        _set_all(mq, {"power": True, "master_bypass": False, "enable": "In",
                      "lm_freq": "200 CPS", "lm_peak": a.meq_lm,
                      "mid_freq": "500 CPS", "mid_dip": a.meq_dip,
                      "hm_freq": "3 KCS", "hm_peak": a.meq_hm, "output": "0.0 dB"})
        chain.append(mq)
    if not a.no_dbx:
        d = load_plugin(DBX)
        _set_all(d, {"power": True, "master_bypass": False, "thresh": a.dbx_thresh,
                     "compress": a.dbx_ratio, "gain": a.dbx_gain, "meter": "GC",
                     "sc_filter": False, "mix": 100.0})
        chain.append(d)
    if a.tape:
        t = load_plugin(STUDER)
        _set_all(t, {"power": True, "path_select": "Repro", "ips": a.ips, "tape_type": "456",
                     "emphasis_eq": "NAB", "cal_level": 6.0, "auto_cal": True, "noise": False,
                     "input_level": a.tape_in, "repro_hf_eq": a.repro_hf, "output_level": 0.0})
        chain.append(t)
    if not a.no_hlf:
        hl = load_plugin(HLF)
        _set_all(hl, {"master_bypass": False, "enable": "In",
                      "low_cut": a.hlf_lowcut, "high_cut": a.hlf_highcut})
        chain.append(hl)
    y = Pedalboard(chain)(x, sr) if chain else x
    e2 = src + ".funky2.wav"
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage G — light tonal polish (zero-phase)
    e3 = src + ".funky3.wav"
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=80, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=3500, gain_db=a.snap, q=1.2)], phase="zero")

    # Stage H — narrow toward mono (the breakbeat image)
    cur = e3
    e4 = None
    if abs(a.width - 1.0) > 1e-6 or a.mono_below > 0:
        e4 = src + ".funky4.wav"
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
    print(f"funky-drummer bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
