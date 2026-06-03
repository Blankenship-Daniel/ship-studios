---
name: tape-j-37
description: "Use when running the Arturia Tape J-37 — the neural-modeled Studer J37 valve tape machine (Abbey Road / Sgt. Pepper) — for tape warmth, glue, saturation, or vintage color on drums, bus, vocals, or a mix: 'Tape J-37', 'Arturia tape', 'Studer J37', 'that Beatles/Sgt Pepper tape sound', 'add tape with the J-37', 'use the J-37 on my drums'. CRITICAL: this plugin does NOT render headless in the ship-studios pipeline (measured passthrough) — it is DAW-only; the skill teaches how to dial it in the DAW, hand the bounce back to the pipeline, and which headless tape to use instead. The plugin-specific deep-dive of [[vst-saturate]], grounded in the real param surface + the passthrough proof in docs/vst/tape-j-37.md."
---

# tape-j-37 — drive the Arturia Tape J-37 (Studer J37) tape machine

The plugin-specific, measured version of [[vst-saturate]] for the **Arturia Tape J-37** — a neural-modeled
emulation of the **Studer J37** 1″ 4-track valve recorder (Abbey Road / *Sgt. Pepper*). Full field guide —
real param surface, the COLOR modes, the levers, recipes, the J37 history, and our own passthrough measurement —
lives in [`docs/vst/tape-j-37.md`](../../../docs/vst/tape-j-37.md). This skill is the workflow; pull the doc for
the *why* and the settings tables.

## The governing facts (read first)

1. **It does NOT render in the headless pipeline on this rig — it passthroughs.** Measured: the plugin loads
   and accepts every parameter, but the DSP never engages. A 1 kHz sine at **drive 50 / Color4** came out at
   **0.00 % THD**; `output_level_db=−24` → no level change; `noise_db=+20` → no noise; `+15 dB` low-shelf → no
   spectral change; **drive 0 ≡ drive 40 ≡ Bypassed, bit-for-bit**. Arturia's ASC licensing self-bypasses in an
   unattended no-GUI subprocess. **Never run it through `apply-vst-chain` / the `[[vst-preset]]` harness as a tape
   stage — you will ship an unprocessed copy and a false `changed:true`.** (That's why there is deliberately **no
   `presets/vst/tape-j-37-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Dial it on the channel/bus (the screenshot shows
   exactly this), **print/bounce to WAV**, drop into `projects/<track>/`, then measure / loop / master with the
   pipeline. The plugin is the *creative* tape stage; ship-studios is *measurement + delivery*.
3. **For a tape stage inside the pipeline, use a verified-headless option** instead: [[studer-a800]] (punchy
   multitrack), [[ampex-atr-102]] (glossy 2-bus/master), IK `Tape Machine 80/440/99/24`, `UAD Oxide Tape`, or
   pure-DSP `[L] saturate-loop`.
4. **Meters own tone** (Gemini hears mono): verify with `[L] measure-spectrum` / `measure-loudness` /
   `measure-stereo` / `check-clipping`. ST Offset widens → **always check mono correlation**.
5. **It's a Studer, not an Ampex** (the "Ampex Tape J-37" in the title is a misnomer). For an Ampex master tape
   that renders headless → [[ampex-atr-102]].

## Decision: where am I being asked to use it?

- **"Apply the J-37 to this WAV in the pipeline" / a headless render** → you **cannot** with this plugin.
  Say so plainly, then offer the substitute: [[studer-a800]] / [[ampex-atr-102]] / `saturate-loop`, or the
  DAW hand-off below. Do **not** silently swap — tell the user the J-37 passthroughs headless and what you'll
  use instead.
- **"How do I dial the J-37 / what settings" / they're working in the DAW** → give DAW settings from the
  doc's §4 + decision table, then the bounce→measure loop (below).

## Recipe (DAW hand-off — the way this plugin works here)

1. **Pick a starting point** by goal from [`docs/vst/tape-j-37.md`](../../../docs/vst/tape-j-37.md) §2–§4:
   - **Warm drum bus / glue (default):** `Color2 (SM911 / American-NAB) · 15 IPS · Vintage · Drive ~12–15
     (auto-gain on) · ST Offset off until mono-verified · Noise/Instability off · Delay off`.
   - **Fat / vintage drums:** `Color3 (aged SM468) · 7.5 IPS · Vintage · moderate Drive`.
   - **Transparent bus glue:** `Color1 (SM911 / European-CCIR, leanest) · 15 IPS · low Drive · ST off`.
   - **Saturation without tape EQ:** any Color · **Modern** mode · Drive to taste.
   - **Dirty / lo-fi FX:** `Color4 (over-biased SM468) · 7.5 IPS · high Drive` + Noise/Instability.
   - Remember: **Drive defaults to 15 (already saturating)**; auto-gain means you must A/B loudness-matched.
2. **Dial + print in the DAW**, then **bounce/print the channel or bus to a 24-bit WAV**. Drop it into
   `projects/<track>/mix/` (or `stems/`).
3. **Measure the bounce** (the "after"): `[L] measure-spectrum` (warmer = centroid/tilt **down**; a 2–5 kHz
   **rise** = overdriven, pull Drive back), `measure-loudness` (crest dropped a little = glue, not squash),
   `measure-stereo` (ST Offset → correlation / mono-sum loss — reject if mono collapses), `check-clipping`.
4. **A/B loudness-matched:** `[L] render-ab` dry vs the tape bounce; optionally `[G] compare-to-reference` on the
   matched pair for a perceptual read. Confirm it's better, not just louder.
5. **Continue the pipeline** — [[loops-to-deliverables]] / [[master-track]] / [[finalize-mix]] as normal.

## (Optional) prove the passthrough yourself

If unsure the plugin still passthroughs (e.g. on another machine, or after an Arturia update), screen it with
[[vst-verify]] — the decisive test is a **1 kHz sine at high Drive → `[L] measure-distortion`**: ~0 % THD = it's
passing audio through (do not use it as tape); several % THD = it's actually saturating (re-enable it). A bare
`changed:true` or an LUFS delta is **not** sufficient proof for a tape unit.

## Outputs

- A DAW recipe (Color / Speed / Modern / Drive / ST Offset) + the measured before→after on the **bounce**
  (centroid / tilt / crest / mono correlation). **No** `projects/.../mix/` render is produced *by the pipeline*
  for this plugin — the render comes from the user's DAW bounce.

## Reporting to the user

Lead with the constraint if relevant: **"Tape J-37 doesn't render through the headless pipeline (verified
passthrough) — dial it in your DAW and bounce, or I'll use [[studer-a800]]/[[ampex-atr-102]]/`saturate-loop`
instead."** Then give the settings, and once there's a bounce, the before→after **centroid / tilt / crest /
mono correlation** with an honest loudness-matched A/B.

## Pitfalls

- **Don't headless-render it** — `apply-vst-chain` returns an unprocessed copy + latency, `changed:true` lies.
- **Auto-gain hides Drive** — judge loudness-matched, never by level.
- **ST Offset ON by default widens** — mono-fold landmine; `measure-stereo` and disable for mono material.
- **Overdriven = harsh** (esp. Color4) — cure is less Drive / leaner Color (Color1) / Modern mode, not EQ.
- **Set levels before tape** ([[mix-balance]]); tape is glue + tilt, not balance or surgery.

## Related

- [`docs/vst/tape-j-37.md`](../../../docs/vst/tape-j-37.md) — the full field guide (param surface, passthrough proof, COLOR modes, history, recipes)
- [[vst-saturate]] — the generic tape/harmonic-color skill this specializes · [[vst-verify]] — prove render-vs-passthrough (the sine→THD test that caught this)
- [[studer-a800]] — punchy headless multitrack tape (the in-pipeline substitute) · [[ampex-atr-102]] — glossy headless 2-bus/master tape
- [[vst-chain]] / [[vst-preset]] — the headless render backbones (which this plugin is **not** safe for) · [[vst-browse]] — re-scan the headless-safe inventory
- [[finalize-mix]] — the glue stage a tape bounce slots into · [[loops-to-deliverables]] / [[master-track]] — where the bounce goes next
- [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak/stereo for tape moves
