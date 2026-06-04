# Setup prerequisites & environment variables

Setup and configuration reference for ship-studios. The contract (tool surface, pipelines, rules) lives in [`CLAUDE.md`](../CLAUDE.md); this is the "look it up when you need it" detail.

Both servers are sibling repos using `uv`. Sync each in its own directory before first use.

## `../stemmy-loops-mcp`

```bash
# Minimal — MCP server + DSP mix/master measurement & render tools:
uv sync --extra loops-mcp --extra mixing

# VST hosting — add the `vst` extra to run third-party VST3/AU effect plugins (apply-vst-chain):
uv sync --extra loops-mcp --extra mixing --extra vst

# Or the convenience superset (separate + embed + classify + quantize + viz + llm + listen + beats):
uv sync --extra loops-mcp --extra mixing --extra ml
```

Extras: `loops-mcp` → the MCP server · `mixing` → loudness/render/AB tools · `llm` → `diagnose/ask/suggest/caption-loops/analyze-loops` LLM flags · `listen` → `describe-loops` (Gemini) · `separate` → `extract-drums` + `find-loops separate=true` · `classify` → hit tagging · `quantize` → `quantize-loop` · `beats` → deep beat tracker · `viz` → debug plots · `embed` → CLAP loop/bar embeddings · `vst` → `apply-vst-chain` (`list-vst-plugins` needs no extra) · `ml` → superset of all of the above.

## `../stemmy-gemini-mcp`

```bash
uv sync   # no extras — all deps bundled
```

## Environment variables

| Var | Needed by |
|---|---|
| `ANTHROPIC_API_KEY` | `[L]` LLM tools (`diagnose-output`, `ask-about-output`, `suggest-approach`, `caption-loops`, `analyze-loops` w/ llm flags) |
| `GEMINI_API_KEY` | `[G]` Gemini perceptual tools + `[L] describe-loops` |
| `STEMMY_LLM_MODEL` / `STEMMY_LLM_CAPTION_MODEL` | optional `[L]` model overrides |
| `STEMMY_MCP_MODEL` | optional `[G]` Gemini model override (default `gemini-3.1-pro-preview`) |
| `STEMMY_LISTEN_MODEL` | optional `[L] describe-loops` Gemini override. **Separate from `STEMMY_MCP_MODEL`** — to move *every* Gemini read off the default set this **alongside** it (the footgun: changing only `STEMMY_MCP_MODEL` leaves `describe-loops` on the old model) |
| `STEMMY_MCP_THINKING_LEVEL` / `STEMMY_MCP_THINKING_BUDGET` | optional `[G]` per-call thinking-tier override (else a per-tool default tier: high for verdict/critique, low for cheap tags) |
| `STEMMY_MCP_MODEL_CONCURRENCY` | optional `[G]` cap on concurrent Gemini **model** calls (default `3`) — throttles a fan-out so it doesn't trip the 429 per-minute quota |
| `STEMMY_LOOPS_DSP_CONCURRENCY` | optional `[L]` cap on concurrent pure-DSP offloads in the batch tools; default `min(cpu, 4)` |
| `STEMMY_MCP_ALLOWED_ROOTS` | optional `[G]` filesystem allow-list — OS-path-separator-delimited absolute roots. The Gemini server enforces it (each input path is `resolve()`d and must be a child of an allowed root); the hub passes paths through unmodified. Unset = unrestricted local use |
| `SHIP_STUDIOS_LOOPS_DIR` / `SHIP_STUDIOS_GEMINI_DIR` | optional sibling-repo overrides (auto-resolved from the main checkout incl. worktrees); set only for a non-standard layout |
| `SHIP_STUDIOS_STARTUP_TIMEOUT` / `SHIP_STUDIOS_CALL_TIMEOUT` | optional **hub** timeouts (s): handshake budget (default `120`) and per tool-call budget (default `600`); `0` disables. A `CALL_TIMEOUT` fire abandons the client's *wait* but does NOT abort server-side work (no cancellation sent) — set generously for heavy tools (Demucs, Gemini renders) |
| `SHIP_STUDIOS_ARTIFACTS_DIR` / `SHIP_STUDIOS_PROJECTS_DIR` | optional **hub** path overrides (default `<repo>/artifacts`, `<repo>/projects`) |
| `STEMMY_CACHE_DIR` / `STEMMY_NO_CACHE` | optional `[L]` disk-cache controls for `separate`/`embed`/`classify` (`stemmy/_diskcache.py`); `STEMMY_NO_CACHE=1` to disable |

Pure-DSP measurement/render tools on **either** server need no env vars and no network. Set keys only when reaching for a Gemini/LLM tool.
