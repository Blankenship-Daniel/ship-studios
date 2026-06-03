---
name: multitrack-triage
description: Use when the user has a pile of raw, interface-named multi-mic recordings and wants them cleaned and organized before alignment/mixing — "clean up these raw stems", "triage my drum session recordings", "which channels are dead", "are these the same song or different takes", "split/organize this Logic dump", "the ADAT tracks are clipped", "figure out which mic is which", "prep these for drum-prep". Turns a flat folder of interface-input WAVs into clean, song-split, role-labeled per-song kits with a kit.json ready for [[drum-prep]]. Local DSP + sox/ffmpeg + Gemini ears; never mutates a DAW project.
argument-hint: <raw stems dir>
---

# Triage raw multi-mic recordings into clean, labeled kits

Goal: take the messy output of [[logic-extract]] (or any tracking dump) — files
named by interface input, multiple takes, dead channels, dual-mono pairs, clipped
banks, and sometimes *several different songs mixed together* — and turn it into
clean, song-separated, role-labeled kits with a `kit.json` that [[drum-prep]] can
align. Everything writes to gitignored scratch; the source dump is never mutated.

This is the missing stage between "raw files exist" and "drum-prep aligns a kit."
It combines fast local DSP (sox/ffmpeg + the scripts below), the stemmy MCP meters
(`check-clipping`, `measure-spectrum`, `measure-stereo`), and Gemini's ears
(`compare-audio-files`, `classify-audio`) for the judgment calls.

## Prerequisites

- A folder of WAV/AIFF, same sample rate (e.g. `artifacts/<slug>-raw/` from
  [[logic-extract]]).
- `ffmpeg`/`ffprobe`/`sox` on PATH. Helper scripts live next to this skill in
  `.claude/skills/multitrack-triage/scripts/` (run `chmod +x` once).
- `GEMINI_API_KEY` for the song-grouping / role-ID steps (Gemini listens). The
  measurement steps are pure DSP, no key.
- For the eventual hand-off: `uv sync --extra drum-prep` (see [[drum-prep]]).

## Recipe (ordered)

1. **Inventory + measure (read-only).** Run the scanner per take folder:
   `scripts/scan-channels.sh <dir>` → peak/RMS/DC + a FLAG (DEAD/HOT/LOW/live)
   per channel. For every HOT channel, confirm real clipping with
   `[L] check-clipping` (sample-peak pinned at 0 dBFS + tens of thousands of
   clipped samples + inter-sample peak > 0 dBTP = genuine converter clipping).
2. **Quarantine DAW artifacts.** Move Logic `merged`/`merged_1` fragments (and any
   obvious scratch) to `quarantine/`. They're sub-fragments of a take, not channels.
3. **Split dual-mono pairs.** Interface inputs sometimes pack two independent mono
   sources into one interleaved file (`..._1_2.wav` — a DI pair, or a stereo room).
   `scripts/split-dual-mono.sh <file> --delete-original` → `_1` + `_2` and reports
   the L-R difference (`-inf` = identical dual-mono; large = two distinct sources).
4. **Group takes into SONGS (Gemini).** Different record passes are often
   *different songs*, not alternate takes — and **different durations are a strong
   hint they differ**. Make a ~60–75 s excerpt of the most melodic/instrument
   channel from each take (the DI/guitar/bass channel discriminates far better
   than drums), then `[G] compare-audio-files` with a schema asking it to group
   files into songs. Keep distinct songs separate; only treat same-song passes as
   a redundant pair.
5. **Pick the best take** of each genuinely-redundant pair: fewest clipped samples
   (`check-clipping`), most complete (longest without a breakdown), best
   performance (Gemini's read in step 4). Quarantine the loser — don't delete; full
   performances are recoverable. Reorganize into `songA/ songB/ …` (meaningful
   names beat `take-02`).
6. **Drop dead channels — but verify across takes first.** `scan-channels.sh`
   flags DEAD (peak < −60 dB) vs LOW (−60…−25 dB, bleed — keep). **A channel can be
   DEAD in one song and live in another** (a real mic that was just unused/quiet
   that take). Re-scan a candidate across all takes before removing it. Delete only
   the truly-dead per the user's call (originals are safe in the DAW); quarantine
   if unsure.
7. **Handle clipping.** For channels `check-clipping` confirms clipped, per the
   user's choice: accept as-is, or reconstruct with
   `scripts/declip.sh <in> <out> [hpf]` (ffmpeg adeclip + HPF + renormalize).
   Heavy clipping only partially recovers — say so; re-tracking is the only true fix.
8. **Infer roles → kit.json.** Build the role map for each song's kit:
   - **Overheads (the anchor) — find by correlation, not by guessing.** The OH
     stereo pair shares the cymbal field, so it self-identifies: merge candidate
     full-range channels into stereo (`ffmpeg ... amerge`) and run
     `[L] measure-stereo`; the pair with the **highest positive correlation** is
     the overheads, the uncorrelated full-range one is the room.
   - **Close mics — use the spectrum, not Gemini.** `[L] measure-spectrum` per
     channel: kick = >80% energy <120 Hz, peak ~50–70 Hz, steep tilt; snare =
     mid + HF presence; toms = low-mid focused, little HF; hat/ride/crash =
     bright, high centroid, ~no lows. **Gemini `classify-audio` is unreliable
     here — every mic hears snare/hat bleed**, so it returns "snare 0.95, hat 0.9"
     for nearly everything, including the kick mic. Trust spectrum for close mics.
   - Write `<song>/cleaned/kit.json` (see schema below). **File names MUST include
     the `.wav` extension.** Present the map to the user as a proposal and have
     them confirm — overheads + kick are usually high-confidence from data; the
     snare/tom/cymbal split is a guess they can correct cheaply.
9. **Prep the kit dir for drum-prep.** Put the song's drum mics (HPF'd via
   `clean-loop`/sox `highpass -2 30`, declipped where needed) in `<song>/cleaned/`
   alongside `kit.json`. Exclude non-kit instruments (a real DI). Confirm with
   `uv run --extra drum-prep drum-prep detect <song>/cleaned/`.
10. **Hand off to [[drum-prep]].** `phase-align` (or full `chain` if a reference
    exists). Then build a listen test — see "Phase audition" below.

## kit.json schema (the role map drum-prep reads)

```json
{
  "version": 1, "src_dir": ".", "overhead_mode": "stereo",
  "stems": [
    {"file": "A_ADAT_1.wav", "role": "overhead_l"},
    {"file": "A_ADAT_2.wav", "role": "overhead_r"},
    {"file": "B_ADAT_1.wav", "role": "kick_in"},
    {"file": "B_ADAT_2.wav", "role": "kick_beater", "partner": "B_ADAT_1.wav"},
    {"file": "B_HIZ_1.wav",  "role": "room", "ambience": true},
    {"file": "B_HIZ_2.wav",  "role": "room", "ambience": true}
  ]
}
```

Roles (from `drum_prep/roles.py`): `overhead` / `overhead_l` / `overhead_r`,
`room` (ambience: polarity-checked, timing kept), `kick_in` / `kick_beater` /
`kick_out` / `kick_sub`, `snare_top` / `snare_bottom`, `hihat`, `ride`, `crash`,
`tom` (use `label` to disambiguate multiples). Partner pairs (snare bottom→top,
kick beater→in) get a `partner` key. A stereo room = two `room` entries.

## Phase audition (before/after — the proof alignment worked)

drum-prep writes aligned stems as **24-bit AIFF with a `.wav` extension** —
ffmpeg can't read those directly. Convert first:
`scripts/aiff2wav.sh <song>/cleaned/phase-aligned /tmp/al`. Then build a
loudness-matched mono **before vs after** A/B (mono-sum reveals phase cancellation)
and a full stereo kit mix:

- Mono-sum each set, **trim inside the filtergraph** (`amix=...:normalize=0,atrim=START:END,asetpts=PTS-STARTPTS,loudnorm=I=-16:TP=-1.5`). Input-side `-ss/-t` only applies to the *first* `-i`, so multi-input trims must use `atrim`.
- Concat `[before | 0.6 s silence | after]`.
- Read the win from the phase-align JSON (per-mic `pre_corr`→`post_corr` going
  positive) — that's the unambiguous evidence; the mono low-end delta is a
  secondary, mix-dependent check.

## Outputs

```
artifacts/<slug>-raw/
  songA/ songB/ ...            # one per song; meaningful names
    <interface>.wav            # cleaned, split, dead-dropped channels
    cleaned/                   # drum mics prepped for drum-prep + kit.json
      kit.json
      phase-aligned/           # (from drum-prep) 24-bit AIFF in .wav names
      auditions/               # before/after + stereo kit mix
  quarantine/                  # merge-fragments, non-best takes, removed channels
  MANIFEST.md                  # what each channel is, what was done, what's a guess
```

Always write a `MANIFEST.md`: the song grouping, the role map with a
confirmed-vs-guess column, the clipping verdict, and what was quarantined/deleted.

## Reporting to the user

Lead with the structure discovered (how many songs, which takes collapsed). Give
the role map as a table marking user-confirmed vs guessed. State the clipping
verdict honestly (recoverable or not). Point them at the before/after audition.
List what's quarantined (recoverable) vs deleted, and the open questions
(uncertain roles, reference track for tonal match).

## Pitfalls

- **Don't trust filenames or Gemini classify for close-mic roles** — spectrum for
  close mics, inter-channel correlation for the overhead pair.
- **Different durations / passes are often different songs.** Verify with Gemini
  before collapsing anything; keep distinct songs apart.
- **"Dead here" ≠ "dead everywhere."** Cross-check a channel across all takes
  before deleting it.
- **kit.json file fields need the `.wav` extension** or drum-prep errors
  ("manifest references a file not in dir").
- **drum-prep output is AIFF-in-`.wav`** — convert with `aiff2wav.sh` before any
  ffmpeg step.
- **adeclip overshoots past 0 dBFS** — `declip.sh` renormalizes; don't skip that.
- **Clipping is baked in.** Declip smooths, it doesn't restore. Be honest.
- **Never touch the DAW project / the Logic package.** Triage works on the copy.

## Related

- [[logic-extract]] — the upstream step that produces the raw dump
- [[drum-prep]] — aligns the labeled kit this skill emits (+ [[drum-phase-align]], [[drum-reference-match]], [[drum-audition]])
- [[understand-audio]] — deeper Gemini analysis of any single file
- [[new-track]] — scaffold a durable `projects/<slug>/` once songs are separated
