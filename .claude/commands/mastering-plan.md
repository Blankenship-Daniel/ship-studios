---
description: Design a meter-grounded, typed mastering chain (plan only, no render) from a creative brief or a measure-first proposal.
argument-hint: <near-final-mix.wav> [intent/platform brief]
---

Invoke the **mastering-plan** skill on `$ARGUMENTS`.

`$1` is a near-final stereo mix. With a creative brief (loud/warm/punchy, intensity, platform) the skill uses `[G] master-assistant`; otherwise `[G] recommend-mastering-chain` for a measure-first proposal. It returns a typed chain (EQ/comp/sat/stereo/limiter/expected_lufs) grounded on measured meters — **no audio is rendered**. Defer to the skill; present the chain as concrete moves and hand off to [[master-track]] to render. Needs `GEMINI_API_KEY`.
