"""Build a SPEECH-FREE drum-activity key for gating.

The podcast bleed is loud in the close mics (snare plosives peak ~-11 dB), so any
gate keyed from the raw mics false-opens on speech and can't close on pure-speech
gaps. Demucs's 'drums' stem has the drums WITHOUT the speech — keying a gate from
it closes correctly on speech-only sections. This sums the Demucs drums stems of
kick_in + snare_top into one mono 48 kHz key. Run with the loops `separate` venv.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model
from scipy.signal import resample_poly

ROOT = Path("/Users/ship/Documents/code/ship-studios")
RAW = ROOT / "projects/desktop-drums/stems"
OUT = ROOT / "artifacts/desktop-drums-demucs/drum_key.wav"
KEY_MICS = ["kick_in", "snare_top"]


def dev() -> str:
    return "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")


def main() -> int:
    d = dev()
    model = get_model("htdemucs")
    model.to(d)
    model.eval()
    msr = int(model.samplerate)
    di = list(model.sources).index("drums")
    acc = None
    sr_out = 48000
    for s in KEY_MICS:
        x, sr = sf.read(str(RAW / f"{s}.wav"), always_2d=True)
        sr_out = sr
        wav = x.T.astype(np.float32)
        if wav.shape[0] == 1:
            wav = np.repeat(wav, 2, axis=0)
        if sr != msr:
            wav = resample_poly(wav, msr, sr, axis=1).astype(np.float32)
        t = torch.from_numpy(wav)
        ref = t.mean(0)
        t = (t - ref.mean()) / (ref.std() + 1e-8)
        with torch.no_grad():
            out = apply_model(model, t[None].to(d), shifts=1, split=True, overlap=0.25,
                              progress=True, device=d)[0]
        out = out * ref.std() + ref.mean()
        drums = out[di].cpu().numpy()           # (C, L) at msr
        if sr != msr:
            drums = resample_poly(drums, sr, msr, axis=1).astype(np.float32)
        mono = drums.mean(axis=0)               # (L,)
        acc = mono if acc is None else acc[: len(mono)] + mono[: len(acc)]
    sf.write(str(OUT), acc, sr_out, subtype="PCM_24")
    print(f"drum_key -> {OUT}  ({len(acc) / sr_out:.1f}s, {sr_out} Hz)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
