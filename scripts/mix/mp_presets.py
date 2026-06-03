"""Generate the Massive Passive preset-harness JSONs from a compact spec (provenance for presets/vst/massive-passive-*.json).

The Massive Passive is a STEREO L/R EQ whose bands default to enable='OUT'. Every band engaged must set
enable+shape+gain+bw+freq, and (because LINK is a plugin-only gang that the harness shouldn't rely on)
we write BOTH channels explicitly with ctrllink='UNLINKED' — bulletproof regardless of link state.

    ../stemmy-loops-mcp/.venv/bin/python scripts/mix/mp_presets.py   # writes presets/vst/massive-passive-*.json
"""
import json
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "presets", "vst")
STD = "uaudio_manley_massive_passive.vst3"
MST = "uaudio_manley_massive_passive_m.vst3"
BAND_DEFAULTS = {"lo": ("SHELF", 150.0), "lomid": ("BELL", 560.0),
                 "himid": ("BELL", 1500.0), "hi": ("SHELF", 3900.0)}


def build_params(spec):
    """spec['bands'][name] = (enable, shape, gain, bw, freq). Filters/trim per channel. Both channels written."""
    p = {"power": True, "master_bypass": False, "ctrllink": "UNLINKED"}
    for ch in (1, 2):
        p[f"ch{ch}enable"] = "IN"
        p[f"ch{ch}gain"] = float(spec.get("trim", 0.0))
        p[f"ch{ch}lopass"] = spec.get("lopass", "OFF")
        p[f"ch{ch}hipass"] = spec.get("hipass", "OFF")
        for b, (dshape, dfreq) in BAND_DEFAULTS.items():
            if b in spec["bands"]:
                en, sh, g, bw, fr = spec["bands"][b]
                p[f"ch{ch}{b}enable"] = en
                p[f"ch{ch}{b}shape"] = sh
                p[f"ch{ch}{b}gain"] = float(g)
                p[f"ch{ch}{b}bw"] = float(bw)
                p[f"ch{ch}{b}freq"] = float(fr)
            else:
                p[f"ch{ch}{b}enable"] = "OUT"
                p[f"ch{ch}{b}shape"] = dshape
                p[f"ch{ch}{b}gain"] = 0.0
                p[f"ch{ch}{b}bw"] = 1.0 if spec["file"] == MST else 2.0
                p[f"ch{ch}{b}freq"] = dfreq
    return p


PRESETS = [
    {
        "name": "massive-passive-drum-bus",
        "file": STD,
        "description": "The broad 'everything-sounds-better' bus tone on the STANDARD build: a wide LOW SHELF boost @68 for weight + a LOW-MID BELL CUT @270 to keep the lows tight (the boost-some/cut-some move) + a HIGH SHELF @12k for air. Broad musical curves at modest dial positions — the Massive Passive's whole point. Measured on the Watercolors 8-bar drum loop (peak-normalized A/B, [L] measure-spectrum): band_ratio_low 0.798->0.856 (weight), low-mid 0.176->0.128 (tight), high-mid 0.0113->0.0076 (less harsh presence), high 0.0043->0.0053 (air), centroid 1593->1849 Hz, crest 14.63->14.55 (HELD — it's EQ).",
        "intended_for": "drum bus / drum loop / full-mix bus tonal shaping (weight + tight low-mids + a little air). Re-dial freqs to taste; remember the gain DIAL is not dB and interacts with bandwidth.",
        "bands": {
            "lo":    ("BOOST", "SHELF", 12.0, 1.5, 68.0),
            "lomid": ("CUT",   "BELL",  7.0,  2.0, 270.0),
            "hi":    ("BOOST", "SHELF", 13.0, 1.5, 12000.0),
        },
        "hipass": "22 Hz",
        "notes": [
            "GAIN DIAL IS NOT dB and is steeply nonlinear AND bandwidth-coupled: at default bw a bell dial 10 ~ +6 dB, dial 20 ~ +12; a WIDE bell (bw 1.0) tops out ~+4.6 dB even at dial 20, a NARROW bell (bw 3.0) reaches ~+21. Dial to the meter.",
            "BANDWIDTH param 1.0 = WIDEST/gentlest, 3.0 = NARROWEST/most gain (reversed vs a normal Q, and it interacts with gain — Manley calls it 'damping/resonance'). On a SHELF, wider = clean broad shelf; narrower adds a reverse-bell overshoot dip near the corner.",
            "Engaged-flat is NOT a null (tube make-up colour + a ~+1 dB lift @16-18k + a near-Nyquist rolloff). Only master_bypass=true nulls -> loudness-match every A/B.",
            "HPF 22 Hz tightens the very bottom under the low-shelf boost (Manley's intended low-end method: shelf for weight + HPF to tighten).",
        ],
    },
    {
        "name": "massive-passive-low-end-trick",
        "file": STD,
        "description": "The Pultec low-end trick, Massive-Passive style (STANDARD build): a LOW SHELF boost @47 for weight + a LOW-MID BELL CUT @180 to scoop the boxy low-mids -> big-but-tight bottom. Two real bands here; for the single-band version flip the low shelf to a NARROW bandwidth (bw ~3.0) so its built-in reverse-bell overshoot makes the dip for you (measured: lo SHELF @47 dial 20 bw3.0 = +15 @20 Hz / +0.4 @47 / +3.3 @150). Measured on the Watercolors loop ([L] measure-spectrum): band_ratio_low 0.798->0.847, low-mid 0.176->0.131 (the scoop), top ~unchanged, centroid 1593->1710, crest 14.63->14.55 (held).",
        "intended_for": "kick / bass / drum-bus low-end weight + tightness. For bass, try lo @33-47 + lomid cut @120-270.",
        "bands": {
            "lo":    ("BOOST", "SHELF", 13.0, 2.0, 47.0),
            "lomid": ("CUT",   "BELL",  10.0, 2.0, 180.0),
        },
        "hipass": "22 Hz",
        "notes": [
            "Single-band alternative (the box's signature): lo SHELF BOOST @47, bw ~3.0 (narrow) -> the Pultec-shelf reverse-bell dip lands near 47 Hz on its own (measured +15 @20 Hz / +0.4 @47 / +3.3 @150 at dial 20). One band, the whole curve.",
            "HPF 22 Hz keeps the sub from getting sloppy under the boost.",
            "Gain dial is not dB; bands are parallel (non-additive) so dial by ear.",
        ],
    },
    {
        "name": "massive-passive-air-deharsh",
        "file": STD,
        "description": "Open the top WITHOUT spitting (STANDARD build): a HIGH-MID BELL CUT @3.3k tames harshness/honk + a HIGH SHELF boost @16k for air. The 16k shelf is voiced with a reverse-bell dip near ~8 kHz, so it adds air while keeping sibilance/edge in check. The Massive Passive's 'expensive top' move. Measured on the Watercolors loop ([L] measure-spectrum): band_ratio_high-mid 0.0113->0.0056 (de-harsh), high 0.0043->0.0061 (air), centroid 1593->2038, low-mid ~held, crest 14.63->14.17 (held).",
        "intended_for": "bright/harsh drum bus, overheads, full mix, or master that needs air but reads brittle at 3-5 kHz. For a smoother top use bw wider; for more focused air, 12k.",
        "bands": {
            "himid": ("CUT",   "BELL",  10.0, 2.0, 3300.0),
            "hi":    ("BOOST", "SHELF", 12.0, 1.5, 16000.0),
        },
        "notes": [
            "16k/27k high shelves are deliberately voiced so the reverse-bell dip sits ~8 kHz -> 'air without the problem esses'. 27k is the supersonic 'ahh/3D' air move but at 44.1/48k it carves a midrange dip at extreme gain -> prefer 16k at 48k, or render at 96k for 27k.",
            "Engaged-flat already lifts ~+1 dB @16-18k (tube make-up) -> the air here is on top of that; loudness-match the A/B.",
            "Gain dial not dB; bandwidth reversed (1.0 wide, 3.0 narrow) and gain-coupled.",
        ],
    },
    # NOTE: the MST mastering preset is the hand-authored presets/vst/massive-passive-master-polish.json
    # (uaudio_manley_massive_passive_m.vst3) — kept separate; this generator emits the 3 STANDARD-build presets.
]


def main():
    for spec in PRESETS:
        params = build_params(spec)
        preset = {
            "name": spec["name"],
            "description": spec["description"],
            "intended_for": spec["intended_for"],
            "plugin_build": (f"UADx '{spec['file']}' (UADx NATIVE — RENDERS headless via Pedalboard; NOT the "
                             f"'UAD Manley Massive Passive{' MST' if spec['file']==MST else ''}.component' passthrough twin). "
                             "51 params, all enums; gain/bw/freq are NUMERIC enums but enable(CUT/OUT/BOOST), shape(BELL/SHELF), "
                             "lopass/hipass, ctrllink, power are STRING/bool enums -> set via this setattr harness, not apply-vst-chain's float dict "
                             "(which can't engage a band -> silent passthrough)."),
            "recipe": {
                "input_gain_db": 0,
                "output_peak_dbfs": -1.0,
                "width": 1.0,
                "chain": [{"file": spec["file"], "params": params}],
            },
            "notes": spec["notes"],
        }
        path = os.path.normpath(os.path.join(OUT, spec["name"] + ".json"))
        with open(path, "w") as f:
            json.dump(preset, f, indent=2)
        print("wrote", path)


if __name__ == "__main__":
    main()
