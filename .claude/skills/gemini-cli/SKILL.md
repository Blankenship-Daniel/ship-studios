---
name: gemini-cli
description: Use when the user wants to drive Google's standalone `gemini` terminal CLI (the @google/gemini-cli npm binary) non-interactively for text/codebase queries or scripting — "run the gemini cli", "gemini -p / headless gemini", "pipe a file into gemini", "gemini cli vs the gemini MCP tools". The shell CLI for ad-hoc text/codebase Q&A — SEPARATE from this repo's stemmy-gemini `[G]` audio tools. Reference, not a pipeline; it touches no audio.
argument-hint: [topic, e.g. "headless -p" | "json output" | "trust gate" | "vs the MCP tools"]
---

# gemini-cli — drive the standalone `gemini` terminal CLI headless

**Goal:** explain how to run Google's `gemini` shell binary in **non-interactive / headless** mode for one-shot text & codebase queries and scripting. This is the **terminal CLI agent**, NOT this repo's audio path. **It is SEPARATE from the `stemmy-gemini` `[G]` MCP audio tools** (`transcribe-audio`, `analyze-mix-balance`, `mastering-feedback`, …) which run inside a Python stdio subprocess via the `google-genai` SDK and take **WAV file paths**. The shell `gemini` binary does **text/codebase Q&A** from your shell; it touches no audio and is reached by no skill/pipeline in this repo. For any audio-analysis ask, route to **[[understand-audio]]** / **[[gemini-audio]]** instead.

## At a glance

- **Binary:** `/opt/homebrew/bin/gemini` → symlink to `../lib/node_modules/@google/gemini-cli/bundle/gemini.js` (the bundled JS entrypoint, not a package dir). Package `@google/gemini-cli`, version **`0.45.0`** on this machine. Installed/updated via npm — **does NOT touch the repo's audio path** (`uv sync` in the sibling servers), and the servers' setup does not install this CLI.
- **Default is INTERACTIVE.** The headless switch is **`-p`/`--prompt`** — it runs the prompt and exits. `-i`/`--prompt-interactive` runs the prompt then stays interactive; a bare positional query also defaults to interactive. **Only `-p` is headless.**
- **STDIN is appended to `-p`.** `cat file.log | gemini -p 'summarize this'` works — the file content is fed in alongside the prompt.
- **Output format:** `-o text` (model text only) · `-o json` (one JSON object: top-level `response` is the answer, plus `session_id`, `tools`, `files`, and `stats`; `stats.models.<model>` carries `tokens`/`api`/`roles`) · `-o stream-json` (incremental events; ⚠️ unverified here).
- **Model:** `-m <id>`. CLI default in this build = **`gemini-3-flash-preview`**. (The MCP audio path defaults to **`gemini-3.1-pro-preview`** via `STEMMY_MCP_MODEL` — different surface, different default, **same `GEMINI_API_KEY`**.)
- **Auth:** uses **`GEMINI_API_KEY`** when set — the reliable headless/CI path (already set in this env). Interactive mode also supports Google login; Vertex/other modes ⚠️ unverified.
- **Auto-retries on quota/capacity when they occur** (lines go to stderr); the final stdout stays clean.
- **Mono caveat is irrelevant here** — this CLI does no audio. The Gemini-hears-mono rule (meters own loudness/peak/stereo) lives in the MCP audio tools, not in this binary.

### Canonical headless recipes (verified shapes)

```bash
# One-shot text (stdout = just the answer):
GEMINI_CLI_TRUST_WORKSPACE=true gemini -p 'PROMPT' -o text

# JSON + jq (parse the answer):
GEMINI_CLI_TRUST_WORKSPACE=true gemini -p 'PROMPT' -o json | jq -r '.response'

# Feed a file (stdin is appended to -p):
cat file.txt | GEMINI_CLI_TRUST_WORKSPACE=true gemini -p 'summarize this' -o text

# Robust scripting: keep only stdout; warnings/retries/trust-refusal go to stderr; check $?:
GEMINI_CLI_TRUST_WORKSPACE=true gemini -p 'PROMPT' -o text 2>/dev/null   # 0 = ok, 55 = trust refusal
```

## How to use this skill

This is a **reference**: it points at the `gemini` binary's headless surface and disambiguates it from the repo's audio tools — it runs no chain.

- **Want a quick text/codebase answer from the shell, or to script Gemini?** Use the recipes above. Always `-p` (headless), prefer `-o json | jq -r '.response'` for scripts, and **always export `GEMINI_CLI_TRUST_WORKSPACE=true`** so the trust gate can't silently block you.
- **Want to ANALYZE audio (transcribe, critique a mix, master, compare to a reference)?** This CLI can't — go to **[[understand-audio]]** (perceptual recon) or the **[[gemini-audio]]** suite. Those use the `stemmy-gemini` `[G]` MCP server, not this binary.
- **Wondering what Gemini can hear / which model/limit/price applies to audio?** That's **[[gemini-audio]]** / **[[gemini-audio-understanding]]**, not this CLI.

## Pitfalls

- **The trust gate is the #1 automation gotcha — and it fails LOUD-to-stderr, SILENT-to-stdout.** In an untrusted dir (when `security.folderTrust.enabled` is on), `-p` REFUSES: **stdout is empty, the refusal text goes to stderr, and the exit code is `55`** (the underlying `FatalUntrustedWorkspaceError`). A script reading only stdout sees nothing and may think it "worked." Fix: **export `GEMINI_CLI_TRUST_WORKSPACE=true`** (preferred for CI/scripts) or pass `--skip-trust`. Don't rely on the dir resolving as trusted — always set the env var.
- **Always capture stdout separately and check the exit code.** Warnings (`MCP issues detected. Run /mcp list for status.`), quota auto-retry lines, and the trust refusal **all go to stderr**; `-o text` stdout is the clean answer. Script with `2>/dev/null` + `echo $?` (**0 = ok, 55 = trust refusal**).
- **Don't confuse this with the repo's `[G]` audio tools.** The `stemmy-gemini` perceptual tools (`transcribe-audio`, `mastering-feedback`, `detect-mix-issues`, …) are **NOT** reached by shelling out to `gemini` — they run via the `google-genai` SDK inside an MCP subprocess (`uv --directory ../stemmy-gemini-mcp run`) and take WAV paths. Never substitute one for the other.
- **Default mode is interactive — a bare query or `-i` will hang a script.** Use **`-p`** for headless. Per `--help`, `-i`/`--prompt-interactive` continues in interactive mode after the prompt (so it will hang a non-interactive script).
- **The model defaults differ across surfaces.** CLI = `gemini-3-flash-preview` (override with `-m`); MCP audio = `gemini-3.1-pro-preview` (override with `STEMMY_MCP_MODEL` / `STEMMY_LISTEN_MODEL`). Same key, independent selection — don't assume a CLI `-m` change affects the audio tools or vice-versa.
- **`--allowed-tools` is DEPRECATED** (help says use the Policy Engine / `--policy`). For autonomy, `-y`/`--yolo` auto-accepts tool actions and `--approval-mode plan` is read-only — but runtime tool behavior here is ⚠️ unverified; don't promise it without testing.
- **`-o stream-json` and session flags (`-r`/`--resume`, `--session-id`, `--list-sessions`) are ⚠️ unverified on this machine** — present in `--help`, not exercised. Verify before scripting against their exact shape.
- **Subcommands (`gemini mcp`/`extensions`/`skills`/`hooks`/`gemma`) are management, not the query path.** Headless querying is `gemini -p`, never a subcommand.

## Related

- [[understand-audio]] — the recon step for actual audio (transcribe / region / events / classify / compare) via the `[G]` MCP tools; use this, NOT the shell CLI, for any audio ask.
- [[gemini-audio]] — index to the Gemini *audio* capability suite (what Gemini can hear, models/limits/price); the audio counterpart this CLI must not be confused with.
- [[gemini-audio-understanding]] — the audio-IN reference (token cost, formats, the mono caveat, file/duration limits) for the wired `[G]` understanding tools.
- [[gemini-speech-generation]] — Gemini TTS (one-shot speech files); reference only, not wired here.
- [[gemini-live-audio]] — the Live API (real-time streaming voice); reference only, not wired here.
- [[gemini-music-generation]] — Lyria music generation; reference only, not wired here.
