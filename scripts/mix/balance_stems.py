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
import os, sys
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import balance_to_bus    # noqa: E402  (pure-DSP core: measured-LUFS balance + sum)


def main():
    import json

    import pyloudnorm as pyln
    arg = sys.argv[1]
    if os.path.exists(arg):
        with open(arg) as _f:
            spec = json.load(_f)
    else:
        spec = json.loads(arg)
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
    lengths = [len(a) for _, a in loaded]
    n = min(lengths)
    if max(lengths) != n:                              # FIX 2: don't silently truncate the bus
        print(f"warning: stems differ in length ({min(lengths)}..{max(lengths)} samples); "
              f"summing only the shortest {n/sr0:.1f}s — all stems truncated to it", file=sys.stderr)

    meter = pyln.Meter(sr0)
    stems = [(a, float(s["target_lufs"]), float(s.get("pan", 0.0))) for s, a in loaded]
    bus, rows = balance_to_bus(meter, stems, headroom_db=headroom)

    print(f"{'stem':30}{'meas LUFS':>11}{'target':>9}{'gain dB':>9}{'pan':>6}")
    for (s, _a), r in zip(loaded, rows):
        if r["skipped"]:                              # FIX 2: bad-LUFS stem dropped, warn explicitly
            print(f"  {os.path.basename(s['file'])[:28]:28}{r['meas']:>11.1f}{r['target']:>9.1f}"
                  f"{'SKIP':>9}{r['pan']:>6.2f}  (non-finite LUFS — skipped, would NaN the bus)")
            continue
        print(f"  {os.path.basename(s['file'])[:28]:28}{r['meas']:>11.1f}{r['target']:>9.1f}"
              f"{r['gain_db']:>+9.1f}{r['pan']:>6.2f}")

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    sf.write(out, bus, sr0, subtype="PCM_24")

    final = meter.integrated_loudness(bus)
    kept = sum(1 for r in rows if not r["skipped"])
    print(f"\nbalanced bus -> {out}")
    print(f"  {kept}/{len(loaded)} stems · {n/sr0:.0f}s · bus LUFS {final:.1f} · "
          f"peak {headroom:+.0f} dBFS (headroom kept for tone)")


if __name__ == "__main__":
    raise SystemExit(main())
