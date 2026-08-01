"""Manley VOXBOX channel strip on each de-bled drum stem — an alternate, all-tube
'Manley mix' (replaces the VCME + BB A5 chain). VOXBOX path = INPUT -> opto COMP
-> tube PREAMP -> Pultec EQ (peak-dip-peak) -> de-ess/limit. Mic-mode tube drive
for warmth/colour, gentle opto leveling, Pultec weight/air + mid de-box, de-ess
the stems that spit. All 25 params are enums -> driven via apply_vst_preset.py.

Source = de-bled clean stems (raw-debled/); gap-mute is re-applied afterward.
Mono close mics + stereo OH/room both handled (VOXBOX processes dual-mono).
"""
import json
import subprocess
import sys
from pathlib import Path
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

ROOT = repo_root()
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "projects/desktop-drums/stems/raw-debled"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "projects/desktop-drums/stems/voxbox"
PRESET_DIR = ROOT / "projects/desktop-drums/presets/voxbox"
HARNESS = ROOT / "presets/vst/apply_vst_preset.py"
PY = sibling_python()

# Common VOXBOX defaults; each stem overrides a few. Numeric enums as floats,
# string enums as exact strings (the harness setattr's them). mid_dip is negative.
BASE = {
    "source_select": "Mic", "low_cut": "Off", "phase": 0.0,
    "input": 4.0, "gain": 50.0,
    "comp_byp": "In", "comp_thresh": 6.0, "comp_attack": "Medium", "comp_rel": "Medium",
    "eq_byp": "In",
    "lo_peak": 0.0, "lo_peak_freq": 100.0,
    "mid_dip": 0.0, "mid_dip_freq": 500.0,
    "hi_peak": 0.0, "hi_peak_freq": 10000.0,
    "de_ess_byp": "Byp", "de_ess_sel": "6K", "de_ess_thr": 0.0,
    "transformer_byp": "In", "output": 0.0,
}

STEMS = {
    # kick_in: weight + beater click, light leveling, keep lows
    "kick_in": {"input": 4.0, "comp_thresh": 6.0, "comp_attack": "Med Fast",
                "lo_peak": 5.0, "lo_peak_freq": 100.0, "mid_dip": -3.0, "mid_dip_freq": 500.0,
                "hi_peak": 3.0, "hi_peak_freq": 4000.0},
    # kick_beater (2nd kick mic): click/attack layer; low-cut so it doesn't stack
    # sub under kick_in (kick_in owns the weight, the beater owns the attack)
    "kick_beater": {"low_cut": "80 Hz", "input": 4.0, "comp_thresh": 6.0, "comp_attack": "Med Fast",
                    "lo_peak": 1.0, "lo_peak_freq": 90.0, "mid_dip": -2.0, "mid_dip_freq": 500.0,
                    "hi_peak": 4.0, "hi_peak_freq": 4000.0},
    # crotch (low-weight mic): weight + de-box, no top
    "crotch_mic": {"input": 4.0, "comp_thresh": 6.0,
                   "lo_peak": 4.0, "lo_peak_freq": 100.0, "mid_dip": -3.0, "mid_dip_freq": 500.0},
    # snare top: body + crack + air, HPF kick bleed, de-ess the spit
    "snare_top": {"low_cut": "80 Hz", "input": 4.0, "comp_thresh": 7.0,
                  "lo_peak": 3.0, "lo_peak_freq": 150.0, "mid_dip": -3.0, "mid_dip_freq": 700.0,
                  "hi_peak": 5.0, "hi_peak_freq": 5000.0,
                  "de_ess_byp": "In", "de_ess_sel": "9K", "de_ess_thr": 4.0},
    # snare bottom: bright wires, HPF hard, gentle drive, de-ess hard
    "snare_bottom": {"low_cut": "120 Hz", "input": 3.0, "comp_thresh": 6.0,
                     "mid_dip": -2.0, "mid_dip_freq": 500.0, "hi_peak": 4.0, "hi_peak_freq": 8000.0,
                     "de_ess_byp": "In", "de_ess_sel": "9K", "de_ess_thr": 5.0},
    # overheads (stereo): gentle tube, open cymbals, air, de-whoosh, de-ess spit
    "overheads": {"low_cut": "80 Hz", "input": 3.0, "comp_thresh": 5.0, "comp_attack": "Med Slow",
                  "mid_dip": -2.0, "mid_dip_freq": 500.0, "hi_peak": 4.0, "hi_peak_freq": 12000.0,
                  "de_ess_byp": "In", "de_ess_sel": "12K", "de_ess_thr": 4.0},
    # room (stereo): tube warmth + glue, weight, de-boom, gentle open
    "room": {"low_cut": "80 Hz", "input": 4.0, "comp_thresh": 7.0, "comp_attack": "Med Slow",
             "lo_peak": 3.0, "lo_peak_freq": 100.0, "mid_dip": -3.0, "mid_dip_freq": 500.0,
             "hi_peak": 3.0, "hi_peak_freq": 10000.0},
}


def preset(name: str, ov: dict) -> dict:
    params = {**BASE, **ov}
    return {
        "name": f"voxbox-{name}",
        "description": f"Manley VOXBOX (Mic tube) on de-bled {name}.",
        "recipe": {"input_gain_db": 0, "output_peak_dbfs": -1.0, "width": 1.0,
                   "chain": [{"file": "uaudio_manley_voxbox.vst3", "params": params}]},
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    processed = 0
    for name, ov in STEMS.items():
        if not (SRC / f"{name}.wav").exists():
            print(f"\n--- {name}: no {name}.wav in {SRC} — skipped ---")
            continue  # STEMS is the union over mic-set variants; treat absent keys as N/A
        processed += 1
        pp = PRESET_DIR / f"{name}.json"
        pp.write_text(json.dumps(preset(name, ov), indent=2))
        print(f"\n=== {name} (Mic in{(ov.get('input', 4.0))} thr{ov.get('comp_thresh')}) ===")
        r = subprocess.run([str(PY), str(HARNESS), str(pp), str(SRC / f"{name}.wav"),
                            str(OUT / f"{name}.wav")], capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr[-1500:])
            raise SystemExit(f"{name} failed")
    if processed == 0:
        raise SystemExit(
            f"no STEMS keys matched a <key>.wav in {SRC} — check filenames match the "
            f"keys {sorted(STEMS)} (rename your stems to <key>.wav, or add a STEMS entry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
