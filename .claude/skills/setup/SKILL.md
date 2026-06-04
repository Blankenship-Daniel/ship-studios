---
name: setup
description: Use when setting up ship-studios or asking about install / sync / extras / env vars / API keys — "how do I set up", "which uv extras do I need", "what env vars / API keys", "sync the servers", "GEMINI_API_KEY / ANTHROPIC_API_KEY", "STEMMY_* / SHIP_STUDIOS_* config", "the model / concurrency / timeout knobs". The index to the setup reference (docs/setup.md); points at the docs, runs no tools. Reference, not a pipeline.
argument-hint: [topic, e.g. "extras" | "env vars" | "api keys"]
---

# setup — install, sync & env-var reference (index)

Goal: answer "how do I get ship-studios running, which `uv` extras, and which env vars matter"
by routing to [`docs/setup.md`](../../../docs/setup.md) — the full extras list + the complete
`STEMMY_*` / `SHIP_STUDIOS_*` env-var table. This is a **documentation index**, not a pipeline:
it never calls a tool. The same facts live in CLAUDE.md's brief "Setup prerequisites" stub;
the full detail is in the doc to keep CLAUDE.md under its char limit.

## Where to look

| The user is asking about… | Where |
|---|---|
| Which **`uv` extras** to sync (loops `mixing`/`vst`/`ml`, gemini bundled) | [docs/setup.md](../../../docs/setup.md) |
| **API keys** — what needs `GEMINI_API_KEY` vs `ANTHROPIC_API_KEY` | [docs/setup.md](../../../docs/setup.md) |
| **Tuning knobs** — model overrides, `*_CONCURRENCY` caps, hub timeouts, `STEMMY_MCP_ALLOWED_ROOTS`, cache controls | [docs/setup.md](../../../docs/setup.md) |
| **Sibling-repo locations** (`SHIP_STUDIOS_LOOPS_DIR` / `_GEMINI_DIR`) | [docs/setup.md](../../../docs/setup.md) |
| A pre-run health check | `ship-studios doctor` (see `[[developing]]`) |

## At a glance

- Two sibling repos: `../stemmy-loops-mcp` (`uv sync --extra loops-mcp --extra mixing`, add `--extra vst`
  for plugin hosting, `--extra ml` for the full superset) and `../stemmy-gemini-mcp` (`uv sync`, no extras).
- **Keys:** `[G]` Gemini perceptual tools + `[L] describe-loops` need `GEMINI_API_KEY`; `[L]` LLM tools
  need `ANTHROPIC_API_KEY`; **pure-DSP measure/render tools need neither** (no key, no network).
- The forwarded env-var table is the hand-maintained mirror of `ship_studios.config.FORWARDED_ENV`;
  `tests/test_docs_env_table.py` gates the sync (a forwarded var undocumented in CLAUDE.md **or**
  docs/setup.md fails CI), so add new vars to the table in docs/setup.md.

## How to use this skill

Identify which setup topic the question is about and quote the relevant figure from
[`docs/setup.md`](../../../docs/setup.md). For "is my environment OK?" point the user at
`ship-studios doctor` (it reads env vars + sibling-repo presence, launches nothing).

## Pitfalls

- **Never hardcode keys.** Use `${GEMINI_API_KEY}` / `${ANTHROPIC_API_KEY}` env expansion (wired in
  `.mcp.json`); keep secrets in the shell env, not on disk.
- **`@import` would re-bloat context.** CLAUDE.md links docs/setup.md as a plain pointer on purpose —
  don't switch it to `@docs/setup.md` (that transcludes the whole file into every session).

## Related

- `[[developing]]` — tests / lint / types / the headless `ship-studios` CLI (the dev counterpart)
- `[[vst]]` — the `vst` extra + plugin-hosting doctrine
- `[[gemini-audio]]` — what the `GEMINI_API_KEY` tools can/can't do
