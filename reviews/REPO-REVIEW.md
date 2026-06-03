# ship-studios Repo Review

**Date:** 2026-06-03 · **Branch:** `main` · **Worktree:** `.claude/worktrees/hazy-dazzling-dewdrop`

## Executive summary

This review covered the full ship-studios repo: the DSP-free MCP-client hub (`ship_studios/`), the local multi-mic DSP package (`drum_prep/`), the test suite, and the documentation surface (CLAUDE.md, README.md, `docs/`, `.claude/skills/`). The most impactful confirmed findings are a small cluster of `drum_prep` DSP/role-handling bugs — FX stems leaking into phase alignment (both the selector and its validation gate) and a non-equal-power stereo pan that injects an unintended loudness boost — plus several CLI input-validation gaps and a documentation drift cluster (a dangling `[[gemini-mastering-feedback-cross-check]]` wikilink, "six pipelines" vs the five async functions actually defined, and a missing `dry` feel option). No critical findings. The DSP numerics issues are the ones worth fixing first because they silently corrupt output rather than failing loudly. Two findings are disputed and need a human call (control-flow guards may already prevent the described bug). Note: the two sibling MCP servers (`stemmy-loops`, `stemmy-gemini`) were absent from this worktree, so all findings derive from static reading of this repo's own code/docs — nothing was exercised against a live server.

### Severity totals

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 4 |
| Medium | 15 |
| Low | 17 |
| Nit | 9 |
| **Disputed** | **2** (counted within the above) |

---

## Code Review

### [HIGH] FX stems can be included in `partner_pairs` despite not being phase-aligned

`drum_prep/kit.py:280`

```python
for s in kit.stems:
    if s.ambience or s.role == Role.ROOM:
        continue
    anchor = kit.by_name(s.partner)
    if anchor is not None:
        out.append((s, anchor))
```

**Why:** `partner_pairs()` skips ambience/room stems (they're processed separately) but does *not* skip FX stems. FX (effect returns) are documented as "excluded from alignment; handled only at the mix stage as returns" and are explicitly filtered out of `anchored_to_oh()` (line 296). If a user assigns a `partner` to an FX stem in `kit.json`, it silently flows into `partner_pairs()` and gets phase-aligned in `phase_align.py` (read → align → write), corrupting the return. The misconfiguration raises no error.

**Fix:** Add FX to the skip condition: `if s.ambience or s.role == Role.ROOM or s.role == Role.FX:`.

---

### [HIGH] Validation doesn't prevent FX stems from having partners

`drum_prep/kit.py:227`

```python
if s.partner and (s.ambience or s.role == Role.ROOM):
    problems.append(f"{s.name!r} is ambience/room but names a partner ")
```

**Why:** The companion gap to the finding above. `_validate()` flags ambience/room stems that name a partner, because those stems are processed separately. The identical reasoning applies to FX (also excluded from alignment), but the check omits `Role.FX`, so an FX+partner misconfiguration passes validation silently and then mis-routes into `partner_pairs()`. (Adversarial verification downgraded the practical severity to MEDIUM: it requires explicit user error, the impact is configuration-level, and FX returns are rarely given partners — but the original unit logged it HIGH.)

**Fix:** Extend the check to `if s.partner and (s.ambience or s.role == Role.ROOM or s.role == Role.FX):` and update the error message to mention FX. Pair with the `partner_pairs()` fix above.

---

### [HIGH] Stereo stem balance does not preserve loudness when panning

`drum_prep/stem_mix.py:69`

```python
ch = ch * np.array([1.0 - max(0.0, pan), 1.0 - max(0.0, -pan)])
```

**Why:** This balance formula is not equal-power and violates loudness conservation, unlike the `_pan()` helper used for mono stems. After a stereo stem is gained to its target LUFS (line 62), this linear scaling changes its loudness whenever `pan != 0`: at `pan=0.5` total power becomes 1.25 (a +0.97 dB unintended boost), deviating further as pan increases. This breaks the function's stated "balance every stem to target_lufs" contract — the mix gains loudness as stereo stems are panned. No test verifies loudness preservation under panning.

**Fix:** Apply an equal-power pan law to stereo stems so `L² + R²` stays constant across pan positions (mirror the `_pan()` approach, scaled for a stereo source).

---

### [HIGH] Error-message construction can raise an uncaught `KeyError` if `server_key` is invalid

`ship_studios/mcp_client.py:102` — **status: DISPUTED** (see Disputed section for full detail)

```python
f"(uv --directory {config.server_dir(server_key)} run …). "
```

**Why (as filed):** Inside the `except TimeoutError` block, `config.server_dir(server_key)` is called in an f-string. An invalid `server_key` makes `server_dir()` raise `KeyError`, which escapes the handler and masks the intended `TimeoutError`, surfacing a confusing error instead of the helpful timeout message. One reviewer refuted this: line 86 calls `config.server_parameters(server_key)` *before* the try block, which validates the key, so reaching line 102 implies a valid key. Adjusted severity MEDIUM. Listed here because the unit's filed severity was HIGH; treat as needs-judgment.

**Fix (if accepted):** Resolve the directory path before the `try` block, or guard with a fallback for unknown keys.

---

### [MEDIUM] Bare `except Exception` without exception-type logging masks failures

`drum_prep/qc.py:172`

```python
except Exception:
    data = {}
    sidecar_corrupt = True
```

**Why:** The bare handler swallows `JSONDecodeError`, `PermissionError`, `FileNotFoundError`, `UnicodeDecodeError`, etc. without distinguishing or logging them, so operators see only a binary "corrupt" flag and can't tell *why* a sidecar failed. (Adversarial verification downgraded from HIGH to MEDIUM: the failure is *not* fully masked — `sidecar_corrupt=True` is returned and surfaced by `verify_dir()` as a `corrupt_sidecars` list, and the behavior is documented intent. The real weakness is the missing root-cause detail / logging, not a silent drop.)

**Fix:** Catch specific exception types and log, e.g. `except json.JSONDecodeError: logger.warning(...); sidecar_corrupt = True`, or at minimum `except Exception as e: logger.warning(f"failed to read {sidecar}: {e}"); sidecar_corrupt = True`.

---

### [MEDIUM] Input audio files lack `exists=True` validation in `click.Path()`

`ship_studios/cli.py:182`

```python
@click.argument("mix_path", type=click.Path())
```

**Why:** The five pipeline commands accept audio inputs without upfront existence checks (lines 182 master, 236/237 mix-check, 266/267 reference-match, 299 loops, 368 understand). Paths flow straight to `hub.call_tool(...)`, so users discover a missing file only after MCP server startup and handshake instead of immediately at argument parse. Optional config files (`--eq-json`, `--compare-schema`) already validate, confirming the pattern is known but not applied to audio inputs.

**Fix:** Add `exists=True` (and `dir_okay=False`) to `click.Path()` for all audio input arguments.

---

### [MEDIUM] Optional comparison/schema file paths lack `exists=True` validation

`ship_studios/cli.py:381`

```python
@click.option("--compare", "compare_paths", multiple=True, type=click.Path())
```

**Why:** `--compare`, `--compare-schema`, and `--json-schema` accept paths without upfront existence checks, inconsistent with `drum_prep/cli.py` which uses `exists=True` for similar options. Note: `--compare-schema`/`--json-schema` are partly protected because `_load_json_obj()` catches `FileNotFoundError` before server startup; `--compare` has zero pre-validation and is the true gap.

**Fix:** Add `exists=True, dir_okay=False` to lines 381, 385, 389.

---

### [MEDIUM] CLI path arguments accept arbitrary paths (traversal / symlink) without bounds

`ship_studios/cli.py:182` (security)

```python
@click.argument("mix_path", type=click.Path())  # + ~17 similar click.Path() decls
```

**Why:** All 18 `click.Path()` declarations omit validation flags, so `../` traversal or symlinks to sensitive files pass through to the MCP servers unchecked. This is a defense-in-depth concern for scripted/automated invocation from untrusted input; for an interactive CLI the user already controls the args, hence MEDIUM. The Gemini server's `STEMMY_MCP_ALLOWED_ROOTS` covers audio *input* on its side only.

**Fix:** For inputs, add `exists=True, dir_okay=False`. For outputs, validate the parent dir is writable and within the project tree. Optionally enforce a root-directory policy via `Path.resolve().is_relative_to(root)`.

---

### [MEDIUM] Missing validation allows arbitrary `server_key` values to be stored

`ship_studios/mcp_client.py:48`

```python
self.server_keys: list[str] = list(
    server_keys
    if server_keys is not None
    else (config.LOOPS_SERVER, config.GEMINI_SERVER)
)
```

**Why:** `Hub.__init__` stores arbitrary `server_key` values without validation. Invalid keys (e.g. `Hub(["unknown-server"])`) are only caught later during `__aenter__`/`_open_session` when `config.server_parameters()` raises `KeyError` — far from the construction site, producing a less clear error.

**Fix:** Add an `__init__` validation loop: `for key in self.server_keys: if key not in (config.LOOPS_SERVER, config.GEMINI_SERVER): raise ValueError(f"unknown server key: {key!r}")`.

---

### [MEDIUM] `STEMMY_MCP_ALLOWED_ROOTS` passed through without local enforcement

`ship_studios/config.py:74` (security)

**Why:** The config forwards `STEMMY_MCP_ALLOWED_ROOTS` to the Gemini server's env via `_passthrough_env()` but never validates locally that audio paths stay within those roots before calling Gemini tools (`mastering-feedback`, `detect-mix-issues`, `compare-to-reference`, …). If the server's enforcement is bypassed or misconfigured, the hub won't catch it. (Adversarial verification adjusted to LOW: this is an intentional thin-client design — the README explicitly delegates enforcement to the Gemini subprocess, a controlled component.)

**Fix:** Optionally add defense-in-depth: parse `STEMMY_MCP_ALLOWED_ROOTS`, resolve roots, and verify each audio path is under one via `Path.is_relative_to()` before any Gemini call; or document this as a deliberate trust boundary.

---

### [MEDIUM] `zero_phase_eq` reshapes 1D input to 2D without documenting it

`drum_prep/dsp.py:209`

```python
x = np.atleast_2d(x.T).T if x.ndim == 1 else x  # normalize to (N, ch)
...
out[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch]) * glin, n=n)
return out
```

**Why:** 1D input `(N,)` returns as 2D `(N, 1)`; the docstring and `-> np.ndarray` return type don't say so, so callers must know to slice `[:, 0]`. (Adversarial verification adjusted to LOW: production callers always pass 2D from `io.read()`, so the 1D path is exercised only by unit tests, which already account for the shape change — a clarity/type issue, not a production bug.)

**Fix:** Either restore 1D output when the input was 1D, or document the `(N,) → (N, 1)` behavior in the docstring.

---

### [MEDIUM] `loops_to_deliverables` result `input`/`bpm` fields never tested

`tests/test_pipelines.py:252`

```python
result = await pipelines.loops_to_deliverables(...)
assert [d["loop"] for d in result["loops"]]
```

**Why:** The result dict carries `input`, `bpm`, `loops`, `steps`; tests assert only `loops`. The `bpm` parameter should round-trip into the result but is never checked — a refactor dropping `input`/`bpm` would pass silently.

**Fix:** Add `assert result["input"] == "drums.wav"` and `assert result["bpm"] == 120.0`.

---

### [MEDIUM] Insufficient test coverage for `drum_prep/sub_design.py`

`tests/test_drum_prep_sub_design.py:24`

**Why:** ~36 lines cover two significant functions (`estimate_fundamental`, `add_sub`). Untested: harmonic-fundamental selection with multiple peaks, the `sub_hz` override, envelope-following (`env_fc`), the full return-dict structure, and anti-clipping across `ceil_dbfs` variations. (Adversarial verification adjusted to LOW: core behavior *is* tested and correct; the gaps are edge cases on optional params with sane defaults.)

**Fix:** Add tests for envelope clipping, `sub_hz None` vs specified, return-dict fields, and the `env_fc` effect.

---

### [MEDIUM] `test_master_track_sequence` missing assertions for returned fields

`tests/test_pipelines.py:37`

```python
assert result["pipeline"] == "master-track"
```

**Why:** The return dict includes `input`, `streaming_compliant`, and `steps`; only `pipeline` is asserted here. `input` (the passed `mix_path`) is never directly asserted in *any* test. (Adjusted to LOW: `streaming_compliant` is covered by dedicated tests, and no pipeline test asserts `input` — a consistent convention gap rather than an isolated miss.)

**Fix:** Add `assert result["input"] == "projects/song/mix/mix.wav"` and a type check on `streaming_compliant`.

---

### [MEDIUM] `reference_match` result fields not fully verified

`tests/test_pipelines.py:165`

```python
result = await pipelines.reference_match(...)
assert recording_hub.server_tool_sequence == [...]
```

**Why:** The test checks only the server/tool call sequence; the returned `input` and `reference` fields are never asserted. (Adjusted to LOW: consistent with how other pipeline tests are written — the call sequence is verified but the result-dict identity fields aren't.)

**Fix:** Add `assert result["input"] == "mix.wav"` and `assert result["reference"] == "ref.wav"`.

---

## Documentation Review

### [HIGH] `docs/gemini-audio/README.md` references the non-existent `[[gemini-mastering-feedback-cross-check]]` skill

`docs/gemini-audio/README.md:47`

```
repo's standing policy ([[gemini-mastering-feedback-cross-check]]) and the roadmap's headline
```

**Why:** The wikilink convention maps `[[...]]` to retrievable resources (skills / linked docs), but `[[gemini-mastering-feedback-cross-check]]` resolves to nothing: no skill directory, no registered memory resource, no settings-configured memory system. It appears in three files — `README.md:47`, `caveats-and-limits.md:22`, and `.claude/skills/gemini-audio/SKILL.md:36`, where it's labeled "the `gemini-mastering-feedback-cross-check` memory note." The underlying policy (Gemini hears mono → meters own loudness/peak/stereo) *is* well documented in surrounding prose, so impact is limited to link integrity, but the link is dangling across three files.

**Fix:** Either (1) replace the wikilink with plain text describing the policy, or (2) create the referenced resource if it's meant to be maintained. The same broken link is filed again at MEDIUM (`doc-gemini-audio#1`) — fix both occurrences together.

---

### [MEDIUM] CLAUDE.md omits the `dry` feel option in the drum-prep `mix` command

`CLAUDE.md:403`

```
`drum-prep mix <dir> --feel <roomy|punchy|natural>` — mix the prepped kit...
```

**Why:** The code implements four feel options — `drum_prep/cli.py:165` declares `click.Choice(["roomy", "punchy", "natural", "dry"])` and `drum_prep/mix.py:36-40` gives `dry` its own loudness-offset profile ("close-mic forward, room essentially out"). The docs list only three, so users miss a real, working feature.

**Fix:** Update line 403 to `--feel <roomy|punchy|natural|dry>`.

---

### [MEDIUM] Tool count mismatch: "11 Gemini perceptual tools" should be "12"

`docs/gemini-audio/README.md:25`

```
✅ **Yes** — all 11 perceptual `stemmy-gemini` tools
```

**Why:** The `audio-understanding.md` table lists 12 unique tool names (…`recommend-mastering-chain` is the omitted 12th). The "11" claim recurs at README.md:68.

**Fix:** Change "11 perceptual" to "12 perceptual" at lines 25 and 68, or add a note if one tool is intentionally excluded.

---

### [MEDIUM] Non-existent skill referenced: `[[gemini-mastering-feedback-cross-check]]` (second site)

`docs/gemini-audio/README.md:47`

```
repo's standing policy ([[gemini-mastering-feedback-cross-check]])
```

**Why:** Same dangling wikilink as the HIGH finding above, also at `caveats-and-limits.md:22`. The target exists nowhere (skills list, CLAUDE.md, codebase). Either a planned-but-uncreated skill, a misnamed reference (perhaps meant to point at `[[mastering-feedback]]` / `[[gemini-audio]]`), or an obsolete memory-note reference.

**Fix:** Create the skill, repoint to an existing one, or remove the reference. Consolidate with the HIGH finding.

---

### [MEDIUM] KIT BB A5: iLok/PACE landmine stated in the field guide but not surfaced in the skill description

`docs/vst/kit-bb-a5.md:15`

```
**iLok/PACE plugin — verified-headless on THIS machine, a risk elsewhere.** BB A5 is iLok/PACE protected
```

**Why:** The field guide warns this is a render-farm landmine and that verification is *not portable* across machines. The full caveat exists in the SKILL.md Prerequisites/Pitfalls, but the primary skill-description entry point uses only abbreviated language, so a user deploying to a new machine may skip re-verification. Sister plugins (n105, n73) share the same abbreviated phrasing.

**Fix:** Add the landmine + "re-verify load+render on any new machine with `[[vst-verify]]`" caveat to the skill description.

---

### [MEDIUM] `docs/vst/manley-massive-passive.md` missing self-link to the `[[manley-massive-passive]]` skill

`docs/vst/manley-massive-passive.md:9`

```
**parallel passive** tube EQ counterpart to the surgical [[fabfilter-pro-q-4]], the program-EQ
[[pultec-eqp-1a]], and the Motown graphic [[hitsville-eq-mastering]].
```

**Why:** All 31 other VST field guides self-link back to their skill in the intro (e.g. `distressor.md:9` "the measured deep-dive behind the `[[distressor]]` skill"). This one omits it, breaking the documented bidirectional vst↔skill twin-pairing contract.

**Fix:** Append "— the measured deep-dive behind the `[[manley-massive-passive]]` skill." to the intro sentence.

---

### [MEDIUM] README claims "Six pipelines" but the code defines 5 async pipeline functions

`README.md:148`

```
Six pipelines, each available as a Claude Code skill/command and (where it
processes audio) as a CLI subcommand.
```

**Why:** `ship_studios/pipelines.py` defines exactly 5 `async def` pipelines: `master_track`, `mix_check`, `reference_match`, `loops_to_deliverables`, `understand_audio`. The 6th conceptual section (`new-track`) is filesystem-only with no async function and no CLI subcommand. CLAUDE.md:382 correctly says "The five pipeline subcommands."

**Fix:** Change to "Five pipelines," or clarify that 6 conceptual sections are described with one (new-track) being filesystem-only.

---

### [MEDIUM] README project-layout comment says "the six pipelines as async functions"

`README.md:273`

```
├── pipelines.py           the six pipelines as async functions
```

**Why:** Directly contradicts the code — `pipelines.py` has 5 async functions, not 6. Same root drift as the finding above, in the layout diagram.

**Fix:** Change "six" to "five."

---

### [LOW] drum-prep SKILL.md "24-bit AIFF with a `.wav` extension" phrasing is confusing

`.claude/skills/drum-prep/SKILL.md:87`

```
**Output is 24-bit AIFF with a `.wav` extension.** ffmpeg's container sniffing misreads these ("Invalid PCM packet").
```

**Why:** Technically accurate (write_aiff24 forces AIFF while preserving the input extension), but the phrasing reads as if the tool *intentionally* mislabels files. The real causality (input extension is preserved × AIFF format is forced = the trap) isn't explained. (Adjusted from MEDIUM to LOW.)

**Fix:** Clarify the causality and point to `[[format-fix]]` / `aiff2wav.sh`.

---

## Disputed (needs human judgment)

### [HIGH→MEDIUM, DISPUTED] Error-message construction can raise uncaught `KeyError`

`ship_studios/mcp_client.py:102` — confirmed 1 / refuted 1.

- **For:** Line 102 calls `config.server_dir(server_key)` inside an f-string in the `except TimeoutError` block; an invalid key makes it raise `KeyError`, escaping and masking the `TimeoutError`.
- **Against:** Line 86 calls `config.server_parameters(server_key)` *before* the try block, which validates the key and raises `KeyError` for bad keys there — so reaching line 102 implies a valid key, and the described failure can't occur in current control flow.
- **Call needed:** Is invalid-key reachability worth a defensive guard, or is the upstream validation considered sufficient? (Adjusted severity MEDIUM either way.)

### [HIGH, DISPUTED] Stereo stem balance formula causes a 3 dB loudness jump at center pan

`drum_prep/stem_mix.py:69` — confirmed 1 / refuted 1.

- **For:** At `pan=0` a center stereo stem keeps ~2.0 L²+R² power, whereas the mono equal-power `_pan()` produces 1.0 at center — a 10·log10(2) ≈ 3.01 dB mismatch between mono and stereo stems at center, breaking the "balanced by measured loudness" intent.
- **Against:** Line 68 guards the formula with `if pan:`, so it never executes at `pan=0` — stereo stems pass through at their loudness-normalized level. The 3 dB-at-center claim misreads the guard; the remaining mono-vs-stereo asymmetry is intentional.
- **Call needed:** Decide whether the mono/stereo pan-law asymmetry is a real contract violation worth normalizing, or intended behavior. (Note: the *non-disputed* sibling finding `code-mix-qc-io#0` already flags the equal-power problem for `pan != 0` and is confirmed 2/0 — the panning law is worth fixing regardless of the center-pan dispute.)

---

## Minor / unverified

Low / nit / unverified findings, condensed (file:line — note):

- `.claude/skills/loops-to-deliverables/SKILL.md:39` (LOW, unverified) — "already-mastered branch" cites step 2/4 that don't align with the numbered recipe.
- `.claude/skills/vst-preset/SKILL.md:34` (LOW, unverified) — `param` vs `parameters` used interchangeably; JSON key is `parameters`.
- `docs/vst/la-3a.md:34` (LOW, unverified) — keep the "odd/3rd-harmonic grit, not even-harmonic warmth" distinction clear in the skill (vs Fairchild/LA-2A).
- `docs/vst/manley-variable-mu.md:31` (MEDIUM→LOW, confirmed) — threshold is direct (lower = more GR), opposite the Fairchild's inverted enum; already documented in the deep-dive, only the skill `description` field lacks the cross-warning.
- `docs/vst/pultec-eqp-1a.md:287` (LOW, unverified) — output dB trim is a UA addition (hardware has none); note in skill description.
- `docs/vst/softube-tape.md:99` (MEDIUM→LOW, confirmed) — bare default is hot (Amount 7.8); warning already in SKILL.md body, only the top description field omits it.
- `docs/vst/ssl-bus-compressor-2.md:24` (LOW, unverified) — slow-attack-preserves-transients is correct here but opposite API Vision; a cross-compressor attack table in `[[vst-compress]]` would help.
- `ship_studios/config.py:153` (LOW, unverified, security) — `SHIP_STUDIOS_LOOPS_DIR`/`GEMINI_DIR` overrides resolved but not validated to point at real stemmy servers; `uv` could execute an arbitrary console script.
- `ship_studios/pipelines.py:214` / `cli.py:214` (LOW, unverified, security) — output paths not bounded to the project tree before write/MCP call.
- `ship_studios/pipelines.py:540` (LOW, unverified) — `_loop_paths` defensive parser tested only indirectly; add direct parametrized unit tests.
- `tests/test_drum_prep_sub_design.py:32` (LOW, unverified) — only `low_60_gain_db` asserted; add `flow`/`sub_hz`/`sub_gain_db` checks.
- `docs/vst/dbx-160.md:49` (NIT, unverified) — "all enums" but table includes bool params (`sc_filter`, `power`, `master_bypass`).
- `docs/vst/fairchild-660.md:36` (NIT, unverified) — "all 12 params are enums" but 2 are bool (`power`/`master_bypass`).
- `ship_studios/pipelines.py:15` (NIT, unverified) — missing blank line after module docstring (ruff format).
- `ship_studios/pipelines.py:28` (NIT, unverified) — multi-space inline-comment alignment in `DEFAULT_PRESETS` (ruff format).
- `ship_studios/pipelines.py:40` (NIT, unverified) — `_FEEDBACK_MOODS` should collapse to a single line (ruff format).
- `ship_studios/pipelines.py:112` (NIT, unverified) — `_Recorder.run()` signature should be single-line (ruff format).
- `ship_studios/pipelines.py:116` (NIT, unverified) — `_Recorder.run()` body dict should be single-line (ruff format).
- `ship_studios/pipelines.py:386` (NIT, unverified) — `clean-loop`/`optimize-seam` calls should be single-line (ruff format).
- `ship_studios/pipelines.py:561` (NIT, unverified) — `_loop_paths` generator expr should be single-line (ruff format).

Note: the 7 ruff-format nits should be confirmed/auto-fixed in one pass with `uv run ruff format` rather than hand-edited — they are formatter-driven and were not verified against a live ruff run in this worktree.

---

## Coverage & gaps

**Covered (comprehensive):** all 19 `drum_prep/` modules, all 5 `ship_studios/` modules, all 24 test files, and the full documentation surface (`docs/`, `.claude/skills/`, README.md, CLAUDE.md). 21 review units.

**Intentionally uncovered (out-of-scope directories):**

- `.claude/commands/loops.md`, `.claude/commands/master.md`, `.claude/commands/understand.md` — command-config/UI layer, not code-review units.
- `demo/installed-plugins-headless-safe.md`, `demo/installed-plugins.md` — reference/example artifacts.
- `presets/vst/README.md` — VST preset data/config, not code logic.
- `projects/watercolors/track.md` — example project metadata.

These 7 gaps are scoping decisions (command config, demo material, preset data, project examples), not omissions.

---

## Method

- **Workflow:** Findings were produced by per-unit review agents (21 units spanning code, tests, and docs), deduped, then independently verified. Each finding carries a `confirmed`/`refuted` tally and, where verification changed the call, an `adjusted_severity`.
- **Adversarial verification:** Every confirmed finding was re-checked by a separate pass that attempted to refute it (reading guards, control flow, surrounding docs, and downstream call sites). This downgraded several findings (e.g. the `qc.py` bare-except HIGH→MEDIUM once the `corrupt_sidecars` surfacing was found; several test-gap and security items MEDIUM→LOW once defaults/thin-client design were confirmed) and surfaced two genuine disputes (1 confirm / 1 refute each), preserved above for human judgment.
- **Sibling servers absent:** The two sibling MCP servers — `stemmy-loops` (`../stemmy-loops-mcp`) and `stemmy-gemini` (`../stemmy-gemini-mcp`) — were not present in this worktree. All findings are from static reading of *this* repo's code and docs; nothing was exercised against a live server, no audio was processed, and the ruff-format nits were not validated against an actual `ruff format`/`ruff check` run here.
