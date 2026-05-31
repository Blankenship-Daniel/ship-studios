---
description: Copy the raw, pre-processing recordings out of a Logic Pro project package (organized by take, package untouched).
argument-hint: <path/to/Project.logicx>
---

Invoke the **logic-extract** skill on `$ARGUMENTS`.

`$1` is the `.logicx` project package (or project folder). The skill copies the
original per-input recordings out of `<project>/Media/Audio Files/` into
`artifacts/<slug>-raw/`, organized by take (`#NN` pass → `take-NN/`), underscoring
names and setting aside Logic `merged` fragments — **without mutating the package**
(it's the master). Filesystem + read-only `afinfo`/`soxi` only; NO MCP tools.
First clarify whether the user wants the raw source captures (this skill) or the
edited timeline result (a Logic "All Tracks as Audio Files" export — a UI action).
Then hand off to [[multitrack-triage]].
