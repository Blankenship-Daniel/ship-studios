---
description: Render N loudness-matched processing variants for a by-ear pick, optionally ranked by Gemini.
argument-hint: <input.wav> <knob and values>
---

Invoke the **variant-shootout** skill on `$ARGUMENTS`.

`$1` is the input; any remaining args name the knob being swept and its values (e.g. master `target_lufs ∈ {-14, -12, -10}`, or reference-match `strength ∈ {0.75, 0.9}`). The skill spans both servers: render each variant into its own dir (`[L] render-mastered`, or the [[reference-match]] EQ / `drum-prep mix`/`reference-match` for kits), `[L] measure-loudness`/`measure-spectrum` each, build **loudness-matched** A/B WAVs (`[L] render-ab` / `drum-prep audition`), then an optional `[G] compare-audio-files` perceptual rank (needs `GEMINI_API_KEY`). It **judges, it does not decide** — it surfaces the fork with a recommendation and waits; it never auto-promotes a winner or overwrites `mix/` / `masters/`. Cap at 2–4 points (`compare-audio-files` takes 2–10 files). Defer to the skill; present the variant matrix + the A/B paths.
