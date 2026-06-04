# adat-kit-02

- **Source:** `~/Desktop/Raw Stems/` — 7 channels, take `#02`
- **Format:** 48 kHz / 24-bit, 366.628667 s (one simultaneous performance; drums enter ~82 s)
- **Job:** `/ff-stems` — kit-aware FabFilter channel-finalize (Pro-Q4 → Pro-MB → Pro-C2 → Pro-L2)
- **Scope:** channel-finalize stems only (no bus, no master). Outputs sit quiet by design (no makeup).

## Channel → role (Gemini-verified + measurement)

| src | role | notes |
|---|---|---|
| B ADAT 1 | kick_in | sub/boom mic, centroid ~73 Hz |
| B ADAT 2 | kick_beater | click/attack mic, partner of kick_in (locks +72 samp @0.85) |
| B ADAT 3 | tom (rack) | ~193 Hz / G3 ring |
| B ADAT 4 | snare_top | body + crack |
| B MIC_LINE_HIZ 1_2 | overhead | stereo kit-image reference (DARK, little air) |
| A ADAT 1 + A ADAT 2 | **EXCLUDED — vocals + click track** | stereo vocal/dialogue source, not drums (Gemini-ID on the drum-silent intro) |

No dedicated hi-hat mic.

## What happened
- **ADAT-vs-MIC_LINE converter offset (~880–1000 samp / ~19 ms)** broke drum-prep's default phase-align
  (`max_lag 600` railed). Re-aligned via `drum_prep.dsp.align_to` on a clean 150–170 s window at `max_lag 1500`;
  verified on an independent window (tom→OH +0.57, snare→OH +0.48, kick pair +0.75). See [[adat-micline-converter-offset]].
- Per-stem plans authored by a 5-agent fan-out (each measured its aligned stem). Cross-stem cession (OH → close mics)
  folded into the OH plan (no separate unmask.json).
- KIT mode: all 5 chains impulse-verified at **uniform 2112-samp latency** → alignment survives the EQ.

## Results (before → after)

| stem | LUFS | true-peak dBTP | crest | centroid Hz | move |
|---|---|---|---|---|---|
| kick_in | −23.0→−23.1 | −1.07→−3.16 | 22.8→23.7 | 75→83 | 26 Hz HPF + Pro-MB low evens sub |
| kick_beater | −22.4→−22.9 | −1.01→−3.74 | 22.2→23.3 | 332→507 | 40 Hz HPF, −1.8@315 de-box, +2@5k click |
| snare_top | −25.1→−27.0 | −1.06→−3.09 | 29.3→31.4 | 1386→1529 | 90 Hz HPF, −2@450 de-box, +1.5@4k crack, dyn de-harsh 6k |
| tom | −26.0→−29.7 | −1.09→−2.80 | 29.4→34.4 | 396→1010 | 80 Hz HPF, **dyn −4@200 + Pro-MB 120–350 (strong ring-tame)** |
| overheads | −26.4→−31.7 | −0.97→−6.14 | 31.1→32.4 | 231→539 | **140 Hz HPF (cedes lows 42%→1.7%)**, −2.5@200, +2@11k air, width kept |

Verified: floor-safe (out LUFS ≤ in, no makeup), TP ≤ −1 dBTP, crest preserved/up, latency uniform, strong inter-mic
pairs preserved. `snare↔tom` coherence flag = EQ/bleed confound (proven benign: preserved in gutted + untouched bands).

**Caveats:** tom + overheads got the strongest (doctrine-correct) reshaping — dial back if thin. Close mics are now
dual-mono stereo (harmless; center on sum). Pro-MB snaps: kick low-xover 20→30 Hz, releases →100 ms.

## Outputs
- `stems/` — role-named source WAVs + `kit.json`
- `stems/phase-aligned/` — aligned set (the foundation)
- `chains/*.json` — reproducible presets · `plans.json`
- `mix/<stem>_ffchain.wav` — **channel-finalized stems** (the deliverable)

## Next (downstream, separate stages)
Re-level by measured LUFS: [[mix-balance]] / [[drum-mix]] → optional [[warm-drum-bus]] → [[master-track]] → [[delivery-qc]].
