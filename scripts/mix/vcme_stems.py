"""Process the desktop-drums stems through Greenhouse Ghz VCME 3 (the VCME console
mixing engine). VCME requires a STEREO input — mono renders silent — so mono stems
are fed dual-mono and, because dual-mono stays bit-identical L==R, folded back to mono.
Defaults are VCME's stock console chain (comp 3:1/-18/+3 + soft-clip saturation +
brickwall limiter, all on). Serial by design: Pedalboard plugins load on the main thread.
"""

import os
import sys

import numpy as np
import soundfile as sf
from pedalboard import Pedalboard, load_plugin

PLUGIN = "/Library/Audio/Plug-Ins/VST3/Ghz VCME 3.vst3"
# SRC / OUT default to the original run; override via argv: vcme_stems.py <SRC> <OUT>
SRC = sys.argv[1] if len(sys.argv) > 1 else "/Users/ship/Documents/code/ship-studios/projects/desktop-drums/stems"
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{SRC}/vcme"
STEMS = [
    "crotch_mic.wav",
    "kick_in.wav",
    "overheads.wav",
    "room.wav",
    "snare_bottom.wav",
    "snare_top.wav",
]


def process(name: str) -> None:
    x, sr = sf.read(f"{SRC}/{name}", always_2d=False)
    x = np.asarray(x, dtype=np.float32)
    was_mono = x.ndim == 1
    inp = np.stack([x, x], axis=1) if was_mono else x  # dual-mono for VCME

    plugin = load_plugin(PLUGIN)  # fresh instance per stem
    y = np.asarray(Pedalboard([plugin])(inp, sr), dtype=np.float32)

    if was_mono:
        ldiff = float(np.max(np.abs(y[:, 0] - y[:, 1])))
        if ldiff > 1e-6:
            raise SystemExit(f"{name}: dual-mono diverged (L-R {ldiff:.2e}); refusing silent fold")
        out = y[:, 0]
    else:
        out = y

    sf.write(f"{OUT}/{name}", out, sr, subtype="PCM_24")
    chans = 1 if was_mono else out.shape[1]
    print(f"{name:18s} {'mono' if was_mono else 'stereo':6s} "
          f"in_peak {20 * np.log10(np.max(np.abs(x)) + 1e-12):6.1f}  "
          f"out_peak {20 * np.log10(np.max(np.abs(out)) + 1e-12):6.1f}  ch={chans}")


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for name in STEMS:
        process(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
