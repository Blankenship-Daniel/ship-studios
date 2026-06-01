"""Processing-probe: does a plugin actually RENDER headless, or just LOAD and pass audio through?

The reliable discriminator (proven this session): a passthrough/un-engaged plugin ignores its
parameters — its output equals the input no matter what you set. A plugin that's really processing
responds when you push a parameter. So we render a short loud noise burst twice — once at default,
once with one parameter pushed to an extreme — and compare. Differ => RENDERS; identical (and ==
input) => PASSTHROUGH (e.g. the UAD `.component` build, or an unauthorized/demo plugin).

Usage:
    python probe_plugin.py <plugin.vst3|/abs/path|basename> [more ...]

Run with the stemmy-loops `vst` venv (has pedalboard). For UADx, prefer the `uaudio_*.vst3` build —
the `UAD ….component` / `UAD ….vst3` twins pass through offline.
"""
import sys, glob, math
import numpy as np
from pedalboard import load_plugin, Pedalboard

DIR = "/Library/Audio/Plug-Ins/VST3/"
SR = 48000
N = SR  # 1 s


def resolve(a):
    if "/" in a:
        return a
    if (DIR + a) and glob.glob(DIR + a):
        return DIR + a
    hits = glob.glob(DIR + f"*{a}*.vst3") or glob.glob(DIR + f"*{a}*")
    return hits[0] if hits else (DIR + a)


def noise():
    rng = np.random.default_rng(11)
    x = rng.standard_normal((2, N)).astype(np.float32)
    return x * (10 ** (-6 / 20)) / np.sqrt(np.mean(x ** 2))   # -6 dBFS RMS, loud


def pick_param(p):
    names = [n for n in p.parameters
             if n.lower() not in ("bypass", "power", "master_bypass", "enable")
             and "meter" not in n.lower()]
    for key in ("output", "gain", "level", "fader", "trim", "input", "drive", "boost", "mix"):
        for n in names:
            if key in n.lower():
                return n
    return names[0] if names else None


def extreme(par):
    vv = getattr(par, "valid_values", None)
    if vv:
        vv = list(vv)
        return vv[0]  # an end of the enum
    lo = getattr(par, "min_value", None)
    if isinstance(lo, (int, float)) and math.isfinite(lo):
        return lo
    hi = getattr(par, "max_value", None)
    if isinstance(hi, (int, float)) and math.isfinite(hi):
        return hi
    return None


def render(path, param=None, value=None):
    p = load_plugin(path)
    if param is not None:
        setattr(p, param, value)
    return Pedalboard([p])(noise(), SR)


def probe(arg):
    path = resolve(arg)
    try:
        p = load_plugin(path)
    except Exception as e:
        return arg, path, "LOAD-FAIL", f"{str(e)[:80]}"
    name = getattr(p, "name", "?")
    build = "uaudio_* (native)" if "/uaudio_" in path else (
        "UAD component/legacy (likely passthrough!)" if (".component" in path or "/Universal Audio/" in path) else "")
    pn = pick_param(p)
    if not pn:
        return name, path, "NO-PARAMS", build
    try:
        val = extreme(p.parameters[pn])
        x = noise()
        a = render(path)                    # default
        b = render(path, pn, val)           # one param pushed to an extreme
    except Exception as e:
        return name, path, "PROBE-ERR", f"{pn}: {str(e)[:70]}"
    n = min(a.shape[1], b.shape[1], x.shape[1])
    d_ab = float(np.max(np.abs(a[:, :n] - b[:, :n])))      # responds to a param push?
    d_ax = float(np.max(np.abs(a[:, :n] - x[:, :n])))      # info only (confounded by plugin latency)
    # Param-response is the reliable discriminator: a passthrough / un-engaged plugin ignores its
    # params (and you can't dial it even if it adds default color), so it's unusable in a chain.
    verdict = "RENDERS ✓" if d_ab > 1e-3 else "PASSTHROUGH ✗ (ignores params)"
    return name, path, verdict, f"pushed {pn}={val!r}  Δparam={d_ab:.2e} (Δvs-in {d_ax:.1e}, latency)  {build}"


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    print(f"{'verdict':30} {'plugin':34} detail")
    for arg in sys.argv[1:]:
        name, path, verdict, detail = probe(arg)
        print(f"{verdict:30} {name[:34]:34} {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
