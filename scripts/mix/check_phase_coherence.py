"""Verify a per-stem processing pass kept a multi-mic kit PHASE-COHERENT (so the stems still sum without
comb filtering). The verify step of the [[ff-stems]] skill — and a general guard for any per-stem render.

Processing each mic independently with non-zero-phase / non-latency-matched chains silently shifts the mics
in time and rotates their phase differently, so pairs that were in-phase end up partially CANCELLING on the
sum. This re-measures the inter-mic relationships before vs after and flags any that changed.

Usage:
    python scripts/mix/check_phase_coherence.py <before_dir> <after_dir> \
        [--suffix _ffchain] [--stems a,b,c] [--win 180 190] [--maxlag 2000]

before_dir = the stems fed to processing (ideally the phase-ALIGNED kit).  after_dir = the processed stems
(<stem><suffix>.wav). For each stem it reports the input->output signed cross-correlation (polarity + the
per-stem latency); for each PAIR it compares the inter-mic signed cross-correlation BEFORE vs AFTER and flags
a SIGN FLIP (polarity relationship inverted -> partial cancellation on sum) or a lag shift > 20 samples
(time misalignment -> comb filtering). Exit 0 = coherent, 1 = at least one pair degraded. Needs the loops
`vst`/dsp venv (numpy + soundfile).
"""
import sys
from pathlib import Path
import numpy as np
import soundfile as sf


def rd(p):
    x, sr = sf.read(str(p), dtype="float32", always_2d=True)
    return x[:, 0].astype(np.float64), sr


def xcorr(a, b, sr, lo, hi, maxlag):
    a = a[int(lo * sr):int(hi * sr)].copy()
    b = b[int(lo * sr):int(hi * sr)].copy()
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    a -= a.mean(); b -= b.mean()
    L = 1 << int(np.ceil(np.log2(2 * n)))
    cc = np.fft.irfft(np.fft.rfft(a, L) * np.conj(np.fft.rfft(b, L)), L)
    cc = np.concatenate([cc[-maxlag:], cc[:maxlag + 1]])
    cc /= (np.sqrt((a ** 2).sum() * (b ** 2).sum()) + 1e-20)
    k = int(np.argmax(np.abs(cc)))
    return float(cc[k]), k - maxlag


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    before, after = Path(a[0]), Path(a[1])
    suffix = a[a.index("--suffix") + 1] if "--suffix" in a else "_ffchain"
    win = (float(a[a.index("--win") + 1]), float(a[a.index("--win") + 2])) if "--win" in a else (None, None)
    # default > a linear-phase chain's latency (~2112 samp @ Medium) so the in->out column is valid;
    # the inter-mic comparison is the real signal (relative lag between two equally-delayed stems).
    maxlag = int(a[a.index("--maxlag") + 1]) if "--maxlag" in a else 4096

    if "--stems" in a:
        stems = a[a.index("--stems") + 1].split(",")
    else:
        stems = sorted(p.stem for p in before.glob("*.wav")
                       if (after / f"{p.stem}{suffix}.wav").is_file())
    pairs_in, pairs_out, srs = {}, {}, {}
    cache = {}

    def get(p):
        if p not in cache:
            cache[p] = rd(p)
        return cache[p]

    # default analysis window: middle 10 s (or full file if shorter)
    print(f"stems: {stems}")
    print(f"\n{'stem':16} {'in->out xcorr':>13} {'lag':>6}  polarity (chain)")
    for s in stems:
        bi, sr = get(before / f"{s}.wav")
        ai, _ = get(after / f"{s}{suffix}.wav")
        srs[s] = sr
        lo, hi = win if win[0] is not None else (max(0, len(bi) / sr / 2 - 5), len(bi) / sr / 2 + 5)
        r, lag = xcorr(bi, ai, sr, lo, hi, maxlag)
        print(f"{s:16} {r:>+13.3f} {lag:>6d}  {'INVERTED' if r < 0 else 'normal'}")

    degraded = 0
    print(f"\n{'pair':34} {'BEFORE':>16} {'AFTER':>16}   inter-mic coherence")
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            s1, s2 = stems[i], stems[j]
            sr = srs[s1]
            lo, hi = win if win[0] is not None else (max(0, len(get(before / f'{s1}.wav')[0]) / sr / 2 - 5),
                                                     len(get(before / f'{s1}.wav')[0]) / sr / 2 + 5)
            rb, lb = xcorr(get(before / f"{s1}.wav")[0], get(before / f"{s2}.wav")[0], sr, lo, hi, maxlag)
            ra, la = xcorr(get(after / f"{s1}{suffix}.wav")[0], get(after / f"{s2}{suffix}.wav")[0],
                           sr, lo, hi, maxlag)
            # Only STRONG shared-content pairs are phase-diagnostic. A lag/sign change on a near-zero
            # correlation is measurement noise (the two mics barely overlap), and an EQ that guts a
            # shared band re-keys the broadband correlation without any timing defect — so gate on
            # correlation strength and let the impulse latency_check.py own the real coherence verdict.
            notes = []
            strong = min(abs(rb), abs(ra))
            if strong < 0.35:
                notes.append("weak corr — not phase-diagnostic")
            else:
                if np.sign(rb) != np.sign(ra):
                    notes.append("SIGN FLIP"); degraded += 1
                if abs(la - lb) > 20:
                    notes.append(f"lag {la - lb:+d}smp ({(la - lb) / sr * 1000:+.1f}ms)")
                    if "SIGN FLIP" not in notes:
                        degraded += 1
            print(f"{s1+' x '+s2:34} r={rb:+.3f}@{lb:+5d}  r={ra:+.3f}@{la:+5d}   "
                  f"{'  '.join(notes) if notes else 'preserved'}")

    print(f"\n{'OK — inter-mic coherence preserved' if not degraded else f'DEGRADED — {degraded} pair(s) changed'}")
    return 1 if degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
