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


def pick_params(p):
    """Ranked list of pushable params (best first) — so probe() can RETRY past a param whose only
    reachable extreme equals its own default (a single-param probe false-flags PASSTHROUGH then)."""
    names = [n for n in p.parameters
             if n.lower() not in ("bypass", "power", "master_bypass", "enable")
             and "meter" not in n.lower()]
    ranked, seen = [], set()
    for key in ("output", "gain", "level", "fader", "trim", "input", "drive", "boost", "mix",
                "freq", "cut", "thresh", "ratio"):
        for n in names:
            if key in n.lower() and n not in seen:
                ranked.append(n); seen.add(n)
    ranked += [n for n in names if n not in seen]
    return ranked


def pick_param(p):  # back-compat: the single best param
    r = pick_params(p)
    return r[0] if r else None


def extreme(par, current=None):
    """An extreme value to push ``par`` to. For an enum, prefer an end that DIFFERS from ``current``
    (the param's present/default value): vv[0] unless it equals current, else vv[-1] — otherwise a
    filter-only plugin whose enum default is at index 0 gets probed default-vs-default and falsely
    reads PASSTHROUGH."""
    vv = getattr(par, "valid_values", None)
    if vv:
        vv = list(vv)
        end = vv[0]
        if current is not None and end == current and len(vv) > 1:
            end = vv[-1]
        return end
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
    pns = pick_params(p)
    if not pns:
        return name, path, "NO-PARAMS", build
    # NOTE: a SINGLE-param probe can false-flag PASSTHROUGH — if the chosen extreme happens to equal
    # the param's own default (filter-only/enum-default-at-index-0 plugins) we compare default-vs-
    # default and see Δ0. So we (a) push an extreme that DIFFERS from the param's current value, and
    # (b) RETRY across more params before concluding PASSTHROUGH. Even then, verify a suspected
    # passthrough with a real corner (a meaningful param at a meaningful value), not just this probe.
    try:
        x = noise()
        a = render(path)                            # default, once
        best, attempts = 0.0, []
        for pn in pns[:6]:                           # cap the retry so probing stays quick
            cur = getattr(p.parameters[pn], "raw_value", None)
            cur = cur if cur is not None else getattr(p, pn, None)
            val = extreme(p.parameters[pn], cur)
            if val is None or val == cur:           # nothing distinct to push; skip
                continue
            b = render(path, pn, val)               # one param pushed to a distinct extreme
            n = min(a.shape[1], b.shape[1])
            d = float(np.max(np.abs(a[:, :n] - b[:, :n])))
            attempts.append((d, pn, val))
            best = max(best, d)
            if d > 1e-3:                             # responded — no need to retry further params
                break
    except Exception as e:
        return name, path, "PROBE-ERR", f"{pns[0]}: {str(e)[:70]}"
    if not attempts:
        return name, path, "NO-PUSHABLE-PARAM", build
    d_ab, pn, val = max(attempts, key=lambda t: t[0])
    nx = min(a.shape[1], x.shape[1])
    d_ax = float(np.max(np.abs(a[:, :nx] - x[:, :nx])))   # info only (confounded by plugin latency)
    # Param-response is the reliable discriminator: a passthrough / un-engaged plugin ignores its
    # params (and you can't dial it even if it adds default color), so it's unusable in a chain.
    verdict = "RENDERS ✓" if d_ab > 1e-3 else "PASSTHROUGH ✗ (ignores params)"
    tried = f", tried {len(attempts)} param(s)" if d_ab <= 1e-3 else ""
    return name, path, verdict, (f"pushed {pn}={val!r}  Δparam={d_ab:.2e} "
                                 f"(Δvs-in {d_ax:.1e}, latency){tried}  {build}")


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
