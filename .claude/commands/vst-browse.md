---
description: Discover which installed VST3/AU plugins you can actually use here (headless-safe), by task.
argument-hint: [search term, e.g. "comp" or a vendor]
---

Invoke the **vst-browse** skill on `$ARGUMENTS`.

`$1` (optional) narrows the search (a task word like "verb"/"eq"/"comp" or a vendor). The skill runs `[L] list-vst-plugins`, filters to the headless-safe set ([`demo/headless-safe-titles.txt`](../../demo/headless-safe-titles.txt)), groups matches by task ([`docs/vst/README.md`](../../docs/vst/README.md)), and flags installed-but-blocked plugins (iLok/UAD/unauthorized). Read-only. Defer to the skill; point the user at the matching `vst-*` skill for each pick.
