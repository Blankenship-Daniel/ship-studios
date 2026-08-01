"""De-bleed the raw desktop-drums mics with Demucs source separation.

The spoken-word/podcast bleed that overlaps the drum hits cannot be gated out (a
gate must stay open during drum decays, passing the simultaneous speech). Demucs
separates each mic into vocals (the speech) + the rest (drums+bass+other), so the
"no-vocals" sum removes the speech WHILE preserving drums and room ambience — the
de-bleed a gate can't do. Runs on the RAW stems, before VCME/BB A5.

Uses the Demucs PROGRAMMATIC API (not the CLI): torchaudio 2.12 routes its save
through torchcodec (not installed), so we read/write with soundfile ourselves and
keep full control of channel-count and sample rate. htdemucs runs at 44.1 kHz, so
we resample 48k->44.1k in and 44.1k->48k out. Mono mics are upmixed for the model
then folded back to mono. Run with the stemmy-loops `separate` venv.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model
from scipy.signal import resample_poly
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

ROOT = repo_root()
RAW = ROOT / "projects/desktop-drums/stems"
OUT = ROOT / "projects/desktop-drums/stems/raw-debled"
VOC = ROOT / "artifacts/desktop-drums-demucs/vocals"   # extracted speech, for QC
STEMS = ["crotch_mic", "kick_in", "overheads", "room", "snare_bottom", "snare_top"]


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def separate(model, wav_cn: np.ndarray, dev: str) -> np.ndarray:
    """wav_cn: (channels, samples) at model.samplerate. Returns (n_sources, C, L)."""
    t = torch.from_numpy(wav_cn)
    ref = t.mean(0)
    t = (t - ref.mean()) / (ref.std() + 1e-8)  # Demucs normalization
    with torch.no_grad():
        out = apply_model(model, t[None].to(dev), shifts=1, split=True,
                          overlap=0.25, progress=True, device=dev)[0]
    out = out * ref.std() + ref.mean()
    return out.cpu().numpy()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    VOC.mkdir(parents=True, exist_ok=True)
    dev = pick_device()
    model = get_model("htdemucs")
    model.to(dev)
    model.eval()
    msr = int(model.samplerate)
    srcs = list(model.sources)            # ['drums','bass','other','vocals']
    voc_i = srcs.index("vocals")
    print(f"htdemucs device={dev} sources={srcs} model_sr={msr}", flush=True)

    for s in STEMS:
        x, sr = sf.read(str(RAW / f"{s}.wav"), always_2d=True)   # (N, C)
        mono_in = x.shape[1] == 1
        wav = x.T.astype(np.float32)                              # (C, N)
        if mono_in:
            wav = np.repeat(wav, 2, axis=0)
        if sr != msr:
            wav = resample_poly(wav, msr, sr, axis=1).astype(np.float32)

        out = separate(model, wav, dev)                          # (n_src, C, L)
        novoc = out.sum(axis=0) - out[voc_i]                     # drums+bass+other
        voc = out[voc_i]

        def finish(cn: np.ndarray) -> np.ndarray:
            if sr != msr:
                cn = resample_poly(cn, sr, msr, axis=1).astype(np.float32)
            y = cn.T
            return y.mean(axis=1) if mono_in else y

        sf.write(str(OUT / f"{s}.wav"), finish(novoc), sr, subtype="PCM_24")
        sf.write(str(VOC / f"{s}.wav"), finish(voc), sr, subtype="PCM_24")
        print(f"{s:12s} -> no_vocals ({'mono' if mono_in else 'stereo'}) + vocals QC", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
