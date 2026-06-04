# raw-drums

- **Source:** `/Users/ship/Desktop/Raw Stems/` (9-mic drum kit, copied into `stems/`)
- **BPM:** 160 (embedded in the AIFF markers)
- **Format:** 48 kHz / 24-bit AIFF, 292.212 s (4:52)
- **Mics:** Kick In, Kick Out, Snare Top, Snare Bottom, Hi-Hat, Rack Tom, Floor Tom,
  Overhead Mono (1 ch), Stereo Drum Room (2 ch)

## Workflow

`/ff-stems` kit-aware FabFilter channel-finalize → balance to a stereo drum bus.

1. `stems/` — raw copies (Desktop stays pristine)
2. `stems/phase-aligned/` — `drum-prep phase-align` output
3. `chains/` — `plans.json`, `unmask.json`, per-stem FabFilter preset JSONs
4. `mix/` — `<stem>_ffchain.wav` channel-finalized stems + `drum-bus.wav` (balanced, NOT mastered)

Next steps when ready: bus glue (warm-drum-bus) → master-track.
