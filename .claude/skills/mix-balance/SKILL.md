---
name: mix-balance
description: "Use FIRST whenever you sum stems/mics to a bus, or when an element sits wrong in a mix — 'mix these stems', 'balance the kit', 'set the levels', 'the hi-hat / cymbals / overheads are too loud', 'something's too loud/buried', 'gain-stage the mix', 'why is X dominating'. Sets stem VOLUMES by MEASURED loudness (LUFS) to deliberate per-role targets — the step to do BEFORE any EQ/tone. A balance problem is not an EQ problem. Stemmy MCP / local DSP."
argument-hint: <stems dir or files> [intent, e.g. "kick/snare forward, OH under"]
---

# mix-balance — mix stem volumes by measured loudness (before EQ)

Goal: get the **levels** right by measuring, not by eye. The single most common mixing mistake is
treating a **balance** problem with EQ (or compression, or bleed-cancellation). Set deliberate
per-element volumes by **integrated LUFS** first; only then reach for tone.

## Doctrine (why this skill exists)

- **Measure, don't eyeball.** Set each stem's level by its measured **integrated LUFS** to a target,
  not by a guessed dB or by ear-alone. Engine: `scripts/mix/balance_stems.py`.
- **LUFS, not RMS.** RMS under-reads bright mics — an **overhead reads HOT in LUFS** (mid/high-weighted)
  even when its RMS looks modest. Balancing off RMS is how the overhead ends up secretly the loudest thing.
- **Overheads UNDER the close mics.** The OH carries the cymbals **and the hi-hat**; if it's on top, the
  hat/cymbals dominate. Set kick/snare forward and the OH a few LU *under* them — this controls "too much
  hi-hat" at the source, with no EQ.
- **Don't peak-normalize the sum.** That throws the balance away. Sum the gained stems and leave headroom.
- **A forward close mic amplifies its bleed** — gate/cancel it (`[[bleed-gate]]`) instead of turning it up past the spill.
- **Balance BEFORE EQ.** Re-check tone only after the levels are right; then hand to the tone stage.

## Prerequisites

- `scripts/mix/balance_stems.py` run with the stemmy-loops `mixing` venv
  (`../stemmy-loops-mcp/.venv/bin/python`, has pyloudnorm + soundfile). Or `[L] measure-loudness` per stem.
- Time/phase-aligned stems for a multi-mic kit (run `[[drum-phase-align]]` first).

## Recipe

1. **(Optional) de-bleed** forward close mics first — `[[bleed-gate]]` (gate a spill-heavy mic; or cancel a
   correlated source like the hi-hat out of the overheads). Turning a mic up turns its bleed up too.
2. **Measure** each stem's integrated LUFS (the balancer does this and prints the table; or `[L] measure-loudness`).
3. **Set deliberate per-role targets** — kick/snare forward, **overhead under them**, room/ambience subtle,
   support mics (snare-bottom, kick-beater) low. Pan by perspective.
4. **Balance** —
   ```bash
   ../stemmy-loops-mcp/.venv/bin/python scripts/mix/balance_stems.py \
     '{"out":"projects/<track>/mix/bus.wav","headroom_db":-6,"stems":[
        {"file":"…/overhead.wav","target_lufs":-22},{"file":"…/kick in.wav","target_lufs":-17}, …]}'
   ```
   It applies `gain = target − measured`, pans, sums, and leaves headroom (no sum-normalize). Read the table.
5. **Verify** — re-`[L] measure-loudness`/`measure-spectrum` the bus; confirm the intended element leads and
   nothing dominates. Adjust targets and re-run if not.
6. **Then tone** — hand the balanced bus to `[[finalize-mix]]` / `[[vst-chain]]` / EQ. Not before.

## Outputs

- A balanced stereo bus in `projects/<track>/mix/` + the measured **balance table** (measured → target → gain → pan).

## Reporting to the user

- Show the balance table (each stem's measured LUFS, target, applied gain). Call out anything surprising
  (e.g. "the overhead was the loudest stem at −16.7 LUFS — pulled it −5 dB under the kit").

## Pitfalls

- **Don't EQ a balance problem.** Too much hi-hat = overhead too loud; muddy = something over-level — fix
  the *level* first. EQ is for tone after the balance is right.
- **RMS lies** — measure LUFS. **Don't peak-normalize the summed bus** — it undoes the balance.
- **Forward close mics drag up bleed** — `[[bleed-gate]]` first.

## Related

- `[[drum-mix]]` — the kit-specific mixer (role auto-detect + pan + FX return) — prefer it for a full multi-mic kit
- `[[song-mix]]` — full multi-instrument song from named stems · `[[bleed-gate]]` — de-spill before balancing
- `[[drum-normalize]]` — balance-preserving global gain-stage · `[[finalize-mix]]` / `[[mix-check]]` — tone AFTER balance
