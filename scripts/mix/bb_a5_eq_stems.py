"""EQ each VCME-processed desktop-drums stem through KIT BB A5 (Blackbird API Legacy
console strip): Mic-mode console color + API 550L (55L) 4-band EQ, role-appropriate
moves grounded in each stem's measured spectrum. Writes per-stem reusable presets next
to the project, then drives the canonical apply_vst_preset.py harness (which sets the
string/bool enums + gain-stages + peak-trims — apply-vst-chain's float dict can't).

Serial by design (Pedalboard loads on the main thread). KIT BB A5 renders mono fine.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ship/Documents/code/ship-studios")
# SRC / OUT default to the original run; override via argv: bb_a5_eq_stems.py <SRC> <OUT>
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "projects/desktop-drums/stems/vcme"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "projects/desktop-drums/stems/vcme-eq"
PRESET_DIR = ROOT / "projects/desktop-drums/presets/bb-a5"
HARNESS = ROOT / "presets/vst/apply_vst_preset.py"
PY = ROOT.parent / "stemmy-loops-mcp/.venv/bin/python"

# Per-stem 55L moves (gain dB / freq Hz from the discrete enum grids; shelf=type true).
STEMS = {
    "kick_in": dict(drive=30, hpf="30 Hz", bands={
        "55l_low_filter_gain": 2.0, "55l_low_filter_frequency": 50.0, "55l_low_filter_type": False,
        "55l_low_mid_filter_gain": -1.5, "55l_low_mid_filter_frequency": 240.0,
        "55l_high_mid_filter_gain": 2.0, "55l_high_mid_filter_frequency": 3000.0,
    }),
    "crotch_mic": dict(drive=30, hpf="30 Hz", bands={
        "55l_low_filter_gain": 2.0, "55l_low_filter_frequency": 100.0, "55l_low_filter_type": False,
        "55l_low_mid_filter_gain": -2.0, "55l_low_mid_filter_frequency": 240.0,
        "55l_high_filter_gain": -1.5, "55l_high_filter_frequency": 10000.0, "55l_high_filter_type": True,
    }),
    "snare_top": dict(drive=30, hpf="100 Hz", bands={
        "55l_low_filter_gain": 1.5, "55l_low_filter_frequency": 200.0, "55l_low_filter_type": False,
        "55l_low_mid_filter_gain": -2.0, "55l_low_mid_filter_frequency": 500.0,
        "55l_high_mid_filter_gain": 2.0, "55l_high_mid_filter_frequency": 5000.0,
        "55l_high_filter_gain": 2.5, "55l_high_filter_frequency": 12500.0, "55l_high_filter_type": True,
    }),
    "snare_bottom": dict(drive=24, hpf="150 Hz", bands={
        "55l_low_mid_filter_gain": -2.0, "55l_low_mid_filter_frequency": 240.0,
        "55l_high_mid_filter_gain": 1.5, "55l_high_mid_filter_frequency": 8000.0,
        "55l_high_filter_gain": 1.5, "55l_high_filter_frequency": 10000.0, "55l_high_filter_type": True,
    }),
    "overheads": dict(drive=24, hpf="80 Hz", bands={
        "55l_low_mid_filter_gain": -2.0, "55l_low_mid_filter_frequency": 240.0,
        "55l_high_filter_gain": 2.5, "55l_high_filter_frequency": 12500.0, "55l_high_filter_type": True,
    }),
    "room": dict(drive=30, hpf="60 Hz", bands={
        "55l_low_mid_filter_gain": -2.5, "55l_low_mid_filter_frequency": 240.0,
        "55l_high_mid_filter_gain": 1.0, "55l_high_mid_filter_frequency": 5000.0,
        "55l_high_filter_gain": 2.5, "55l_high_filter_frequency": 10000.0, "55l_high_filter_type": True,
    }),
}


def build_preset(name: str, cfg: dict) -> dict:
    params = {
        "pre_amp_source": "Mic Mode",
        "pre_amp_gain": float(cfg["drive"]),
        "high_pass_filter": cfg["hpf"],
        "eq_on_off": True,
        "eq_choice": "55L",
        "55l_continuous_gain": True,
        "master_bus": False,
        "hum": False,
    }
    params.update(cfg["bands"])
    return {
        "name": f"bb-a5-eq-{name}",
        "description": f"KIT BB A5 Mic-mode color (g{cfg['drive']}) + 55L EQ on VCME {name} stem.",
        "recipe": {
            "input_gain_db": 0,
            "output_peak_dbfs": -1.0,
            "width": 1.0,
            "chain": [{"file": "KIT BB A5.vst3", "params": params}],
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    for name, cfg in STEMS.items():
        preset_path = PRESET_DIR / f"{name}.json"
        preset_path.write_text(json.dumps(build_preset(name, cfg), indent=2))
        in_wav = SRC / f"{name}.wav"
        out_wav = OUT / f"{name}.wav"
        print(f"\n=== {name}  (Mic g{cfg['drive']}, HPF {cfg['hpf']}) ===")
        r = subprocess.run(
            [str(PY), str(HARNESS), str(preset_path), str(in_wav), str(out_wav)],
            capture_output=True, text=True,
        )
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            raise SystemExit(f"{name} failed (rc={r.returncode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
