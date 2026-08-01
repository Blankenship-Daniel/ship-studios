"""Dump a plugin's full Pedalboard-exposed parameter surface — names, ranges, enums, defaults.

The companion to probe_plugin.py: probe answers "does it render?", this answers "what can I set,
and to what?". The names it prints are the exact snake_case keys apply_vst_preset.py / apply-vst-chain
expect; enum params print their valid_values (set those via the preset harness, not the float dict).

Usage:
    python dump_params.py <plugin.vst3|/abs/path|basename> [more ...]

Run with the stemmy-loops `vst` venv (has pedalboard). For UADx prefer the uaudio_*.vst3 build.
"""
import sys, glob
from pedalboard import load_plugin

DIR = "/Library/Audio/Plug-Ins/VST3/"


def resolve(a):
    if "/" in a:
        return a
    hits = glob.glob(DIR + f"*{a}*.vst3") or glob.glob(DIR + f"*{a}*")
    return hits[0] if hits else (DIR + a)


def dump(arg):
    path = resolve(arg)
    p = load_plugin(path)
    name = getattr(p, "name", "?")
    params = p.parameters
    print(f"\n=== {name}  ({path})")
    print(f"{len(params)} parameters\n")
    for n in params:
        par = params[n]
        vv = getattr(par, "valid_values", None)
        try:
            # The COOKED value (enum label / real-world float), which is what
            # valid_values are expressed in — not `par.raw_value`, Pedalboard's
            # normalized 0..1 float (see probe_plugin.same_value).
            cur_str = repr(getattr(p, n))
        except Exception:
            cur_str = "?"
        if vv:
            vv = list(vv)
            shown = vv if len(vv) <= 24 else vv[:12] + ["…"] + vv[-6:]
            print(f"  {n:32} ENUM  default={cur_str:>14}  values={shown}")
        else:
            lo = getattr(par, "min_value", None)
            hi = getattr(par, "max_value", None)
            unit = getattr(par, "units", "") or ""
            print(f"  {n:32} NUM   default={cur_str:>14}  range=[{lo}, {hi}] {unit}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    for arg in sys.argv[1:]:
        try:
            dump(arg)
        except Exception as e:
            print(f"\n=== {arg}: DUMP-FAIL {str(e)[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
