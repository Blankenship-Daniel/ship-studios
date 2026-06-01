---
description: Process individual multi-mic stems — per-stem corrective + console/tape color, measured.
argument-hint: <stems-dir> [duration_s]
---

Invoke the **stem-process** skill on `$ARGUMENTS`.

`$1` is a dir of individual stems (ideally phase-aligned); optional `$2` = duration_s for a fast audition
(omit/`0` = full length). Per stem: diagnose from measurement (role-aware), then run
`scripts/mix/process_stems.py` — clean (**declick OFF**) → apply_eq (zero-phase) → de-harsh → dynamic-EQ →
transient → optional **console/tape color** (API Vision Channel Strip, **550 tops kept flat** — no 2–5 kHz
harshness) — with before→after per stem (crest up = punch, centroid/tilt watch for harshness). Mono stays
mono. Optionally re-sum raw vs processed to identical per-role targets for a loudness-matched A/B.
Needs `uv sync --extra vst`. **Validate at a short duration first, but don't tune tone on a non-representative
excerpt** (re-measure full-length). Hand the processed stems to [[warm-drum-bus]] / [[drum-mix]]. Defer to the
skill; report the per-stem table + the net kit read.
