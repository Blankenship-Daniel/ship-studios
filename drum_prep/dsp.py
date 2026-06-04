"""Shared DSP primitives for the drum_prep flows.

The numerics here are ported verbatim from the verified session scripts and
must not drift — each was independently cross-checked:
  * envelope-coarse -> waveform-refine alignment (no half-period slips)
  * the empirical apply-sign resolution loop in ``align_to``
  * coherent measurement + zero-phase (real, symmetric) FFT EQ that leaves an
    existing phase alignment undisturbed

Everything is pure numpy/scipy and stateless. ``centers`` (third-octave or
octave band centres in Hz) is passed explicitly so the same band math serves
both the tonal curve and the ownership shares.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import welch

# ISO third-octave + octave band centres (Hz) and the 6 macro reporting bands.
THIRD_OCT = np.array(
    [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
     1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500,
     16000, 20000], dtype=float)
OCT = np.array([31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], dtype=float)
GROUPS: dict[str, tuple[float, float]] = {
    "sub 20-60": (20, 60), "low 60-120": (60, 120), "lowmid 120-400": (120, 400),
    "mid 400-2k": (400, 2000), "presence 2-6k": (2000, 6000), "air 6-20k": (6000, 20000),
}


# --------------------------------------------------------------------------- #
# time-domain alignment helpers
# --------------------------------------------------------------------------- #
def mono(x: np.ndarray) -> np.ndarray:
    """Collapse a (N, ch) array to a mono (N,) signal by channel mean.

    A 1-D ``(N,)`` input is already mono and is returned unchanged."""
    a = np.asarray(x, dtype=float)
    return a.mean(axis=1) if a.ndim == 2 else a


def normcorr(a: np.ndarray, b: np.ndarray) -> float:
    """Zero-mean normalized cross-correlation scalar (Pearson) at zero lag.

    Trims to the shorter length so unequal-length segments (e.g. a close mic
    shorter than the overhead excerpt window) compare over their overlap rather
    than raising on the dot product."""
    n = min(len(a), len(b))
    if n == 0:
        return 0.0  # empty overlap -> 0 correlation (avoids a NaN from mean([]))
    a = a[:n] - a[:n].mean()
    b = b[:n] - b[:n].mean()
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        return 0.0  # NaN/Inf input -> 0 correlation (avoids a NaN dot product)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def lowpass(seg: np.ndarray, fc: float, sr: int) -> np.ndarray:
    """Brick-wall FFT low-pass at ``fc`` Hz (used only for lag estimation)."""
    n = len(seg)
    s = np.fft.rfft(seg)
    s[np.fft.rfftfreq(n, 1.0 / sr) > fc] = 0.0
    return np.fft.irfft(s, n)


def envelope(seg: np.ndarray, sr: int, fc: float = 60.0) -> np.ndarray:
    """Smoothed amplitude envelope — for unambiguous transient-timing delay."""
    return lowpass(np.abs(seg), fc, sr)


def fractional_delay(x: np.ndarray, delay: float) -> np.ndarray:
    """Shift ``x`` by ``delay`` samples (>0 later, <0 earlier), length preserved."""
    if delay == 0:
        return x.copy()
    n = len(x)
    pad = int(np.ceil(abs(delay))) + 8
    z = np.zeros(pad, dtype=x.dtype)  # pad matches x.dtype, but the rfft/irfft path
    # below always returns float64 regardless of input dtype (production input is
    # float64 from drum_prep.io.read, so no cast back is needed).
    xp = np.concatenate([z, x, z])
    nfft = len(xp)
    k = np.fft.rfftfreq(nfft)
    y = np.fft.irfft(np.fft.rfft(xp) * np.exp(-2j * np.pi * k * delay), n=nfft)
    return y[pad:pad + n]


def estimate(a: np.ndarray, b: np.ndarray, max_lag: int,
             center: int = 0, halfwidth: int | None = None) -> tuple[float, float]:
    """Sub-sample lag d* maximizing sum a[n]b[n-d], and the (signed) peak value.

    With ``halfwidth`` the peak is sought only within ``center +/- halfwidth``
    (refine a coarse envelope estimate without slipping a half-period).
    """
    n = max(len(a), len(b))
    if n == 0:  # both excerpts empty: log2(0) below overflows int(); no lag to find
        return 0.0, 0.0
    a = a - a.mean()
    b = b - b.mean()
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    # Clamp the search to the available correlation range. For normal inputs
    # nfft >> 2*max_lag so this is a no-op; it only guards pathologically short
    # segments (n <= max_lag), where the unclamped slices below would wrap the
    # circular correlation and return a corrupt lag.
    max_lag = min(max_lag, nfft - 1)
    cc = np.fft.irfft(np.fft.rfft(a, nfft) * np.conj(np.fft.rfft(b, nfft)), nfft)
    # Index from the front (len(cc) == nfft): identical to cc[-max_lag:] for any
    # max_lag >= 1, but correct at the degenerate max_lag == 0 (where cc[-0:] would
    # wrongly take the WHOLE array instead of the empty negative-lag slice).
    cc = np.concatenate([cc[nfft - max_lag:], cc[:max_lag + 1]])
    lags = np.arange(-max_lag, max_lag + 1)
    mag = np.abs(cc)
    if halfwidth is not None:
        win = (lags < center - halfwidth) | (lags > center + halfwidth)
        # Degenerate: the center +/- halfwidth window lies wholly outside the
        # searched [-max_lag, max_lag] range, so every bin would be masked and
        # argmax would return a bogus lag (idx 0 == -max_lag) with a misleading
        # peak. Decline cleanly with a zero lag and zero peak instead.
        if win.all():
            return 0.0, 0.0
        mag = mag.copy()
        mag[win] = -1.0
    idx = int(np.argmax(mag))
    peak = cc[idx]
    if 0 < idx < len(cc) - 1:
        y0, y1, y2 = abs(cc[idx - 1]), abs(cc[idx]), abs(cc[idx + 1])
        den = y0 - 2 * y1 + y2
        delta = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
    else:
        delta = 0.0
    return lags[idx] + delta, peak


def align_to(target_seg: np.ndarray, ref_seg: np.ndarray, max_lag: int, sr: int,
             band: float | None = None, hw: int = 60) -> tuple[float, float, float, float]:
    """Align target->ref. Coarse delay from envelopes (transient timing, no
    half-period ambiguity), then polarity + sub-sample refined on the waveform
    within +/- ``hw`` samples of the coarse estimate.

    Returns ``(delay_to_apply, polarity, pre_corr, post_corr)``.
    """
    a = lowpass(target_seg, band, sr) if band else target_seg
    b = lowpass(ref_seg, band, sr) if band else ref_seg
    d_coarse, _ = estimate(envelope(a, sr), envelope(b, sr), max_lag)
    d_star, peak = estimate(a, b, max_lag, center=int(round(d_coarse)), halfwidth=hw)
    pol = -1.0 if peak < 0 else 1.0
    best: tuple[float, float] | None = None  # empirically resolve apply-sign
    for s in (-d_star, d_star):
        c = normcorr(fractional_delay(a, s) * pol, b)
        if best is None or c > best[1]:
            best = (s, c)
    assert best is not None
    return best[0], pol, normcorr(a, b), best[1]


def pick_excerpt(ref_m: np.ndarray, sr: int, seconds: float = 40.0) -> slice:
    """Slice of the loudest ``seconds``-long window of ``ref_m`` (by energy)."""
    win = int(seconds * sr)
    # A non-positive window makes ``csum[:-win]`` (win==0 -> csum[:0]) empty and
    # crashes argmax, or (win<0) builds a bogus reversed slice — fall back to the
    # whole signal, consistent with the win>=len early return below.
    if win <= 0:
        return slice(0, len(ref_m))
    if win >= len(ref_m):
        return slice(0, len(ref_m))
    csum = np.concatenate([[0.0], np.cumsum(ref_m ** 2)])
    start = int(np.argmax(csum[win:] - csum[:-win]))
    return slice(start, start + win)


# --------------------------------------------------------------------------- #
# spectral / EQ helpers
# --------------------------------------------------------------------------- #
def psd(xmono: np.ndarray, sr: int, nperseg: int = 16384) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD. nperseg=16384 is the value the reference-match EQ was tuned and
    verified against — keep analysis and application on the same resolution.

    Clamp nperseg to the signal length so short inputs (e.g. a one-bar reference
    loop, < 8192 samples) don't trip welch's noverlap >= nperseg guard. Band
    aggregation is in fixed Hz bands, so a lower FFT resolution stays comparable."""
    nperseg = min(nperseg, len(xmono))
    return welch(xmono, fs=sr, nperseg=nperseg, noverlap=nperseg // 2, detrend=False)


def band_power(f: np.ndarray, p: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Sum PSD into 1/3-octave (or octave) bands around ``centers``."""
    return np.array([p[(f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))].sum() or 1e-20
                     for fc in centers])


def band_db(f: np.ndarray, p: np.ndarray, centers: np.ndarray) -> np.ndarray:
    return 10 * np.log10(band_power(f, p, centers) + 1e-20)


def shape(db: np.ndarray, centers: np.ndarray, lo: float = 80.0, hi: float = 12000.0) -> np.ndarray:
    """Normalize a band curve by subtracting its broadband mean over [lo, hi]
    so curves compare by SHAPE (tonal balance), not absolute level."""
    idx = (centers >= lo) & (centers <= hi)
    return db - db[idx].mean()


def group_avg(curve: np.ndarray, centers: np.ndarray,
              groups: dict[str, tuple[float, float]] = GROUPS) -> dict[str, float]:
    return {n: float(curve[(centers >= lo) & (centers < hi)].mean())
            for n, (lo, hi) in groups.items()}


def tilt(db: np.ndarray, centers: np.ndarray) -> float:
    """Spectral tilt in dB/octave (lstsq slope vs log2 frequency)."""
    if np.any(np.asarray(centers, dtype=float) <= 0):
        # log2(<=0) -> -inf/nan makes polyfit fail with "SVD did not converge";
        # reject up front so a caller passing a 0 Hz center gets a clear error.
        raise ValueError("tilt() centers must be positive frequencies (log2 needs > 0)")
    return float(np.polyfit(np.log2(centers), db, 1)[0])


def interp_gain_db(freqs: np.ndarray, centers: np.ndarray, gains_db: np.ndarray) -> np.ndarray:
    """Log-frequency interpolation of band gains onto FFT bins (DC forced flat).

    ``centers`` MUST be ascending (np.interp requires sorted ``xp``); the
    internal callers pass the ascending ``THIRD_OCT`` / ``OCT`` constants, so
    this is a guard only for external/direct callers.
    """
    if np.any(np.diff(centers) < 0):
        raise ValueError("centers must be ascending")
    lf = np.log10(np.clip(freqs, 1e-6, None))
    g = np.interp(lf, np.log10(centers), gains_db, left=gains_db[0], right=gains_db[-1])
    g[freqs <= 0] = 0.0
    return g


def zero_phase_eq(x: np.ndarray, sr: int, centers: np.ndarray, gains_db: np.ndarray) -> np.ndarray:
    """Apply a real (zero-phase) magnitude curve to each channel; length preserved.

    Because the gain is real and non-negative, the phase of every bin is left
    untouched — so a prior inter-mic phase alignment survives intact.

    A 1-D ``(N,)`` input is treated as a single channel and returned 2-D
    ``(N, 1)`` (production callers pass 2-D ``(N, ch)`` from
    :func:`drum_prep.io.read`; the 1-D path is for direct/unit use).

    Edge tradeoff (circular convolution): this does an *un-padded*
    ``rfft -> x gain -> irfft`` at length ``n``, which is circular (not linear)
    convolution — the filter's time-domain tail that would spill past the buffer
    end instead WRAPS around onto the start (and vice-versa). The interior is
    exact; only the first/last few samples carry the wrap. This is safe in the
    production envelope it's used in: modest gains on full-length stems (the
    reference-match step caps boosts/cuts at +6/-8 dB, where the filter tail is
    short and the edge contamination is inaudible against a multi-second stem).
    A *large narrow* boost (a long, ringing time-domain tail) or a *very short*
    buffer (a one-bar loop, where the edges are a large fraction of the signal)
    would produce audible edge contamination. The fix, if those cases arise, is
    to zero-pad to ``n + tail`` and crop back — mirroring
    :func:`fractional_delay` — which is deliberately NOT done here so the pinned
    numeric signature of the verified ref-match path stays bit-identical.
    """
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x  # normalize to (N, ch)
    n = x.shape[0]
    glin = 10 ** (interp_gain_db(np.fft.rfftfreq(n, 1.0 / sr), centers, gains_db) / 20.0)
    out = np.empty_like(x)
    for ch in range(x.shape[1]):
        out[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch]) * glin, n=n)
    return out
