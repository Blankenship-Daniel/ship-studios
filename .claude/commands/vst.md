---
description: VST plugin suite index — route to the right vst-* skill + the headless-safe doctrine.
argument-hint: [what you want to do]
---

Invoke the **vst** skill (suite index) for `$ARGUMENTS`.

The skill maps the request to the right `vst-*` skill (channel-strip, eq, compress, saturate, reverb, delay, de-ess, master, amp) or `[[vst-chain]]` for a freeform chain, and states the doctrine: headless-safe plugins only ([`docs/vst/README.md`](../../docs/vst/README.md)), measure before/after, `dump_state:true`, opt-in & non-deterministic. Defer to the skill; if the user already named a task, hand straight to that `vst-*` skill.
