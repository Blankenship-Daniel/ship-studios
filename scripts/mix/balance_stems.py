"""Balance a set of stems to a stereo bus by MEASURED loudness — the right way to mix volumes.

Measures each stem's **integrated LUFS** (ITU-R BS.1770, via pyloudnorm), applies the gain needed to
hit a deliberate per-role target, pans, sums, and leaves headroom (it does NOT peak-normalize the sum,
which would throw the balance away). Prints the measured→target→gain table so the balance is explicit
and reproducible — never eyeball gains, never balance off RMS (RMS under-reads bright mics like
overheads, which read hot in LUFS and carry the cymbals/hi-hat).

Usage:
    python balance_stems.py <spec.json|inline-json>

spec = {
  "out": "projects/<track>/mix/bus.wav",
  "headroom_db": -6.0,          # final peak ceiling of the summed bus (keep headroom for the tone stage)
  "duration_s": null,           # optional: balance/sum only the first N seconds
  "stems": [
    {"file": "...overhead.wav",  "target_lufs": -22.0, "pan": 0.0},   # pan -1=L .. +1=R; stereo files keep their image
    {"file": "...kick in.wav",   "target_lufs": -17.0, "pan": 0.0},
    {"file": "...snare top.wav", "target_lufs": -20.0, "pan": -0.1}
  ]
}

Run with the stemmy-loops `mixing` venv (has pyloudnorm + soundfile). Balance levels FIRST, then reach
for EQ/compression/tone — a balance problem (e.g. too much hi-hat = overhead too loud) is not an EQ problem.
"""
import sys, json, math, os
import numpy as np, soundfile as sf
import pyloudnorm as pyln


def main():
    arg = sys.argv[1]
    spec = json.load(open(arg)) if os.path.exists(arg) else json.loads(arg)
    out = spec["out"]
    headroom = spec.get("headroom_db", -6.0)
    dur = spec.get("duration_s")

    # load + (optional) trim, find common length + sample rate
    loaded = []
    sr0 = None
    for s in spec["stems"]:
        a, sr = sf.read(s["file"], dtype="float32")
        sr0 = sr0 or sr
        if sr != sr0:
            raise SystemExit(f"sample-rate mismatch: {s['file']} is {sr}, expected {sr0}")
        if dur:
            a = a[: int(dur * sr)]
        loaded.append((s, a))
    n = min(len(a) for _, a in loaded)

    meter = pyln.Meter(sr0)
    bus = np.zeros((n, 2), np.float32)
    print(f"{'stem':30}{'meas LUFS':>11}{'target':>9}{'gain dB':>9}{'pan':>6}")
    for s, a in loaded:
        a = a[:n]
        meas = meter.integrated_loudness(a)            # 1-D mono or (n,ch) both accepted
        gain = 10 ** ((s["target_lufs"] - meas) / 20.0)
        pan = float(s.get("pan", 0.0))
        if a.ndim == 1:                                # mono -> equal-power pan into stereo
            th = (pan + 1) * 0.25 * math.pi
            st = np.stack([a * math.cos(th), a * math.sin(th)], 1)
        else:
            st = a if a.shape[1] == 2 else np.repeat(a, 2, 1)
        bus[: len(st)] += st * gain
        print(f"  {os.path.basename(s['file'])[:28]:28}{meas:>11.1f}{s['target_lufs']:>9.1f}"
              f"{20*math.log10(max(gain,1e-9)):>+9.1f}{pan:>6.2f}")

    peak = float(np.max(np.abs(bus)))
    if peak > 0:
        bus *= (10 ** (headroom / 20.0)) / peak
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    sf.write(out, bus, sr0, subtype="PCM_24")

    final = meter.integrated_loudness(bus)
    print(f"\nbalanced bus -> {out}")
    print(f"  {len(loaded)} stems · {n/sr0:.0f}s · bus LUFS {final:.1f} · peak {headroom:+.0f} dBFS (headroom kept for tone)")


if __name__ == "__main__":
    raise SystemExit(main())
