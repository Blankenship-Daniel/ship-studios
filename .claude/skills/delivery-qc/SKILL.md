---
name: delivery-qc
description: "Use before shipping any deliverable — 'QC these deliverables', 'are these ready to ship', 'check the master/loops before delivery', 'did the tags survive export'. A pre-flight gate fusing loudness/true-peak/clipping/streaming checks with TAG/format verification (the piece no other tool covers). Spans the stemmy MCP servers + a local drum-prep verify-tags."
---

# QC deliverables before shipping

Goal: a final pre-flight gate that decides **ship / don't-ship** on a finished
deliverable (a master, an export matrix, or a loop set) before it leaves the
studio. This skill fuses the objective checks — loudness, true-peak, clipping,
per-platform compliance — with the one thing no meter covers: **did the tags
and format actually survive the export.**

Lead with the real failure this catches: **`export-deliverables tag=true`
silently drops the embedded tags.** Only the `fmt ` and `data` chunks survive
the write — the RIFF INFO `LIST` chunk is gone — yet the export's return value
reads as success. A clean loudness/true-peak report says nothing about whether
the file is tagged. **Never trust the export's success return; verify the
written files.**

Three tools are in play. Objective DSP/compliance checks live on
**stemmy-loops** (`[L]`) and **stemmy-gemini** (`[G]`); the tag/format
verification is a **local helper** — `drum-prep verify-tags` (numpy/soundfile,
not an MCP tool). Every MCP name below is verified; mind hyphen vs underscore.

## Prerequisites

- `.mcp.json` registers both `stemmy-loops` and `stemmy-gemini` (siblings at
  `../stemmy-loops-mcp`, `../stemmy-gemini-mcp`). Confirm both are up.
- `[G] check-streaming-targets` and `[G] check-delivery-spec` are pure DSP and
  need **no** `GEMINI_API_KEY`. `[L] check-clipping` / `[L] inspect-loop` are
  core DSP, no key.
- The local `drum-prep` console script needs `uv sync --extra drum-prep` (run
  from the repo root). It is **local DSP, not an MCP server.**
- Resolve up front: the deliverable path(s) — a single master WAV, a
  `projects/<track>/deliverables/` directory, or a `loops/` set — and the
  destination platform(s) to check compliance against.

## Recipe (ordered, per deliverable file/dir)

1. **Per-platform compliance** — `[G] check-streaming-targets {path,
   platforms}`. LUFS-I + true-peak vs each platform's target; flags whether
   the platform will attenuate or the ceiling is breached.
2. **Clipping / DC / polarity** — `[L] check-clipping {path}`. Inter-sample
   clip, DC offset, and polarity inversion — failures a LUFS read won't show.
3. **Delivery spec pre-flight** — `[G] check-delivery-spec {path}`. The
   general deliverability pass (format/headroom/peak sanity).
4. **Loop deliverability (loops only)** — `[L] inspect-loop {path}`. One-shot
   deliverability report per loop (seam, length, headroom). Skip for a stereo
   master.
5. **Tag + format verification (LOCAL, crucial)** —
   `drum-prep verify-tags <DIR>`. For every WAV it parses the RIFF chunk
   headers and the `.tags.json` sidecar, reporting `has_list_chunk`,
   `has_sidecar`, and `tagged` per file (`tagged = LIST chunk OR sidecar
   present`), plus channels / samplerate / subtype. This is the **only** check
   that catches the silent tag-drop above. Run it on the *written* export dir.
6. **Album-set loudness (multi-track releases only)** — when QC'ing a whole
   EP/album, `[L] analyze-album-normalization {dir, target_lufs}` for the shared
   gain a platform will apply (TD1008 vs album-integrated) and which tracks play
   quieter under album mode. Skip for a single deliverable.
7. **Reconcile into a gate.** Any file that is out-of-spec (step 1–4) **or**
   untagged (step 5) fails the gate. A clean step 1–4 with `tagged: false` is
   still a **don't-ship**.

## Outputs

- No new audio is written — this is a read-only gate.
- A per-file QC table and a single ship / don't-ship verdict (see below).
- If anything is untagged, the remediation is a re-tag, not a re-export (a
  re-export through `tag=true` drops them again).

## Reporting to the user

Emit a **per-file table** with columns: file · LUFS-I · true-peak dBTP ·
clip/DC/polarity · **tagged** (yes/no, with `has_list_chunk` /`has_sidecar`).
Then a **single ship / don't-ship verdict** that explicitly lists every
untagged or out-of-spec file. Don't bury a `tagged: false` inside a wall of
green loudness numbers — surface it.

## Pitfalls

- **A clean loudness/true-peak report does NOT mean tagged.** Always run
  `drum-prep verify-tags`; the meters and the tag check are orthogonal.
- **Don't trust the export's success return.** `export-deliverables tag=true`
  returns success while silently dropping the RIFF INFO `LIST` chunk — only
  `verify-tags` reveals it.
- **Re-tag, don't re-export, when untagged.** Re-running the export with
  `tag=true` will drop the tags again. Re-tag the exported files instead —
  **out-of-place** (`tag-deliverable` with `out_path != path`, then move the
  tagged WAV back over the export; in-place tagging fails on the `.tmp`
  extension). See the `stemmy-loops-tagging-gotchas` memory note and the
  tagging step in [[loops-to-deliverables]].
- **`verify-tags` takes a directory.** Point it at the deliverables dir, not a
  single file.
- **Verify the written files, not the source.** Steps 1–5 must point at the
  exported deliverable, never the pre-export master/loop.

## Related

- [[loops-to-deliverables]] — produces the loop deliverables this gate checks; holds the tagging step to re-run if untagged
- [[master-track]] — produces the master + export matrix this gate fronts
- [[release-package]] — the album-assembly stage this gate backs up (shares the album-normalization read)
