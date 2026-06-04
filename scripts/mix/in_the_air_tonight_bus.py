"""Phil Collins "In the Air Tonight" (Hugh Padgham, 1981) GATED-REVERB drum-bus tone chain.

    python in_the_air_tonight_bus.py <in_bus.wav> <out_bus.wav>
        [--hpf 30]
        [--decay-s 1.6] [--reverb-dark 9000] [--reverb-seed 1981] [--predelay-ms 8]
        [--rev-comp-thresh -30] [--rev-comp-ratio 8] [--rev-comp-attack 1] [--rev-comp-release 200]
        [--gate-thresh-pct 50] [--gate-hold-ms 320] [--gate-release-ms 28] [--gate-floor-db -60]
        [--wet 0.7]
        [--low-shelf 1.0] [--crack 2.0] [--air 1.0]
        [--width 1.4] [--mono-below 0]
        [--reverb-vst ""] [--reverb-vst-mix 100] [--no-gate] [--no-comp]

Applies, to an ALREADY balanced drum bus (see presets/mix/in-the-air-tonight.json), the gated-reverb
chain that defined the 1980s — Padgham's accident on Peter Gabriel's "Intruder", made famous on "In the
Air Tonight":
  A. apply_eq          — HPF zero-phase (keep subsonic out of the reverb)
  B. SYNTH REVERB      — a deterministic decaying-noise impulse (seeded -> bit-reproducible), convolved
                         on the dry kit = a big, slightly dark room ambience. (NOT a VST by default.)
  C. HEAVY COMPRESSION — the ambience is CRUSHED (compress-loop, low thresh + high ratio + auto-makeup):
                         this is the SSL-channel "talkback-comp" move that makes the room EXPLODE.
  D. ABRUPT NOISE GATE — the crushed ambience is keyed off the DRY kit envelope, held open for a fixed
                         window, then SLAMMED shut (short release). The abrupt cutoff IS the sound.
  E. BLEND wet+dry     — the gated explosion sits UNDER the dry hits (--wet).
  F. apply_eq          — present/CRACK polish (low weight + 4 kHz crack + gentle air), zero-phase.
  G. adjust_stereo     — WIDE (the HUGE 80s image; the OPPOSITE of tomorrow-never-knows' mono).
then peak-normalize to -1 dBFS.

THE SOUND vs the other famous-drum recipes (a NEW axis): EXPLOSIVE / GATED / HUGE. Not warm-room-as-a-
layer (fool-in-the-rain), not mono-crush (tomorrow-never-knows), not clean-dynamic (home-at-last): a
heavily-compressed ambience cut off abruptly by a gate, blended big and WIDE. It chases the gated-reverb
TONE, not a specific groove.

DELIBERATE INVERSIONS (do NOT "fix" them):
  * The reverb is CRUSHED then GATED — the abrupt tail cutoff is the signature; do not soften the close.
  * width goes WIDE (the opposite of TNK's mono) — the explosion fills the stereo field.
  * the reverb is a DETERMINISTIC synthesized IR by default (NOT a VST) so a bare invocation reproduces
    the approved signature bit-for-bit. --reverb-vst routes a real reverb instead, but that path is a
    CREATIVE alternative, NOT the locked signature (load != render — verify it actually processed).

The DEFAULTS reproduce the approved In-the-Air-Tonight signature; a bare invocation is unchanged and
fully reproducible (synth reverb + numpy gate are deterministic). Run with the stemmy-loops `vst` venv
(compress-loop + apply_eq + adjust_stereo + scipy live there; no VST is loaded on the default path).

Honest nuance: the real effect was an SSL 4000 channel's compressor+gate on a talkback room mic into an
AMS/Lexicon-style ambience; this is an era-appropriate, deterministic pure-DSP chase of that gated-room
TONE, not a model of the literal Townhouse Studio signal path. See presets/mix/in-the-air-tonight.json.
"""
import argparse, os, sys

import numpy as np, soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, fftconvolve, sosfilt

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                              # scripts/mix (for _core)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # for set_param (optional VST reverb)
from _core import peak_normalize        # noqa: E402  (pure-DSP core: the -1 dBFS normalize invariant)
from apply_vst_preset import set_param  # noqa: E402  (tolerant enum/float setter; only used for --reverb-vst)

OUT_PEAK_DBFS = -1.0


def _m(tag, f):
    from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
    from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
    from stemmy.loops_mcp.tools.measure_stereo import measure_stereo
    L = measure_loudness(f).model_dump(); S = measure_spectrum(f).model_dump(); T = measure_stereo(f).model_dump()
    print(f"  {tag:<10} centroid {S['spectral_centroid_hz']:5.0f} | tilt {S['spectral_tilt_db_per_octave']:+.2f} "
          f"| crest {L['crest_factor_db']:5.1f} | LUFS {L['integrated_lufs']:6.1f} | corr {T['correlation']:.3f}")


def _reverb_ir(sr, decay_s, dark_hz, seed):
    """A deterministic decaying-noise reverb impulse — seeded RNG so the render is bit-reproducible.

    White noise * an exponential decay (≈ -52 dB by decay_s), band-limited dark (LPF dark_hz) and HPF'd
    at 120 Hz so the verb doesn't muddy the low end, then energy-normalized. Two different seeds give a
    decorrelated L/R pair = a wide room.
    """
    n = max(1, int(decay_s * sr))
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-t / (decay_s / 6.0)).astype(np.float32)
    sos_lp = butter(2, min(dark_hz, sr * 0.49), btype="low", fs=sr, output="sos")
    sos_hp = butter(2, 120.0, btype="high", fs=sr, output="sos")
    ir = sosfilt(sos_hp, sosfilt(sos_lp, ir)).astype(np.float32)
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)


def _synth_wet(dry_mono, sr, decay_s, dark_hz, seed, predelay_ms):
    """Convolve the dry kit with a decorrelated L/R IR pair -> a wide, slightly dark room (stereo (2,n))."""
    pre = max(0, int(predelay_ms / 1000.0 * sr))
    d = np.concatenate([np.zeros(pre, np.float32), dry_mono]) if pre else dry_mono
    n = len(dry_mono)
    wl = fftconvolve(d, _reverb_ir(sr, decay_s, dark_hz, seed))[:n]
    wr = fftconvolve(d, _reverb_ir(sr, decay_s, dark_hz, seed + 1))[:n]
    return np.stack([wl, wr], 0).astype(np.float32)


def _vst_wet(dry, sr, plugin_path, wet_mix):
    """Render the dry through a real reverb VST as the wet (best-effort 100%-wet). NOT the locked path."""
    from pedalboard import Pedalboard, load_plugin
    p = load_plugin(plugin_path)
    for k in ("mix", "wet", "dry_wet", "dry_wet_mix", "mix_percent", "wet_dry"):
        if set_param(p, k, float(wet_mix)) is None:
            break
    return Pedalboard([p])(dry, sr).astype(np.float32)


def _abrupt_gate(dry_mono, sr, thresh_pct, hold_ms, release_ms, floor_db):
    """A noise gate keyed off the DRY kit: instant open on a hit, HOLD open for hold_ms, then ABRUPT close.

    The hold + short release truncate the crushed reverb tail = the gated-reverb 'slam'. Mirrors the
    scripts/mix/keyed_gate.py envelope (5 ms key env, percentile threshold, one-pole release) but with a
    HOLD window and a FAST release so the tail is chopped rather than allowed to ring out.
    """
    env = uniform_filter1d(np.abs(dry_mono), size=max(1, int(0.005 * sr)))
    thr = float(np.percentile(env, 80) * (thresh_pct / 100.0))
    floor = 10 ** (floor_db / 20.0)
    hold = max(1, int(hold_ms / 1000.0 * sr))
    g = np.full(len(env), floor, dtype=np.float32)
    ctr = 0
    for i, opened in enumerate(env > thr):
        if opened:
            ctr = hold; g[i] = 1.0
        elif ctr > 0:
            ctr -= 1; g[i] = 1.0
    rg = float(np.exp(-1.0 / (max(release_ms, 0.1) / 1000.0 * sr)))   # fast = abrupt close
    sm = np.empty_like(g); p = floor
    for i, v in enumerate(g):
        p = v if v >= p else rg * p + (1.0 - rg) * v                  # instant attack, fast release
        sm[i] = p
    return sm


def main():
    ap = argparse.ArgumentParser(description="Phil Collins 'In the Air Tonight' gated-reverb drum-bus chain "
                                             "(synth reverb -> heavy comp -> abrupt gate -> blend -> wide).")
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--hpf", type=float, default=30.0, help="pre-chain HPF Hz (subsonic, zero-phase)")
    # reverb (deterministic synth IR) -----------------------------------------------------------
    ap.add_argument("--decay-s", type=float, default=1.6, help="reverb decay seconds (the room size; the gate truncates it)")
    ap.add_argument("--reverb-dark", type=float, default=9000.0, help="reverb IR low-pass Hz (lower = darker room)")
    ap.add_argument("--reverb-seed", type=int, default=1981, help="RNG seed for the IR (determinism; vary for a different room)")
    ap.add_argument("--predelay-ms", type=float, default=8.0, help="reverb pre-delay ms (separates the room from the dry hit)")
    # heavy ambience compression (compress-loop) ------------------------------------------------
    ap.add_argument("--rev-comp-thresh", type=float, default=-30.0, help="wet-reverb comp threshold dBFS (lower = more crush)")
    ap.add_argument("--rev-comp-ratio", type=float, default=8.0, help="wet-reverb comp ratio (high = the explosive crush)")
    ap.add_argument("--rev-comp-attack", type=float, default=1.0, help="wet-reverb comp attack ms (fast)")
    ap.add_argument("--rev-comp-release", type=float, default=200.0, help="wet-reverb comp release ms")
    ap.add_argument("--no-comp", action="store_true", help="skip the heavy ambience compression (A/B)")
    # the abrupt gate ---------------------------------------------------------------------------
    ap.add_argument("--gate-thresh-pct", type=float, default=50.0, help="gate threshold as %% of the dry env 80th-pctile (lower = opens easier)")
    ap.add_argument("--gate-hold-ms", type=float, default=320.0, help="how long the gate stays OPEN after a hit (the reverb window)")
    ap.add_argument("--gate-release-ms", type=float, default=28.0, help="gate close time ms (SHORT = the abrupt 80s slam)")
    ap.add_argument("--gate-floor-db", type=float, default=-60.0, help="gate floor dB between hits (how hard it shuts)")
    ap.add_argument("--no-gate", action="store_true", help="skip the gate -> ungated big reverb (A/B)")
    # blend + tone + width ----------------------------------------------------------------------
    ap.add_argument("--wet", type=float, default=0.7, help="gated-reverb blend vs dry (0..1+; RMS-matched to dry first)")
    ap.add_argument("--low-shelf", type=float, default=1.0, help="post low_shelf @100 gain dB (weight)")
    ap.add_argument("--crack", type=float, default=2.0, help="post bell @4k gain dB (the explosive snare CRACK)")
    ap.add_argument("--air", type=float, default=1.0, help="post high_shelf @10k gain dB (gentle 80s sheen)")
    ap.add_argument("--width", type=float, default=1.4, help="M/S width 0..1+ (>1 = WIDE; the HUGE image, opposite of TNK)")
    ap.add_argument("--mono-below", type=float, default=0.0, help="mono the bass below this Hz (0=off)")
    # optional real reverb VST (NOT the locked path) --------------------------------------------
    ap.add_argument("--reverb-vst", default="", help="path to a reverb VST3 to use instead of the synth IR (NOT the locked signature; verify it renders)")
    ap.add_argument("--reverb-vst-mix", type=float, default=100.0, help="wet%% to request on the VST reverb (best-effort)")
    a = ap.parse_args()

    # vst/tool imports deferred so --help works without the vst venv
    from stemmy.loops_mcp.tools.adjust_stereo import adjust_stereo
    from stemmy.loops_mcp.tools.apply_eq import EqBand, apply_eq
    from stemmy.loops_mcp.tools.compress_loop import compress_loop

    src, out = a.src, a.out
    _m("in", src)
    tmps = []

    # Stage A — subsonic HPF (zero-phase)
    e1 = src + ".iat1.wav"; tmps.append(e1)
    apply_eq(src, e1, bands=[EqBand(type="high_pass", freq_hz=a.hpf, gain_db=0, q=0.707)], phase="zero")

    dry, sr = sf.read(e1, dtype="float32", always_2d=True)
    dry = dry.T.copy()
    if dry.shape[0] == 1:
        dry = np.repeat(dry, 2, 0)
    dry_mono = dry.mean(0)

    # Stage B — the big room (deterministic synth IR by default; optional real VST)
    if a.reverb_vst:
        wet = _vst_wet(dry, sr, a.reverb_vst, a.reverb_vst_mix)
    else:
        wet = _synth_wet(dry_mono, sr, a.decay_s, a.reverb_dark, a.reverb_seed, a.predelay_ms)

    # Stage C — CRUSH the ambience (compress-loop, deterministic; auto-makeup brings it back up = explosive)
    if not a.no_comp:
        wp = src + ".iatwet.wav"; cp = src + ".iatcomp.wav"; tmps += [wp, cp]
        sf.write(wp, wet.T, sr, subtype="PCM_24")
        compress_loop(wp, cp, threshold_db=a.rev_comp_thresh, ratio=a.rev_comp_ratio,
                      attack_ms=a.rev_comp_attack, release_ms=a.rev_comp_release, knee_db=3.0, mix=1.0)
        cw, _ = sf.read(cp, dtype="float32", always_2d=True); wet = cw.T.copy()

    # Stage D — the abrupt gate (keyed off the dry kit), truncating the crushed tail
    if not a.no_gate:
        sm = _abrupt_gate(dry_mono, sr, a.gate_thresh_pct, a.gate_hold_ms, a.gate_release_ms, a.gate_floor_db)
        n = min(wet.shape[1], len(sm))
        wet = wet[:, :n] * sm[None, :n]

    # Stage E — blend the gated explosion under the dry (RMS-match the wet to dry first so --wet is meaningful)
    n = min(dry.shape[1], wet.shape[1])
    dry = dry[:, :n]; wet = wet[:, :n]
    d_rms = float(np.sqrt(np.mean(dry ** 2))) + 1e-9
    w_rms = float(np.sqrt(np.mean(wet ** 2))) + 1e-9
    y = dry + a.wet * (d_rms / w_rms) * wet
    e2 = src + ".iat2.wav"; tmps.append(e2)
    sf.write(e2, y.T, sr, subtype="PCM_24")

    # Stage F — present / crack polish (zero-phase)
    e3 = src + ".iat3.wav"; tmps.append(e3)
    apply_eq(e2, e3, bands=[
        EqBand(type="low_shelf", freq_hz=100, gain_db=a.low_shelf, q=0.7),
        EqBand(type="bell", freq_hz=4000, gain_db=a.crack, q=1.0),
        EqBand(type="high_shelf", freq_hz=10000, gain_db=a.air, q=0.7)], phase="zero")

    # Stage G — WIDE (the HUGE 80s image)
    cur = e3
    e4 = None
    if abs(a.width - 1.0) > 1e-6 or a.mono_below > 0:
        e4 = src + ".iat4.wav"; tmps.append(e4)
        adjust_stereo(e3, e4, width=a.width, mono_below_hz=a.mono_below)
        cur = e4

    z, sr = sf.read(cur, dtype="float32", always_2d=True)
    zz = peak_normalize(z.T, OUT_PEAK_DBFS)   # shared core; same -1 dBFS invariant
    sf.write(out, zz.T, sr, subtype="PCM_24")
    for f in tmps:
        try:
            os.remove(f)
        except OSError:
            pass
    _m("FINAL", out)
    print(f"in-the-air-tonight bus -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
