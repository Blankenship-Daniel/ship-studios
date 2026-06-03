"""Turn a find-loops run into tagged loop deliverables (raw + mastered multi-format).

    python build_loops.py <run_dir> <loops_out> <deliv_out>
        [--name-prefix watercolors_drums] [--target-lufs -15]
        [--presets distribution_44k_16,production_48k_24,master_96k_24]

<run_dir> is a `find-loops` output dir (contains manifest.json + loop WAVs). For each selected loop:
  1. optimize-seam  -> click-free wrap
  2. RAW   : tag-deliverable(seam -> <loops_out>/<name>.wav)         — keeps the source character, no re-master
  3. MASTER: render-mastered(seam, target_lufs, ceiling -1, transient 0)
             -> export-deliverables(presets, tag=False)              — correct per-preset sample-rate/bit-depth
             -> tag each export                                       — see the tagging gotchas below

Two hard-won tagging gotchas are handled here (do not "simplify" them away):
  * export-deliverables `tag=True` drops the RIFF INFO chunk -> always export with tag=False, then tag after.
  * tag-deliverable force-writes PCM_24 -> tagging a 16-bit deliverable silently upgrades it to 24-bit,
    defeating a 16-bit distribution preset. So: 24-bit exports get the full in-WAV tag (temp -> replace);
    16-bit exports keep PCM_16 and have the RIFF LIST chunk SPLICED in from a throwaway tagged 24-bit twin
    (true 16-bit WITH the embedded tag — beats sidecar-only; sidecar kept too). verify-tags -> tagged:true.

For high-crest drum material a low target_lufs over-limits (crest collapse) — default -15 keeps the
warm/tight dynamics. Run with the stemmy-loops mixing/vst venv.
"""
import sys, os, json, argparse, struct
from collections import defaultdict
import soundfile as sf
from stemmy.loops_mcp.tools import optimize_seam as _os, render_mastered as _rm, export_deliverables as _ed, tag_deliverable as _td
from stemmy.loops_mcp.tools.measure_loudness import measure_loudness


def _tag_24(path, **kw):  # 24-bit deliverable: full in-WAV RIFF tag, stays 24-bit
    t = path + ".t.wav"
    _td.tag_deliverable(path, t, **kw)
    os.replace(t, path)
    if os.path.exists(t + ".tags.json"):
        os.replace(t + ".tags.json", path + ".tags.json")


def _list_chunk_bytes(wav_path):
    """Return the full RIFF `LIST` chunk (id+size+data+pad) from a WAV, or None."""
    b = open(wav_path, "rb").read()
    if b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        return None
    i = 12
    while i + 8 <= len(b):
        cid = b[i:i + 8]
        sz = struct.unpack("<I", b[i + 4:i + 8])[0]
        end = i + 8 + sz + (sz & 1)  # even-pad
        if b[i:i + 4] == b"LIST":
            return b[i:end]
        i = end
    return None


def _tag_16(path, **kw):  # 16-bit: keep PCM_16, SPLICE the LIST chunk from a tagged 24-bit twin
    """tag-deliverable force-writes PCM_24, so we tag a throwaway 24-bit twin, then splice its RIFF
    LIST chunk onto the true 16-bit file (rewriting the RIFF size). Result = true PCM_16 WITH the
    embedded in-WAV tag (the splice beats sidecar-only — see [[stemmy-loops-tagging-gotchas]])."""
    t = path + ".t24.wav"
    _td.tag_deliverable(path, t, **kw)
    if os.path.exists(t + ".tags.json"):
        os.replace(t + ".tags.json", path + ".tags.json")  # keep the sidecar too
    chunk = _list_chunk_bytes(t)
    if chunk:
        b = bytearray(open(path, "rb").read())
        if len(b) & 1:
            b += b"\x00"
        b += chunk
        struct.pack_into("<I", b, 4, len(b) - 8)  # RIFF size = total - 8
        open(path, "wb").write(b)
    if os.path.exists(t):
        os.remove(t)


def _lk(p):
    m = measure_loudness(p).model_dump()
    return m["integrated_lufs"], m["sample_peak_dbfs"], m["crest_factor_db"]


def main():
    ap = argparse.ArgumentParser(description="Build tagged loop deliverables from a find-loops run.")
    ap.add_argument("run_dir"); ap.add_argument("loops_out"); ap.add_argument("deliv_out")
    ap.add_argument("--name-prefix", default="loop")
    ap.add_argument("--target-lufs", type=float, default=-15.0)
    ap.add_argument("--presets", default="distribution_44k_16,production_48k_24,master_96k_24")
    a = ap.parse_args()
    presets = [p.strip() for p in a.presets.split(",") if p.strip()]

    man = json.load(open(os.path.join(a.run_dir, "manifest.json")))
    loops = man["loops"]; bpm = int(round(man["bpm"]))
    seam_dir = os.path.join(a.run_dir, "seam"); mast_dir = os.path.join(a.run_dir, "master")
    for d in (seam_dir, mast_dir, a.loops_out, a.deliv_out):
        os.makedirs(d, exist_ok=True)

    ctr = defaultdict(int)
    print(f"{'loop':<34}{'seam dB b>a':>14}{'RAW lufs/crest':>17}{'MAST lufs/crest':>17}")
    for L in loops:
        ctr[L["bars"]] += 1
        name = f"{a.name_prefix}_{bpm}bpm_{L['bars']}bar_{chr(96 + ctr[L['bars']])}"
        bars = L["bars"]; src = os.path.join(a.run_dir, L["wav"])
        comment = f"{a.name_prefix} - {bars} bar (bar {L['bar_index']})"
        kw = dict(bpm=float(bpm), bars=bars, comment=comment, originator="ship-studios")

        seam = os.path.join(seam_dir, name + ".wav")
        sr = _os.optimize_seam(src, seam).model_dump()
        # RAW (no re-master)
        raw = os.path.join(a.loops_out, name + ".wav")
        _td.tag_deliverable(seam, raw, **kw)
        # MASTERED -> multi-format -> tagged
        mast = os.path.join(mast_dir, name + ".wav")
        _rm.render_mastered(seam, mast, target_lufs=a.target_lufs, ceiling_dbtp=-1.0,
                            transient_shape=0.0, high_pass_hz=30.0)
        _ed.export_deliverables(mast, a.deliv_out, presets=presets, tag=False)
        for p in presets:
            f = os.path.join(a.deliv_out, f"{name}.{p}.wav")
            if not os.path.exists(f):
                continue
            (_tag_16 if sf.info(f).subtype == "PCM_16" else _tag_24)(f, **kw)

        rl = _lk(raw); ml = _lk(mast)
        seam_s = f"{sr['seam_continuity_before_db']:.0f}>{sr['seam_continuity_after_db']:.0f}"
        print(f"{name:<34}{seam_s:>14}{f'{rl[0]:.1f}/{rl[2]:.1f}':>17}{f'{ml[0]:.1f}/{ml[2]:.1f}':>17}")

    nraw = len([f for f in os.listdir(a.loops_out) if f.endswith('.wav')])
    ndel = len([f for f in os.listdir(a.deliv_out) if f.endswith('.wav')])
    print(f"\nraw loops -> {a.loops_out} ({nraw} wav)")
    print(f"mastered  -> {a.deliv_out} ({ndel} wav across {len(presets)} formats)")


if __name__ == "__main__":
    raise SystemExit(main())
