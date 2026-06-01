---
name: excite
description: Use when a mix/stem is dull, lacks air or presence, and a static EQ shelf would just raise hiss — "add air to the top", "it sounds dull/dark/flat", "give the vocal presence/forwardness", "open up the highs", "needs sparkle/sheen without getting harsh", "the cymbals have no shimmer". Band-limited parallel harmonic excitement that generates air/presence from the material itself, with a 5–7 kHz harshness guard. Pure DSP, no API key. Stemmy MCP.
---

# Excite — band-limited parallel harmonic air / presence

Goal: add perceived air (top-end sheen) or presence (forwardness) to a dull
file by generating harmonics *from the material itself* and blending them in
parallel — instead of a static high-shelf, which lifts the noise floor and hiss
right along with the music. `[L] excite-loop` band-passes the target band,
oversamples + waveshapes it to spawn harmonics, DC-blocks, and mixes it back.
It reports the harmonic energy added and a 5–7 kHz guard delta so you can catch
harshness creep.

The overlap trap: a tonal **shelf/bell** (`apply-eq`) boosts what's already
there (and the hiss); excitement **creates** new harmonic content. If the file
is *harsh*, that's the opposite job — `[[de-harsh]]`.

## Prerequisites

- `stemmy-loops` up. `[L] excite-loop` / `measure-spectrum` are pure DSP, no key.
- Input is **one stereo WAV** (mix, bus, or stem) — not loop-only despite the
  schema wording.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-spectrum {path}`. Note the top octave (air) or
   1–3 kHz (presence) and the 5–7 kHz region (the harshness watch zone).
2. **Excite** — `[L] excite-loop {path, out_path, band: "air"|"presence",
   drive_db: 12, mix: 0.3, model: "tanh", oversample: 4}`. `air` = 6–16 kHz
   sheen, `presence` = 1–3 kHz forwardness; or set custom `low_hz`/`high_hz`.
   Keep `mix ≈ 0.3` and oversample ≥4 to suppress aliasing. `tape` model adds
   even-harmonic warmth; `soft_clip` is more aggressive.
3. **Confirm** — read back the harmonic energy added + the **5–7 kHz guard
   delta**, then re-run `[L] measure-spectrum`. The target band should open up;
   the 5–7 kHz guard should not run away (that's harshness creeping in).

## Outputs

- Excited file → `projects/<track>/mix/`.

## Reporting to the user

Lead with the **harmonic energy added** in the target band and the **5–7 kHz
guard delta** (the harshness check). State the band, drive, and mix used.
Confirm it added air/presence without tipping into harsh.

## Pitfalls

- **Keep `mix` modest.** High blend or drive turns sheen into harsh fizz —
  watch the 5–7 kHz guard delta.
- **Oversample ≥4.** Low oversampling aliases the generated harmonics into ugly
  inharmonic tones.
- **Don't excite a noisy source naively.** It generates harmonics from whatever
  is in the band, including hiss — clean first if the noise floor is high
  (`clean-loop` with `declick=false` on percussive material).
- **Harsh, not dull?** Use `[[de-harsh]]` — excitement is the wrong direction.

## Related

- [[de-harsh]] — the opposite move when the result (or source) is harsh
- [[mix-check]] — diagnose whether the dullness is tone, balance, or air
- [[master-track]] — a touch of air often belongs in the master, gently
- [[vst-saturate]] — the plugin form of harmonic enhancement
