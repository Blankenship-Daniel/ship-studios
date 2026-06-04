# Ship Studios — Drum Stems

- **Source:** multi-mic drum kit (`~/Desktop/Ship Studios - Drum Stems`): overheads (stereo), room, kick in + beater, snare top + bottom, snare-reverb return.
- **BPM:** ~104 (detected; per-loop measured 103.7–104.1). 4/4.
- **Sample rate:** 48 kHz.

## Processing
1. **Prep** (`drum-prep`): role detect → phase-align close mics to overheads (snare top −0.32→+0.53 corr) → balance-preserving global normalize (−0.483 dB). Snare reverb kept as `fx`, out of alignment.
2. **Mix** (`drum-prep mix`): **feel=dry, perspective=audience** → stereo print. Room −24 dB under the close mics; snare verb folded in at −24 dB. Unprocessed unity sum (crest 25.8 dB).
3. **Master** (`render-mastered`): −14 LUFS target / −1 dBTP ceiling, +0.2 transient shape, 30 Hz HPF → landed **−15.1 LUFS / −1.01 dBTP**, 0 clip (true-peak-limited on peaky material; Apple Music fully compliant, Spotify plays ~−15).
4. **Loops** (`find-loops` @ 104 → clean → seam → master → export): 3× 1-bar stereo loops, ~−14.5 to −15.0 LUFS.

## Layout
- `mix/drums-mix-dry-audience.wav` — the dry/punchy stereo print (+ 12 s excerpt)
- `masters/drums-master-14lufs.wav` (+ `masters/deliverables/` 44k16 · 48k24 · 96k24)
- `loops/drums-104-1bar-{A,B,C}.wav` (+ `loops/deliverables/` 44k16 · 48k24)

## Notes / gotchas hit
- `find-loops` outputs **mono 16-bit** — loops were re-cut **stereo** from the print via the manifest sample offsets.
- `tag-deliverable` / `export-deliverables tag=true` currently **fail to embed** (soundfile `.rewrite.tmp` bug) → tags written manually (RIFF LIST/INFO + `acid` tempo chunk + `.tags.json` sidecar).
- Master could not reach −14 at a −1 dBTP ceiling (crest 25.8). For a louder master, drop the ceiling to −1.5/−2 dBTP or limit harder.
