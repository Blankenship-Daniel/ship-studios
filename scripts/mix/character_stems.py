"""Apply per-stem UADx VST CHARACTER chains to drum stems (serial, UADx-safe).

    python character_stems.py <plans.json> <src_dir> <out_dir> [duration_s=0]

plans.json = [{stem, role?, character?, rationale?, recipe:{input_gain_db?, chain:[{file, params}],
               width?, output_peak_dbfs?}}, ...]
(the schema the drum-stems-character workflow emits in mode:'character'). Each stem flows:
  src -> input gain-stage -> UADx plugin chain (enum-safe set_param) -> optional M/S narrow
      -> peak-normalize -> out
Only the recipe's chain runs; an EMPTY chain (the 'Clean' character) is a faithful passthrough plus
the normalize invariant. Mono inputs stay mono. Measures before/after + flags any param that
failed/snapped.

Stems are processed ONE AT A TIME on purpose: each loads a UADx plugin, and concurrent UADx hosts
render non-deterministically (see MEMORY: "UADx workflow render nondeterminism"). This is the
per-stem-VST sibling of process_stems.py (which is the corrective/API-color pass).

Run with the stemmy-loops vst venv (pedalboard + the tools). duration_s>0 processes only the first
N seconds (fast audition); 0 = full length.
"""
import json, os, sys, tempfile
from pathlib import Path

import numpy as np, soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                            # scripts/ isn't a package
sys.path.insert(0, os.path.join(_HERE, "..", "..", "presets", "vst"))  # reuse the enum-safe param setter
from _core import peak_normalize          # noqa: E402  (the always-normalize invariant, shared core)
from apply_vst_preset import set_param    # noqa: E402  (exact-first, then nearest-valid enum snap)

PLUGIN_DIR = "/Library/Audio/Plug-Ins/VST3/"

def _tmp(tmpdir):
    fd, path = tempfile.mkstemp(suffix=".wav", dir=tmpdir); os.close(fd); return path

def render(src, recipe, out, mono):
    """src -> out: input gain -> UADx chain -> optional M/S narrow -> peak-normalize. Returns warn notes.

    Same render shape as presets/vst/apply_vst_preset.py (it reuses that module's enum-tolerant
    set_param), but loops one stem at a time and collapses dual-mono back to mono like process_stems.
    """
    from pedalboard import Pedalboard, load_plugin
    warns = []
    audio, sr = sf.read(src, dtype="float32", always_2d=True); x = audio.T.copy()
    if x.shape[0] == 1: x = np.repeat(x, 2, 0)
    x *= 10 ** (float(recipe.get("input_gain_db", 0.0)) / 20.0)
    plugins = []
    plugin_root = Path(PLUGIN_DIR).resolve()
    for e in recipe.get("chain") or []:
        # Resolve relative `file` entries under PLUGIN_DIR and refuse any path (absolute or
        # via `../`) that escapes it — plugin binaries are loaded+executed, so an untrusted
        # plans.json must not point load_plugin() at arbitrary filesystem locations.
        cand = Path(e["file"]) if str(e["file"]).startswith("/") else plugin_root / e["file"]
        cand = cand.resolve()
        if plugin_root not in cand.parents and cand != plugin_root:
            raise ValueError(f"plugin path escapes {PLUGIN_DIR!r}: {e['file']!r}")
        p = load_plugin(str(cand))
        for k, v in (e.get("params") or {}).items():
            note = set_param(p, k, v)               # never crashes the render; returns a note on fail/snap
            if note: warns.append(f"{os.path.basename(str(e['file']))}:{note}")
        plugins.append(p)
    y = Pedalboard(plugins)(x, sr) if plugins else x
    w = float(recipe.get("width", 1.0))
    if w != 1.0 and y.shape[0] == 2:                # M/S narrow toward mono (Crushed/TNK)
        mid = (y[0] + y[1]) * 0.5; side = (y[0] - y[1]) * 0.5 * w
        y = np.stack([mid + side, mid - side], 0)
    target = recipe.get("output_peak_dbfs", -1.0)   # absent -> -1 dBFS; explicit null -> faithful (no trim)
    if target is not None: y = peak_normalize(y, float(target))
    if mono: y = y[:1]                               # collapse dual-mono back to mono
    sf.write(out, y.T, sr, subtype="PCM_24")
    return warns

def m(path):
    from stemmy.loops_mcp.tools.measure_loudness import measure_loudness
    from stemmy.loops_mcp.tools.measure_spectrum import measure_spectrum
    L = measure_loudness(path).model_dump(); S = measure_spectrum(path).model_dump()
    return dict(lufs=L["integrated_lufs"], crest=L["crest_factor_db"],
                cen=S["spectral_centroid_hz"], tilt=S["spectral_tilt_db_per_octave"])

def main():
    with open(sys.argv[1]) as _f: plans = json.load(_f)
    src_dir = sys.argv[2]; out_dir = sys.argv[3]
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    os.makedirs(out_dir, exist_ok=True)
    print(f"{'stem':<16}{'LUFS b>a':>14}{'crest b>a':>13}{'centroid b>a':>16}{'tilt b>a':>14}  notes")
    with tempfile.TemporaryDirectory(prefix="character_stems_") as tmpdir:
        for plan in plans:
            name = os.path.basename(plan["stem"]); src = os.path.join(src_dir, name)
            if not os.path.exists(src): src = plan["stem"]
            info = sf.info(src); mono = (info.channels == 1)
            work = src
            if dur > 0:
                a, sr = sf.read(src, dtype="float32", always_2d=True)
                work = _tmp(tmpdir); sf.write(work, a[:int(dur*sr)], sr, subtype="PCM_24")
            recipe = plan.get("recipe") or {}
            before = m(work)
            out = os.path.join(out_dir, name)
            warns = render(work, recipe, out, mono)
            after = m(out)
            note = "" if not warns else "FAIL:" + ",".join(warns)
            print(f"{name:<16}{before['lufs']:>6.1f}>{after['lufs']:<6.1f}{before['crest']:>6.1f}>{after['crest']:<5.1f}"
                  f"{before['cen']:>7.0f}>{after['cen']:<7.0f}{before['tilt']:>6.2f}>{after['tilt']:<6.2f}  {note}")
    print(f"\nwrote character stems -> {out_dir}")

if __name__ == "__main__":
    raise SystemExit(main())
