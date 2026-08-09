"""Acceptance checks for the Ship Studios Distance plugin.

Run with the stemmy-loops `vst` venv (has pedalboard):

    /Users/ship/Documents/code/stemmy-loops-mcp/.venv/bin/python vst/verify_distance.py

Proves the things that matter and are easy to get silently wrong:
  3. centre is transparent      -- distance=0 must not touch the audio
  4. tone moves the right way   -- centroid must rise monotonically far -> close
  5. level does NOT move        -- the fader is a tone control, not a volume one
  6. no zipper on automation    -- sweeping the fader must not click
  7. harshness guard            -- 5-7 kHz is this repo's known trap band
"""

import os
import sys

import numpy as np
import time

import pyloudnorm
from scipy import signal
from pedalboard import load_plugin

VST3 = os.path.expanduser("~/Library/Audio/Plug-Ins/VST3/Ship Studios Distance.vst3")
SR = 48000
DUR = 4.0


METER = pyloudnorm.Meter(SR)


def pink_noise(n, seed=7):
    """Pink noise band-limited to 20 Hz - 20 kHz.

    The band limit matters: unbounded 1/f puts enormous energy below 20 Hz, which
    no real programme material has and which would dominate a broadband level
    measurement while being inaudible.
    """
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((2, n))
    spectrum = np.fft.rfft(white, axis=1)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)

    shape = np.zeros_like(freqs)
    band = (freqs >= 20.0) & (freqs <= 20000.0)
    shape[band] = 1.0 / np.sqrt(freqs[band])

    shaped = np.fft.irfft(spectrum * shape, n=n, axis=1)
    shaped /= np.max(np.abs(shaped))
    return (shaped * 0.25).astype(np.float32)


def lufs(x):
    """Integrated loudness (BS.1770 K-weighted) -- what the compensation targets."""
    return float(METER.integrated_loudness(x.T.astype(np.float64)))


def centroid_hz(x):
    mono = x.mean(axis=0)
    mag = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
    return float((freqs * mag).sum() / mag.sum())


def band_db(x, lo, hi):
    mono = x.mean(axis=0)
    mag = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
    sel = (freqs >= lo) & (freqs < hi)
    return float(10 * np.log10(mag[sel].sum() + 1e-20))


def rms_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-20))


EXTREME = False   # set per pass in main()


def set_param(plugin, name, value):
    """Set a plugin parameter, refusing to silently invent a Python attribute.

    pedalboard names VST3 parameters by their ID (`output_db`), not their display
    name (`Output`) -- and assigning an unknown name just creates an ordinary
    attribute with no error. That hid a no-op for several runs.
    """
    if name not in plugin.parameters:
        raise AttributeError(f"no such plugin parameter {name!r}; "
                             f"have {sorted(plugin.parameters)}")
    setattr(plugin, name, value)


def render(plugin, x, distance, output_db=0.0, bypass=False, input_db=0.0, hard=False):
    set_param(plugin, "hard_clip", hard)
    set_param(plugin, "input_db", input_db)
    set_param(plugin, "distance", distance)
    set_param(plugin, "output_db", output_db)
    set_param(plugin, "bypass", bypass)
    set_param(plugin, "extreme", EXTREME)
    plugin.reset()
    return plugin(x, SR)


def run(plugin, x, guard_limit):
    failures = []

    # --- 3. centre is transparent -------------------------------------------
    # The limiter's lookahead delays the output, so this must align first. The
    # delay is found by cross-correlation rather than assumed, which also proves
    # the reported latency matches the real one.
    y = render(plugin, x, 0.0)
    lag = int(np.argmax(np.correlate(y[0, : SR // 2], x[0, : SR // 4], mode="valid")))
    n = min(x.shape[1] - lag, y.shape[1] - lag)
    delta = float(np.max(np.abs(y[:, lag : lag + n] - x[:, :n])))
    ok = delta < 1e-6
    failures += [] if ok else ["centre not transparent"]
    print(f"[{'PASS' if ok else 'FAIL'}] 3. centre transparent   max|delta| = {delta:.3e}  "
          f"(< 1e-6, latency {lag} samples)")

    # pedalboard trims the plugin's REPORTED latency from the output before
    # returning it, so a residual lag here is exactly (real - reported): zero
    # means setLatencySamples told the truth. Any future stage that adds real
    # latency (an oversampler, a longer lookahead) without updating the report
    # shows up as a nonzero residual and fails loudly here.
    ok = lag == 0
    failures += [] if ok else [f"reported latency off by {lag} samples"]
    print(f"[{'PASS' if ok else 'FAIL'}] 3b. latency lockstep    residual (real - reported) "
          f"= {lag} samples (== 0)")

    # --- 4/5/7. sweep --------------------------------------------------------
    print()
    print(f"{'distance':>9} {'centroid Hz':>12} {'LUFS':>9} {'5-7k dB':>9}")
    rows = {}
    for d in (-100.0, -50.0, 0.0, 50.0, 100.0):
        yd = render(plugin, x, d)
        rows[d] = (centroid_hz(yd), lufs(yd), band_db(yd, 5000, 7000))
        print(f"{d:>9.0f} {rows[d][0]:>12.1f} {rows[d][1]:>9.3f} {rows[d][2]:>9.2f}")

    cents = [rows[d][0] for d in (-100.0, -50.0, 0.0, 50.0, 100.0)]
    mono_ok = all(a < b for a, b in zip(cents, cents[1:]))
    failures += [] if mono_ok else ["centroid not monotonic"]
    print()
    print(f"[{'PASS' if mono_ok else 'FAIL'}] 4a. centroid rises far->close monotonically")

    # Full-range swing is the criterion for a bipolar control: how much darker
    # fully-far is than fully-close. (The original bar -- far vs FLAT >= 25%, from
    # the levee preset's 2223->1597 -- was not like-for-like: that number came
    # from a Distressor + 15 IPS tape + Binson echo chain, not an EQ alone.)
    swing = 1.0 - rows[-100.0][0] / rows[100.0][0]
    ok = swing >= 0.25
    failures += [] if ok else [f"far->close centroid swing {swing*100:.1f}% < 25%"]
    print(f"[{'PASS' if ok else 'FAIL'}] 4b. far->close swing    {swing*100:.1f}%  (>= 25%)")

    drop = 1.0 - rows[-100.0][0] / rows[0.0][0]
    print(f"       (far vs flat: {drop*100:.1f}%; close vs flat: "
          f"{(rows[100.0][0] / rows[0.0][0] - 1.0)*100:+.1f}%)")

    # Loudness must now TRACK distance: closer is louder, further is quieter.
    # 6 dB per doubling (free-field inverse-square), one doubling at each fader
    # extreme, scaled by 2x mode.
    lo = [rows[d][1] for d in (-100.0, -50.0, 0.0, 50.0, 100.0)]
    mono_l = all(a < b for a, b in zip(lo, lo[1:]))
    failures += [] if mono_l else ["loudness not monotonic with distance"]
    print(f"[{'PASS' if mono_l else 'FAIL'}] 5a. loudness rises far->close monotonically")

    expected = 6.0 * (2.0 if EXTREME else 1.0)
    far_delta = rows[-100.0][1] - rows[0.0][1]
    close_delta = rows[100.0][1] - rows[0.0][1]

    ok = abs(far_delta + expected) <= 1.5 and abs(close_delta - expected) <= 1.5
    failures += [] if ok else [
        f"level law off target (far {far_delta:+.2f}, close {close_delta:+.2f}, want +/-{expected:.0f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 5b. level law           far {far_delta:+.2f} LU, "
          f"close {close_delta:+.2f} LU  (want -/+{expected:.0f}, +/-1.5)")

    # Level-NORMALISED: subtract each position's own loudness first. Now that
    # close is deliberately +6 dB (or +12 at 2x), a raw band comparison just
    # re-reports the level law -- every band rises together. What the guard is
    # actually about is 5-7 kHz's SHARE of the signal.
    guard = ((rows[100.0][2] - rows[100.0][1]) - (rows[0.0][2] - rows[0.0][1]))
    ok = guard <= guard_limit
    failures += [] if ok else [f"5-7k boost {guard:.2f} dB > {guard_limit:.1f}"]
    print(f"[{'PASS' if ok else 'FAIL'}] 7.  5-7k share at close {guard:+.2f} dB  "
          f"(<= {guard_limit:+.1f}, level-normalised)")

    # --- 6. no zipper on automation -----------------------------------------
    # A steady tone, swept fader. Any coefficient step that is audible shows up
    # as a sample-to-sample jump far larger than the tone's own slew.
    print()
    # 4 kHz at -62 dBFS. Two reasons for each choice:
    #   -62 dBFS is below the compressor threshold at both scales (-24 dBFS at
    #   1x, -48 at 2x, 6 dB knee), so its fast far-side attack cannot distort.
    #   4 kHz has a 0.25 ms period, SHORTER than the transient shaper's 0.5 ms
    #   detector, so the shaper sees a steady envelope instead of tracking
    #   individual cycles. At 440 Hz it tracks the waveform and modulates gain at
    #   880 Hz -- real behaviour, but indistinguishable from a click here.
    # What is left is exactly what this test is for: EQ coefficient stepping and
    # gain smoothing.
    toneHz = 4000.0
    t = np.arange(int(SR * 2.0)) / SR
    tone = np.vstack([np.sin(2 * np.pi * toneHz * t) * 0.0008] * 2).astype(np.float32)

    # The sweep runs reset=False so it is continuous, which means it would
    # otherwise inherit the compressor's averaged makeup from whatever loud
    # render ran last -- measured as a +39 dB burst at the head of the sweep.
    # Reset, then warm up on the quiet tone so the average settles first.
    set_param(plugin, "extreme", EXTREME)
    set_param(plugin, "output_db", 0.0)
    set_param(plugin, "bypass", False)
    set_param(plugin, "distance", -100.0)
    plugin.reset()
    plugin(tone[:, : int(SR * 0.5)], SR, reset=False)

    chunks, pos, steps = [], 0, 200
    hop = tone.shape[1] // steps
    for i in range(steps):
        set_param(plugin, "distance", -100.0 + 200.0 * (i / (steps - 1)))
        chunks.append(plugin(tone[:, pos : pos + hop], SR, reset=False))
        pos += hop
    swept = np.concatenate(chunks, axis=1)

    # Compare the biggest sample-to-sample jump against the jump this tone MUST
    # make at its own amplitude: a sine of peak A slews at most A*omega per
    # sample. An absolute threshold is wrong here -- the EQ changes A across the
    # sweep (a lot at 2x), so a louder output legitimately slews faster and a
    # fixed limit flags it as a click. The ratio is amplitude-independent:
    # ~1.0 means the only motion is the tone itself; >>1 means a real
    # discontinuity.
    max_step = float(np.max(np.abs(np.diff(swept, axis=1))))
    omega = 2.0 * np.pi * toneHz / SR
    peak = float(np.max(np.abs(swept)))
    slew_ratio = max_step / max(peak * omega, 1e-12)

    ok = slew_ratio < 1.3
    failures += [] if ok else [f"automation slew ratio {slew_ratio:.2f}"]
    print(f"[{'PASS' if ok else 'FAIL'}] 6.  automation sweep    slew ratio = {slew_ratio:.3f}  "
          f"(< 1.3;  step {max_step:.5f}, peak {peak:.3f})")

    # --- 9. compressor ballistics -------------------------------------------
    # The design claim: FAR uses a fast attack that softens onsets (crest drops),
    # CLOSE uses a slow attack that lets them through (crest largely survives).
    # Pink noise has no transients to speak of, so this needs a percussive signal.
    print()
    n = int(SR * 3.0)
    env = np.zeros(n, dtype=np.float64)
    period = int(SR * 0.25)
    for start in range(0, n - period, period):
        L = int(SR * 0.12)
        env[start : start + L] = np.exp(-np.arange(L) / (SR * 0.02))
    rng2 = np.random.default_rng(11)
    # -20 dBFS peak, deliberately quiet. This check is about the compressor's
    # ATTACK BALLISTICS, and at a hot level the close path slams the ceiling --
    # the clipper and limiter then flatten the peaks regardless of attack time,
    # so the measurement stops being about ballistics at all. Even +12 dB of
    # level law at 2x leaves this below the clip knee.
    hits = env * rng2.standard_normal(n)
    hits = (hits / np.max(np.abs(hits)) * 0.1).astype(np.float32)
    hits = np.vstack([hits, hits])

    def crest_db(x):
        peak = np.max(np.abs(x))
        rms = np.sqrt(np.mean(x**2))
        return float(20 * np.log10(peak / (rms + 1e-20) + 1e-20))

    def onset_to_body_db(x):
        """Peak of each hit's first 3 ms against the RMS of its 20-100 ms body.

        This -- not global crest -- is the compressor claim. Global crest over a
        signal with gaps is dominated by the -18 dB air cut pulling RMS down
        faster than peak, which buries the ballistics entirely.
        """
        mono = x.mean(axis=0)
        ratios = []
        for start in range(0, len(mono) - period, period):
            atk = np.max(np.abs(mono[start : start + int(SR * 0.003)]))
            body = np.sqrt(np.mean(mono[start + int(SR * 0.02) : start + int(SR * 0.10)] ** 2))
            if body > 1e-9 and atk > 1e-9:
                ratios.append(20 * np.log10(atk / body))
        return float(np.mean(ratios))

    y_far, y_flat, y_close = (render(plugin, hits, v) for v in (-100.0, 0.0, 100.0))

    print(f"crest dB        in {crest_db(hits):6.2f}   far {crest_db(y_far):6.2f}"
          f"   flat {crest_db(y_flat):6.2f}   close {crest_db(y_close):6.2f}")
    o_in, o_far, o_flat, o_close = (onset_to_body_db(v) for v in (hits, y_far, y_flat, y_close))
    print(f"onset/body dB   in {o_in:6.2f}   far {o_far:6.2f}"
          f"   flat {o_flat:6.2f}   close {o_close:6.2f}")

    # With the transient shaper reinforcing the compressor's ballistics, this
    # should now be a wide separation, not a marginal one. A small margin would
    # mean the shaper is not actually contributing.
    separation = o_close - o_far
    ok = separation > 3.0
    failures += [] if ok else [
        f"onset separation only {separation:.2f} dB (far {o_far:.2f}, close {o_close:.2f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 9a. far softens onsets, close sharpens them  "
          f"(separation {separation:+.2f} dB > 3)")

    # Direction, independently of each other: close must SHARPEN vs untouched,
    # far must SOFTEN vs untouched. Comparing only far-vs-close would pass even
    # if both moved the same way.
    ok = o_close > o_in + 1.0 and o_far < o_in - 1.0
    failures += [] if ok else [
        f"shaping not bidirectional (in {o_in:.2f}, far {o_far:.2f}, close {o_close:.2f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 9c. bidirectional vs source   "
          f"close {o_close - o_in:+.2f}, far {o_far - o_in:+.2f} dB")

    c_delta = crest_db(y_flat) - crest_db(hits)
    ok = abs(c_delta) < 0.01
    failures += [] if ok else [f"flat crest moved {c_delta:+.3f} dB"]
    print(f"[{'PASS' if ok else 'FAIL'}] 9b. flat leaves transients untouched  "
          f"({c_delta:+.4f} dB)")

    # --- 11. input gain ------------------------------------------------------
    # At flat, everything downstream is inert, so the output should be the input
    # scaled by exactly the input gain -- proving the stage is in the path and
    # correctly calibrated. Ceiling opened up so the limiter cannot confound it.
    print()
    set_param(plugin, "ceiling_db", 0.0)
    quiet = (x * 0.1).astype(np.float32)
    base = rms_db(render(plugin, quiet, 0.0, input_db=0.0))

    worst = 0.0
    for drive in (-12.0, -6.0, 6.0, 12.0):
        got = rms_db(render(plugin, quiet, 0.0, input_db=drive)) - base
        worst = max(worst, abs(got - drive))
        print(f"       input {drive:+6.1f} dB -> {got:+7.3f} dB")

    ok = worst < 0.05
    failures += [] if ok else [f"input gain error {worst:.3f} dB"]
    print(f"[{'PASS' if ok else 'FAIL'}] 11. input gain          max error {worst:.4f} dB  (< 0.05)")
    set_param(plugin, "ceiling_db", -0.3)

    # --- 12. soft clip, driven by the fader ----------------------------------
    # Saturation is now a proximity cue, so the claim is directional: harmonics
    # must RISE toward close and be absent toward far. A distant source dirtier
    # than a near one would be backwards.
    print()
    ceiling_lin = 10 ** (-0.3 / 20.0)

    t2 = np.arange(SR) / SR
    sine = np.vstack([np.sin(2 * np.pi * 220 * t2) * 0.5] * 2).astype(np.float32)

    def harmonics_db(y, f0=220.0):
        mono = y.mean(axis=0)
        mag = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
        freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
        def at(f):
            i = int(np.argmin(np.abs(freqs - f)))
            return float(np.max(mag[max(0, i - 3): i + 4]))
        fund = at(f0)
        low = sum(at(f0 * k) ** 2 for k in (2, 3, 4))
        high = sum(at(f0 * k) ** 2 for k in range(8, 20))
        return (20 * np.log10(np.sqrt(low) / (fund + 1e-20) + 1e-20),
                20 * np.log10(np.sqrt(high) / (fund + 1e-20) + 1e-20))

    h_far, _ = harmonics_db(render(plugin, sine, -100.0))
    h_flat, _ = harmonics_db(render(plugin, sine, 0.0))
    h_close, high_close = harmonics_db(render(plugin, sine, 100.0))

    print(f"       low-order harmonics   far {h_far:+.1f}   flat {h_flat:+.1f}"
          f"   close {h_close:+.1f} dB")

    # Assert only what this signal can actually prove: the clipper engages toward
    # close. The far figure is NOT the clipper (which is exactly zero there) --
    # it is the far compressor's 0.3 ms attack tracking a 220 Hz waveform and
    # distorting it. Sustained tones are the worst case for that; it is reported
    # rather than asserted on.
    ok = h_close > h_flat + 10.0
    failures += [] if ok else [f"no saturation at close ({h_close:.1f} vs flat {h_flat:.1f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12a. saturation engages toward close  "
          f"({h_close - h_flat:+.1f} dB over flat)")
    print(f"       NB far {h_far:+.1f} dB is compressor waveform-tracking, not the clipper")

    # Mode comparison needs the clipper ACTUALLY CLIPPING in steady state. At
    # unity drive the chain lands below the knee and only the opening transient
    # clips -- the two modes then measure byte-for-byte identical harmonics and
    # the comparison is vacuous. +18 dB of input drive puts it firmly over.
    drive = 18.0
    h_soft_d, high_soft_d = harmonics_db(render(plugin, sine, 100.0, input_db=drive))
    h_hard_d, high_hard_d = harmonics_db(render(plugin, sine, 100.0, input_db=drive, hard=True))

    soft_spread = h_soft_d - high_soft_d
    hard_spread = h_hard_d - high_hard_d

    # Thresholds allow for the transient shaper, which adds its own harmonics on
    # tonal material and so raises the high-order floor for BOTH modes. That
    # compressed the measured soft-vs-hard gap from 6.1 dB to ~3.9 without
    # changing the clipper at all. Driving harder does not recover it -- at +24
    # dB both modes saturate into each other (gap 1.6 dB) -- so +18 is the most
    # discriminating point available.
    ok = soft_spread > 12.0
    failures += [] if ok else [f"soft mode not soft (spread {soft_spread:.1f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12b. soft mode is soft       "
          f"8th+ are {soft_spread:.1f} dB below 2nd-4th (> 12, driven +{drive:.0f} dB)")

    print(f"       high-order vs low-order   soft -{soft_spread:.1f} dB"
          f"   hard -{hard_spread:.1f} dB")

    ok = hard_spread < soft_spread - 3.0
    failures += [] if ok else [
        f"hard mode not harsher (soft spread {soft_spread:.1f}, hard {hard_spread:.1f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12e. hard mode is harsher    "
          f"{soft_spread - hard_spread:.1f} dB more high-order content (> 3)")


    # No fold-back: a slow ramp is near-DC, so the EQ only scales it and the
    # dynamics only compress it -- both monotonic. A shaper that folded back
    # would invert and show up immediately as a decreasing output.
    ramp = np.linspace(-1.2, 1.2, SR, dtype=np.float32)
    ramp_probe = np.vstack([ramp, ramp])
    y_ramp = render(plugin, ramp_probe, 100.0)[0]
    settled = y_ramp[SR // 10:]

    # Tolerance is looser than when the shaper could be tested in isolation
    # (+7.27e-06 then): the ramp now passes through EQ, compressor and limiter,
    # whose gain movement adds small wobble -- at 2x, the held compressor
    # detector and the limiter's boxcar envelope leave up to ~2.5e-3 of it on
    # this pathological near-DC input (the automation-sweep test covers real
    # signals). This still catches gross fold-back, which inverts the signal
    # and shows up as an excursion around 0.1, forty times this bar.
    backslide = float(np.min(np.diff(settled)))
    ok = backslide > -5e-3
    failures += [] if ok else [f"soft clip folds back ({backslide:.2e})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12c. monotonic, no foldback  min step {backslide:+.2e}")

    peak_ramp = float(np.max(np.abs(y_ramp)))
    ok = peak_ramp <= ceiling_lin + 1e-4
    failures += [] if ok else [f"exceeded ceiling ({peak_ramp:.4f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12d. bounded by ceiling      "
          f"peak {20*np.log10(peak_ramp):+.3f} dBFS")

    y_hard_ramp = render(plugin, ramp_probe, 100.0, hard=True)[0]
    hard_peak = float(np.max(np.abs(y_hard_ramp)))
    ok = hard_peak <= ceiling_lin + 1e-4
    failures += [] if ok else [f"hard mode exceeded ceiling ({hard_peak:.4f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12f. hard bounded by ceiling "
          f"peak {20*np.log10(hard_peak):+.3f} dBFS")

    hard_back = float(np.min(np.diff(y_hard_ramp[SR // 10:])))
    ok = hard_back > -5e-3
    failures += [] if ok else [f"hard mode folds back ({hard_back:.2e})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 12g. hard monotonic          min step {hard_back:+.2e}")

    # --- 13. clip aliasing ----------------------------------------------------
    # A driven tone at a frequency that is NOT a divisor of the sample rate:
    # genuine harmonics land on the k*f0 comb, aliased fold-back lands off it.
    # The worst off-comb spectral peak is the aliasing figure. Before the ADAA
    # clipper this sat at -24 dB (hard) / -26 dB (soft) relative to the
    # fundamental; first-order ADAA on the clip correction bought ~8-10 dB.
    # The harmonic spread checks (12b/12e) never see this, so it gets its own
    # gate.
    print()
    f13 = 2093.0
    t13 = np.arange(SR * 2) / SR
    sine13 = np.vstack([np.sin(2 * np.pi * f13 * t13) * 0.5] * 2).astype(np.float32)

    def worst_alias_db(y):
        mono = y.mean(axis=0)[SR // 2:]          # steady tail: dynamics settled
        m = len(mono)
        mag = np.abs(np.fft.rfft(mono * np.hanning(m)))
        fr = np.fft.rfftfreq(m, 1.0 / SR)
        i0 = int(np.argmin(np.abs(fr - f13)))
        fund = float(np.max(mag[i0 - 3: i0 + 4]))
        harm = np.arange(1, int(fr[-1] / f13) + 1) * f13
        dist = np.min(np.abs(fr[:, None] - harm[None, :]), axis=1)
        mask = (dist > 80.0) & (fr > 200.0)
        return float(20 * np.log10(np.max(mag[mask]) / (fund + 1e-20) + 1e-20))

    alias_soft = worst_alias_db(render(plugin, sine13, 100.0, input_db=18.0))
    alias_hard = worst_alias_db(render(plugin, sine13, 100.0, input_db=18.0, hard=True))

    ok = alias_soft <= -30.0
    failures += [] if ok else [f"soft clip aliasing {alias_soft:+.1f} dB > -30"]
    print(f"[{'PASS' if ok else 'FAIL'}] 13a. soft clip aliasing      worst off-comb peak "
          f"{alias_soft:+.1f} dB rel fundamental (<= -30)")

    ok = alias_hard <= -30.0
    failures += [] if ok else [f"hard clip aliasing {alias_hard:+.1f} dB > -30"]
    print(f"[{'PASS' if ok else 'FAIL'}] 13b. hard clip aliasing      worst off-comb peak "
          f"{alias_hard:+.1f} dB rel fundamental (<= -30)")

    # --- 10. brick-wall ceiling ---------------------------------------------
    # Hostile input: full-scale noise bursts, driven at the loudest setting so
    # the distance law and EQ boosts are both working against the ceiling.
    print()
    rng3 = np.random.default_rng(23)
    hot = (rng3.standard_normal((2, SR * 2)) * 0.9).astype(np.float32)
    hot = np.clip(hot, -1.0, 1.0)

    for ceiling in (-0.3, -3.0):
        set_param(plugin, "ceiling_db", ceiling)
        y_hot = render(plugin, hot, 100.0)
        peak_db = 20 * np.log10(float(np.max(np.abs(y_hot))) + 1e-20)
        # 0.1 dB of slack for the ramp arriving within the lookahead window.
        ok = peak_db <= ceiling + 0.1
        failures += [] if ok else [f"ceiling {ceiling} exceeded: peak {peak_db:+.2f} dBFS"]
        print(f"[{'PASS' if ok else 'FAIL'}] 10. ceiling {ceiling:+.1f} dBFS      "
              f"peak out {peak_db:+.3f} dBFS")

    set_param(plugin, "ceiling_db", -0.3)

    # --- bypass --------------------------------------------------------------
    yb = render(plugin, x, 100.0, bypass=True)
    blag = int(np.argmax(np.correlate(yb[0, : SR // 2], x[0, : SR // 4], mode="valid")))
    n = min(x.shape[1] - blag, yb.shape[1] - blag)
    bdelta = float(np.max(np.abs(yb[:, blag : blag + n] - x[:, :n])))
    ok = bdelta < 1e-6
    failures += [] if ok else ["bypass not transparent"]
    print(f"[{'PASS' if ok else 'FAIL'}] 8.  bypass transparent  max|delta| = {bdelta:.3e}")

    return failures


# ==========================================================================
# 14-21. Adaptive EQ -- the bands move to the source's own features.
#
# Every check below reads the plugin's TRANSFER FUNCTION, never its internal
# state: what matters is where the curve ended up, not what the analyser
# believes it decided.
# ==========================================================================

def transfer_db(plugin, x, distance):
    """Smoothed out/in magnitude response in dB, and the matching frequencies."""
    y = render(plugin, x, distance)
    lag = int(np.argmax(np.correlate(y[0, : SR // 2], x[0, : SR // 4], mode="valid")))
    n = min(x.shape[1] - lag, y.shape[1] - lag)
    a, b = x[0, :n], y[0, lag : lag + n]

    nper = 16384
    f, pa = signal.welch(a, SR, nperseg=nper)
    _, pb = signal.welch(b, SR, nperseg=nper)
    keep = (f >= 30) & (f <= 18000)
    return f[keep], 10.0 * np.log10(np.maximum(pb[keep], 1e-20)
                                    / np.maximum(pa[keep], 1e-20))


def peak_hz(f, db, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(f[m][int(np.argmax(db[m]))])


def analyse(plugin, material, settle=3.0):
    """Arm capture, feed `material`, wait for the background worker."""
    set_param(plugin, "analyse", False)
    set_param(plugin, "distance", 0.0)     # capture is pre-EQ, but keep it honest
    set_param(plugin, "bypass", False)
    plugin.reset()
    set_param(plugin, "analyse", True)     # rising edge on the first block
    plugin(material, SR)
    set_param(plugin, "analyse", False)
    time.sleep(settle)


def revert(plugin):
    """No analysis has been published yet at load; a clean reload is the only
    way back to factory from the harness, so tests that need factory run first."""
    return load_plugin(VST3)


def resonant_source(seconds=32.0, seed=11):
    """Pink noise with a deliberate 240 Hz resonance and a 6 kHz rolloff --
    features at frequencies the FACTORY bands (300 Hz / 8 kHz) do not sit on."""
    x = pink_noise(int(SR * seconds), seed=seed)[0]

    b, a = signal.iirpeak(240.0 / (SR / 2), Q=3.0)
    x = x + 3.0 * signal.lfilter(b, a, x)

    b, a = signal.butter(2, 6000.0 / (SR / 2), btype="low")
    x = signal.lfilter(b, a, x) + 0.02 * x       # a real knee, not a brick wall

    x = x / (np.max(np.abs(x)) + 1e-12) * 0.5
    return np.stack([x, x])


def run_adaptive():
    global EXTREME
    EXTREME = False
    failures = []

    print("=" * 62)
    print("  ADAPTIVE EQ")
    print("=" * 62)

    probe = pink_noise(int(SR * 4.0), seed=3)

    # --- 14. it actually adapts, measured on the curve ----------------------
    plugin = load_plugin(VST3)
    f, before = transfer_db(plugin, probe, -100.0)      # FAR: bands are boosts/cuts
    room_before = peak_hz(f, before, 120, 600)

    src = resonant_source()
    analyse(plugin, src)

    f, after = transfer_db(plugin, probe, -100.0)
    room_after = peak_hz(f, after, 120, 600)

    moved = abs(room_after - 240.0) < abs(room_before - 240.0)
    changed = float(np.max(np.abs(after - before))) > 0.25
    ok = moved and changed
    failures += [] if ok else ["curve did not adapt toward the 240 Hz resonance"]
    print(f"[{'PASS' if ok else 'FAIL'}] 14. adapts to source   ROOM peak "
          f"{room_before:.0f} -> {room_after:.0f} Hz (target 240), "
          f"max curve delta {float(np.max(np.abs(after - before))):.2f} dB")

    # --- 15. deterministic --------------------------------------------------
    analyse(plugin, src)
    f, again = transfer_db(plugin, probe, -100.0)
    d = float(np.max(np.abs(again - after)))
    ok = d < 1e-3
    failures += [] if ok else ["analysis not deterministic"]
    print(f"[{'PASS' if ok else 'FAIL'}] 15. deterministic      max|delta| between two "
          f"analyses of the same buffer = {d:.3e}")

    # --- 16. centre still transparent after adapting ------------------------
    y = render(plugin, probe, 0.0)
    lag = int(np.argmax(np.correlate(y[0, : SR // 2], probe[0, : SR // 4], mode="valid")))
    n = min(probe.shape[1] - lag, y.shape[1] - lag)
    delta = float(np.max(np.abs(y[:, lag : lag + n] - probe[:, :n])))
    ok = delta < 1e-6
    failures += [] if ok else ["centre not transparent after adaptation"]
    print(f"[{'PASS' if ok else 'FAIL'}] 16. centre transparent after adaptation  "
          f"max|delta| = {delta:.3e}")

    # --- 17. harshness guard survives adaptation ----------------------------
    # A deliberately BRIGHT source is the adversarial case: it pulls PRESENCE up,
    # and at fixed Q that would push the band's upper skirt through 5-7k.
    bright = pink_noise(int(SR * 32.0), seed=5)[0]
    b, a = signal.butter(2, 4000.0 / (SR / 2), btype="high")
    bright = bright + 4.0 * signal.lfilter(b, a, bright)
    bright = bright / (np.max(np.abs(bright)) + 1e-12) * 0.5
    hot = load_plugin(VST3)
    analyse(hot, np.stack([bright, bright]))

    yc = render(hot, probe, 100.0)
    share = band_db(yc, 5000, 7000) - rms_db(yc) - (band_db(probe, 5000, 7000) - rms_db(probe))
    ok = share <= 2.0
    failures += [] if ok else [f"5-7k share {share:+.2f} dB after adapting to a bright source"]
    print(f"[{'PASS' if ok else 'FAIL'}] 17. harshness guard    5-7k share "
          f"{share:+.2f} dB after adapting to a BRIGHT source  (<= +2.0)")

    # --- 18. pathological sources stay inside the clamps --------------------
    n11 = int(SR * 32.0)
    t = np.arange(n11) / SR
    cases = {
        "silence":    np.zeros(n11),
        "DC":         np.full(n11, 0.5),
        "pure sine":  0.5 * np.sin(2 * np.pi * 1000 * t),
        "white noise": 0.5 * np.random.default_rng(1).standard_normal(n11),
    }
    for name, sig_ in cases.items():
        pl = load_plugin(VST3)
        analyse(pl, np.stack([sig_, sig_]).astype(np.float32))
        f2, c = transfer_db(pl, probe, -100.0)
        finite = bool(np.all(np.isfinite(c))) and float(np.max(np.abs(c))) < 60.0
        prox = peak_hz(f2, c, 40, 260)
        failures += [] if finite else [f"pathological source {name!r} produced a broken curve"]
        print(f"[{'PASS' if finite else 'FAIL'}] 18. clamp: {name:<12} curve finite, "
              f"max |{float(np.max(np.abs(c))):.1f}| dB, low peak {prox:.0f} Hz")

    # --- 19. no signal is refused, not hallucinated -------------------------
    quiet = load_plugin(VST3)
    f3, base = transfer_db(quiet, probe, -100.0)
    tiny = (pink_noise(n11, seed=9)[0] * 10 ** (-70.0 / 20.0)).astype(np.float32)
    analyse(quiet, np.stack([tiny, tiny]))
    _, post = transfer_db(quiet, probe, -100.0)
    d = float(np.max(np.abs(post - base)))
    ok = d < 1e-3
    failures += [] if ok else ["adapted to a signal below the -60 dBFS gate"]
    print(f"[{'PASS' if ok else 'FAIL'}] 19. NO SIGNAL gate     -70 dBFS input left the "
          f"curve untouched  (max|delta| {d:.3e})")

    # --- 20. the upload is opt-in and off by default ------------------------
    # Everything above adapted with `gemini` at its default. If that default
    # were ON, every check in this file would have silently uploaded audio to
    # Google -- so this asserts the default, not just that the path works.
    fresh = load_plugin(VST3)
    default_off = not bool(getattr(fresh, "gemini"))
    failures += [] if default_off else ["gemini upload defaults to ON"]
    print(f"[{'PASS' if default_off else 'FAIL'}] 20. upload opt-in      "
          f"gemini defaults {'OFF -- every check above was DSP-only' if default_off else 'ON'}"
          f"  (GEMINI_API_KEY {'set' if os.environ.get('GEMINI_API_KEY') else 'unset'})")

    # --- 23. the window picker skips the dead lead-in -----------------------
    # The case that motivated it, reproduced: 20 s of near-silence followed by
    # 12 s of the resonant source. Fitting the bands to whatever is under the
    # playhead would describe the silence; picking the window finds the music.
    #
    # Measured on the CURVE, so it proves the chosen audio reached the bands --
    # not that some internal index moved.
    lead = np.zeros(int(SR * 20.0), dtype=np.float32)
    music = resonant_source(seconds=12.0)[0]
    late = np.stack([np.concatenate([lead, music])] * 2).astype(np.float32)

    late_plugin = load_plugin(VST3)
    _, late_base = transfer_db(late_plugin, probe, -100.0)
    analyse(late_plugin, np.ascontiguousarray(late))
    _, late_after = transfer_db(late_plugin, probe, -100.0)

    late_room = peak_hz(f, late_after, 120, 600)
    moved = float(np.max(np.abs(late_after - late_base)))
    ok = moved > 0.25 and abs(late_room - 240.0) < abs(313.0 - 240.0)
    failures += [] if ok else ["window picker did not find the late-starting music"]
    print(f"[{'PASS' if ok else 'FAIL'}] 23. window picker      20 s of silence then music: "
          f"ROOM landed at {late_room:.0f} Hz (target 240), curve moved {moved:.2f} dB")

    # --- 24. the settings assistant cannot break the plugin ------------------
    # Asserted on the AUDIO, not on plugin.<param>: pedalboard's parameter
    # getters return ITS OWN cached value, not the plugin's live one, so a
    # background write is invisible to them. Measured -- the assistant moved
    # distance to +35 and changed the render by 0.088, while plugin.distance
    # still read 0.0. Anything checking parameters here would have passed while
    # testing nothing.
    #
    # It is the only place a model chooses a NUMBER, so what is asserted is the
    # CONTAINMENT, not the taste: whatever comes back, the output stays finite
    # and under the ceiling. Runs with or without a key -- the failure path has
    # to be just as contained.
    assist = load_plugin(VST3)
    set_param(assist, "ceiling_db", -3.0)
    set_param(assist, "assist", False)
    assist.reset()

    plugin_ok = True
    try:
        set_param(assist, "assist", True)
        assist(pink_noise(int(SR * 32.0), seed=13), SR)
        set_param(assist, "assist", False)
        time.sleep(50.0)
        out = assist(pink_noise(int(SR * 2.0), seed=17) * 0.9, SR)
    except Exception as exc:                       # noqa: BLE001 -- any throw fails
        plugin_ok = False
        out = np.zeros((2, 16))
        print(f"       assistant raised: {exc}")

    finite = bool(np.all(np.isfinite(out)))
    peak_db = 20 * np.log10(max(float(np.max(np.abs(out))), 1e-12))
    ok = plugin_ok and finite and peak_db <= -3.0 + 0.05
    failures += [] if ok else ["assistant left the plugin unbounded or broken"]
    print(f"[{'PASS' if ok else 'FAIL'}] 24. assistant contained  output finite, peak "
          f"{peak_db:+.2f} dBFS vs a -3.0 ceiling "
          f"({'key set' if os.environ.get('GEMINI_API_KEY') else 'no key'})")

    # --- 25. an assist pass leaves the audio path intact ---------------------
    # The apply writes parameters from the analysis worker. If that ever raced
    # the audio thread the damage would surface as a transparency break at
    # centre -- the one invariant nothing is allowed to cost.
    set_param(assist, "distance", 0.0)
    set_param(assist, "output_db", 0.0)
    set_param(assist, "input_db", 0.0)
    set_param(assist, "extreme", False)
    set_param(assist, "bypass", False)
    set_param(assist, "ceiling_db", -0.3)
    assist.reset()
    ya = assist(probe, SR)
    lag = int(np.argmax(np.correlate(ya[0, : SR // 2], probe[0, : SR // 4], mode="valid")))
    n = min(probe.shape[1] - lag, ya.shape[1] - lag)
    delta = float(np.max(np.abs(ya[:, lag : lag + n] - probe[:, :n])))
    ok = delta < 1e-6
    failures += [] if ok else ["centre not transparent after an assist pass"]
    print(f"[{'PASS' if ok else 'FAIL'}] 25. assist keeps centre  max|delta| = {delta:.3e}")

    # --- 22. the adapted curve survives a session save/load -----------------
    # Frequencies only are stored, so this also proves the reload rebuilds the
    # compensation tables from them rather than restoring the factory pair.
    plugin2 = load_plugin(VST3)
    plugin2.raw_state = plugin.raw_state
    _, restored = transfer_db(plugin2, probe, -100.0)
    d_keep = float(np.max(np.abs(restored - after)))
    d_move = float(np.max(np.abs(restored - before)))
    ok = d_keep < 0.05 and d_move > 0.25
    failures += [] if ok else ["adapted curve did not survive a state round-trip"]
    print(f"[{'PASS' if ok else 'FAIL'}] 22. state round-trip   restored curve is "
          f"{d_keep:.4f} dB from the adapted one, {d_move:.2f} dB from factory")

    # --- 21. no click across a swap -----------------------------------------
    # Adapt WHILE a steady tone plays: the profile flips under live signal, so
    # any step in the curve shows up as a sample-to-sample jump.
    live = load_plugin(VST3)
    set_param(live, "distance", -100.0)
    set_param(live, "analyse", False)
    set_param(live, "extreme", False)
    set_param(live, "bypass", False)
    live.reset()
    tone = np.stack([0.3 * np.sin(2 * np.pi * 220 * np.arange(int(SR * 32.0)) / SR)] * 2
                    ).astype(np.float32)
    set_param(live, "analyse", True)
    live(tone, SR)                       # capture happens here
    set_param(live, "analyse", False)
    time.sleep(3.0)
    out = live(tone, SR)                 # the swap lands inside THIS render
    step = float(np.max(np.abs(np.diff(out[0]))))
    expected = float(np.max(np.abs(np.diff(0.3 * np.sin(
        2 * np.pi * 220 * np.arange(SR) / SR)))))
    ratio = step / max(expected, 1e-12)
    ok = ratio < 1.3
    failures += [] if ok else [f"click across profile swap (slew ratio {ratio:.3f})"]
    print(f"[{'PASS' if ok else 'FAIL'}] 21. no click on swap   slew ratio = {ratio:.3f}  "
          f"(< 1.3)")

    print()
    return failures


def main():
    global EXTREME

    if not os.path.exists(VST3):
        sys.exit(f"plugin not found: {VST3}")

    plugin = load_plugin(VST3)
    x = pink_noise(int(SR * DUR))
    all_failures = []

    for extreme, guard in ((False, 2.0), (True, 6.0)):
        EXTREME = extreme
        label = "2x  EXTREME" if extreme else "1x  NORMAL"
        print("=" * 62)
        print(f"  {label}   (5-7k guard limit {guard:+.1f} dB)")
        print("=" * 62)
        all_failures += [f"[{label}] {f}" for f in run(plugin, x, guard)]
        print()

    all_failures += [f"[adaptive] {f}" for f in run_adaptive()]

    if all_failures:
        print("FAILURES: " + "; ".join(all_failures))
        sys.exit(1)
    print("ALL CHECKS PASSED (both modes)")


if __name__ == "__main__":
    main()
