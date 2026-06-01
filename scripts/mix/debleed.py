"""Reduce mic bleed before balancing — because turning a close mic up also turns up its bleed.

Two modes:
  gate    — attenuate a close mic between its own hits (kills bleed in the gaps), keeping the hits intact.
            e.g. a snare-top mic full of hi-hat bleed: gate it so only the snare hits pass.
  cancel  — least-squares subtract a correlated bleed SOURCE from a TARGET, per channel.
            e.g. subtract the isolated hi-hat mic from the overheads to null the correlated hat bleed
            WITHOUT dulling the cymbals (they aren't in the hat mic). Keep `amount` < 1 to stay natural.

Usage:
    python debleed.py gate   <in.wav> <out.wav> [floor_db=-14] [thresh_pct=50] [release_ms=40]
    python debleed.py cancel <target.wav> <bleed_ref.wav> <out.wav> [amount=0.55]

Run with the stemmy-loops venv (soundfile + numpy). Stems should be phase/time-aligned first
(cancel relies on the bleed reference being time-aligned to the target).
"""
import sys
import numpy as np, soundfile as sf


def _smooth(x, sr, atk_s, rel_s):
    aa, ar = np.exp(-1 / (atk_s * sr)), np.exp(-1 / (rel_s * sr))
    e = 0.0
    out = np.empty_like(x)
    for i, v in enumerate(x):
        c = aa if v > e else ar
        e = c * e + (1 - c) * v
        out[i] = e
    return out


def gate(inp, outp, floor_db=-14.0, thresh_pct=50.0, release_ms=40.0):
    a, sr = sf.read(inp, dtype="float32")
    mono = a if a.ndim == 1 else a.mean(1)
    env = _smooth(np.abs(mono), sr, 0.001, 0.060)
    thr = np.percentile(env, 75) * (thresh_pct / 100.0)
    floor = 10 ** (floor_db / 20.0)
    g = np.where(env > thr, 1.0, floor)
    rg = np.exp(-1 / (release_ms / 1000.0 * sr))           # smooth gain (no clicks)
    p = 1.0
    sm = np.empty_like(g)
    for i, v in enumerate(g):
        p = v if v > p else rg * p + (1 - rg) * v
        sm[i] = p
    y = a * (sm if a.ndim == 1 else sm[:, None])
    sf.write(outp, y, sr, subtype="PCM_24")
    print(f"gate -> {outp}  closed {float(np.mean(g < 1))*100:.0f}% (floor {floor_db:+.0f} dB)")


def cancel(target, ref, outp, amount=0.55):
    t, sr = sf.read(target, dtype="float32")
    r, _ = sf.read(ref, dtype="float32")
    r = r.mean(1) if r.ndim > 1 else r
    n = min(len(t), len(r))
    t, r = t[:n], r[:n]
    rr = r - r.mean()
    chans = [t] if t.ndim == 1 else [t[:, c] for c in range(t.shape[1])]
    out = []
    corr_before = corr_after = 0.0
    cc = lambda a, b: float(np.dot(a - a.mean(), b - b.mean()) / (np.linalg.norm(a - a.mean()) * np.linalg.norm(b - b.mean()) + 1e-9))
    for ch in chans:
        g = np.dot(ch - ch.mean(), rr) / (np.dot(rr, rr) + 1e-9) * amount
        corr_before += cc(ch, r); cleaned = ch - g * r; corr_after += cc(cleaned, r); out.append(cleaned)
    y = out[0] if len(out) == 1 else np.stack(out, 1)
    sf.write(outp, y.astype(np.float32), sr, subtype="PCM_24")
    k = len(chans)
    print(f"cancel -> {outp}  target↔ref corr {corr_before/k:+.2f} -> {corr_after/k:+.2f} (amount {amount})")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    mode = sys.argv[1]
    if mode == "gate":
        gate(sys.argv[2], sys.argv[3], *[float(x) for x in sys.argv[4:]])
    elif mode == "cancel":
        cancel(sys.argv[2], sys.argv[3], sys.argv[4], *[float(x) for x in sys.argv[5:]])
    else:
        print("mode must be 'gate' or 'cancel'"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
