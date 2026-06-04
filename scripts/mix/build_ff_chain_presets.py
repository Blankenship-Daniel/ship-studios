"""Translate per-stem chain PLANS into apply_vst_preset.py preset JSONs (the FabFilter channel-finalize
chain Pro-Q 4 -> Pro-MB -> Pro-C 2 -> Pro-L 2). The deterministic backbone of the [[ff-stems]] skill.

Usage:
    python scripts/mix/build_ff_chain_presets.py <plans.json> <out_dir> [--mode kit|single] [--unmask <unmask.json>]

plans.json = JSON array of plan objects (one per stem). Each plan:
  { "stem": str,
    "proq_bands":  [ {shape, frequency, gain, q, slope?, dynamic?, dynamic_range?, spectral?, spectral_density?} ],
    "promb_bands": [ {low_crossover, high_crossover, mode, threshold, range(NONZERO,neg), ratio, attack, release, knee?} ],
    "proc": {style, threshold, ratio, attack, release, knee?, mix?},
    "prol": {style, gain, ceiling_dbtp} }
Writes one preset JSON per stem to <out_dir>/<stem>.json in the apply_vst_preset.py "recipe" format.
Pure stdlib, deterministic. Apply with:
    <loops-vst-venv>/bin/python presets/vst/apply_vst_preset.py <out_dir>/<stem>.json <in.wav> <out.wav>

--mode kit  (DEFAULT — a MULTI-MIC kit that will be SUMMED) → phase-SAFE:
    Pro-Q processing_mode="Linear Phase" @ a FIXED processing_resolution; spectral bands demoted to plain
    dynamic; Pro-MB processing_mode="Linear Phase", lookahead OFF. Every stem then gets the SAME latency and
    NO per-stem phase rotation, so a prior drum-prep phase-alignment SURVIVES the EQ and the kit still sums
    coherently. (Min/Natural phase + per-stem spectral/lookahead give DIFFERENT per-stem latencies → comb
    filtering on the sum — the bug this mode exists to avoid.)
--mode single  (ONE stereo source, no inter-stem concern) → Pro-Q "Natural Phase" (min-phase, ~0 latency,
    keeps transient snap, no linear-phase pre-ring), Pro-MB "Dynamic Phase", spectral KEPT.

--unmask <unmask.json> = optional {stem: [proq_band, ...]} of complementary cross-stem cuts appended to that
    stem's Pro-Q. On a kit, cut the LOSER / the ambient mic (OH, room) that masks a close mic's fundamental;
    NEVER carve same-source close mics (kick vs sub/crotch) apart — they are meant to reinforce.

Floor-safe contract (both modes): Pro-C auto_gain OFF + no makeup; Pro-L gain 0; output_peak_dbfs=null
(faithful) so Pro-L owns the -1 dBTP true-peak ceiling without renormalization.
"""
import sys, json
from pathlib import Path

PROQ = "FabFilter Pro-Q 4.vst3"
PROMB = "FabFilter Pro-MB.vst3"
PROC = "FabFilter Pro-C 2.vst3"
PROL = "FabFilter Pro-L 2.vst3"
CUTS = {"Low Cut", "High Cut"}
KIT_RESOLUTION = "Medium"  # Pro-Q Linear-Phase resolution; identical across stems => identical latency


def build_proq(bands, mode):
    p = {}
    n = len(bands)
    for i in range(1, 25):
        p[f"band_{i}_enabled"] = i <= n
    p.update({"processing_mode": "Linear Phase", "processing_resolution": KIT_RESOLUTION}
             if mode == "kit" else {"processing_mode": "Natural Phase"})
    p.update({"character": "Clean", "gain_scale": 100.0, "output_level": 0.0, "auto_gain": False})
    for idx, b in enumerate(bands, start=1):
        shape = b["shape"]
        p[f"band_{idx}_used"] = "Used"
        p[f"band_{idx}_shape"] = shape
        p[f"band_{idx}_frequency"] = float(b["frequency"])
        if shape in CUTS:
            p[f"band_{idx}_slope"] = b.get("slope", "24 dB/oct")
        else:
            p[f"band_{idx}_gain"] = float(b.get("gain", 0.0))
            p[f"band_{idx}_q"] = float(b.get("q", 1.0))
        if b.get("dynamic"):
            p[f"band_{idx}_dynamics_enabled"] = "Dynamics Enabled"
            p[f"band_{idx}_dynamics_auto"] = "Dynamics Auto"
            p[f"band_{idx}_threshold"] = "Auto"
            p[f"band_{idx}_dynamic_range"] = float(b.get("dynamic_range", -6.0))
        else:
            p[f"band_{idx}_dynamics_enabled"] = "Dynamics Disabled"
            p[f"band_{idx}_dynamic_range"] = 0.0
        # kit mode demotes spectral to plain dynamic so every stem keeps IDENTICAL latency.
        if b.get("spectral") and mode != "kit":
            p[f"band_{idx}_spectral_enabled"] = True
            p[f"band_{idx}_spectral_density"] = float(b.get("spectral_density", 70.0))
        else:
            p[f"band_{idx}_spectral_enabled"] = False
    return {"file": PROQ, "params": p}


def ratio_str(r):
    return f"{float(r):.2f}:1"


def build_promb(bands, mode):
    p = {
        "processing_mode": "Linear Phase" if mode == "kit" else "Dynamic Phase",
        "oversampling": "Off",
        "lookahead_enabled": mode != "kit",  # off in kit mode => uniform latency
        "mix": 100.0, "input_level": 0.0, "output_level": 0.0,
    }
    for idx, b in enumerate(bands, start=1):
        rng = float(b["range"]) or -3.0  # range 0 == inert; guard the "must process" contract
        p[f"band_{idx}_state"] = "Enabled"
        p[f"band_{idx}_low_crossover"] = float(b["low_crossover"])
        p[f"band_{idx}_low_slope"] = "24.0 dB/oct"
        p[f"band_{idx}_high_crossover"] = float(b["high_crossover"])
        p[f"band_{idx}_high_slope"] = "24.0 dB/oct"
        p[f"band_{idx}_dynamics_mode"] = b.get("mode", "Compression")
        p[f"band_{idx}_threshold"] = float(b["threshold"])
        p[f"band_{idx}_range"] = rng
        p[f"band_{idx}_ratio"] = ratio_str(b.get("ratio", 3.0))
        p[f"band_{idx}_attack"] = float(b.get("attack", 15.0))
        p[f"band_{idx}_release"] = float(b.get("release", 40.0))
        p[f"band_{idx}_knee"] = float(b.get("knee", 18.0))
        p[f"band_{idx}_lookahead"] = 0.0 if mode == "kit" else 2.0
    return {"file": PROMB, "params": p}


def build_proc(c):
    return {"file": PROC, "params": {
        "style": c.get("style", "Punch"),
        "threshold": float(c["threshold"]),
        "ratio": ratio_str(c.get("ratio", 2.5)),
        "attack": float(c.get("attack", 15.0)),
        "release": float(c.get("release", 150.0)),
        "knee": float(c.get("knee", 18.0)),
        "mix": float(c.get("mix", 100.0)),
        "auto_gain": False, "auto_release": False,       # floor-safe: NO makeup
        "output_level": 0.0, "input_level": 0.0,
        "oversampling": "Off", "lookahead_enabled": False,
    }}


def build_prol(l):
    return {"file": PROL, "params": {
        "gain": float(l.get("gain", 0.0)),               # 0 = floor-safe true-peak safety, not a maximizer
        "style": l.get("style", "Transparent"),
        "output_level": float(l.get("ceiling_dbtp", -1.0)),
        "true_peak_limiting": True, "oversampling": "4x", "dithering": "Off",
    }}


def build_preset(plan, mode, unmask):
    proq_bands = list(plan["proq_bands"]) + list(unmask.get(plan["stem"], []))
    return {
        "name": f"{plan['stem']}-ffchain",
        "description": f"[{mode}] Pro-Q4 -> Pro-MB -> Pro-C2 -> Pro-L2 for {plan['stem']}. "
                       f"{plan.get('rationale', '')[:240]}",
        "plugin_build": "FabFilter Pro-Q 4 / Pro-MB / Pro-C 2 / Pro-L 2 (VST3, headless, no-iLok)",
        "mode": mode,
        "recipe": {
            "input_gain_db": 0,
            "output_peak_dbfs": None,                    # faithful: Pro-L owns the -1 dBTP ceiling
            "width": 1.0,
            "chain": [
                build_proq(proq_bands, mode),
                build_promb(plan["promb_bands"], mode),
                build_proc(plan["proc"]),
                build_prol(plan["prol"]),
            ],
        },
    }


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    mode = a[a.index("--mode") + 1] if "--mode" in a else "kit"
    unmask = json.loads(Path(a[a.index("--unmask") + 1]).read_text()) if "--unmask" in a else {}
    plans = json.loads(Path(a[0]).read_text())
    out_dir = Path(a[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        preset = build_preset(plan, mode, unmask)
        (out_dir / f"{plan['stem']}.json").write_text(json.dumps(preset, indent=2))
        nb = sum(1 for k in preset["recipe"]["chain"][0]["params"] if k.endswith("_used"))
        print(f"wrote {out_dir / (plan['stem'] + '.json')}  [{mode}]  Pro-Q {nb} bands"
              f"{' (+unmask)' if plan['stem'] in unmask else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
