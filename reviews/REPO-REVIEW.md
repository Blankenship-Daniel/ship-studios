# ship-studios — Repository Code + Documentation Review

**Date:** 2026-06-03 · **Branch:** `main` · **Scope:** all (code + docs)

## Executive summary

This review covers the ship-studios hub (the DSP-free MCP-client `ship_studios/` package, the local `drum_prep/` DSP package, the CLI, the launch scripts, the `.claude/skills/` surface, and the `docs/` corpus including the VST field guides and the Gemini-audio reference). The headline theme is **documentation drift**: pipeline-recipe ordering in `CLAUDE.md` no longer matches `pipelines.py`, the README contradicts itself on the pipeline count, the Gemini-audio docs over-claim and mis-scope the wired tool surface, and many VST field guides state param counts or behavioral absolutes that their own tables/measurements contradict. On the code side the findings are smaller-blast-radius defensive-coding and DSP-numeric gaps in `drum_prep/` (role-detection precedence, near-zero denominators, NaN/Inf guards, inconsistent loudness anchoring, silent excepts) plus several test-coverage holes. No critical issues were found, and the two security findings around path handling were downgraded after adversarial verification confirmed the trust boundary is enforced (and resolved) inside the sibling Gemini server.

### Severity totals

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 3 |
| Medium | 22 |
| Low | 33 |
| Nit | 2 |
| **Disputed (subset, needs human judgment)** | 3 |

> Note: the three High findings below are the items that survived adversarial verification at High after dedup. Many findings originally proposed at higher severities were downgraded during verification (recorded inline); the totals above reflect the post-verification distribution, with the three disputed items counted separately.

---

## Code Review

### [HIGH] Role detection: "kick in" misdetected as `kick_sub` when both `in` and `sub` tokens are present

`drum_prep/roles.py:77`

```python
if has_tok("sub"):
    return Role.KICK_SUB, conf
return Role.KICK_IN, conf  # explicit 'in'/'inside' and bare 'kick'
```

**Why:** When a filename contains both an `in`/`inside` token and a `sub` token (e.g. `kick in - sub.aif`), the `sub` check fires first and the file is classified `KICK_SUB` instead of `KICK_IN`. The line-79 comment claims to honor an explicit `in`/`inside` keyword, but no such check exists — unlike the `beater`/`batter` (line 73) and `out`/`outside`/`front`/`reso` (line 75) sub-types, which *are* checked explicitly before the default. Verified by running `detect_role('kick in - sub.aif')`, which returns `Role.KICK_SUB`. There is no test for this edge case. Practical blast radius is bounded by the documented `kit.json` override, hence the verification notes oscillated between High and Medium; recorded here as confirmed-High.

**Fix:** Add an explicit `in`/`inside` check before the `sub` check, giving precedence order: beater → out/outside/front/reso → in/inside (new) → sub → default `KICK_IN`.

### [HIGH] Bare broad `except` without logging in `_try_samplerate`

`drum_prep/kit.py:95`

```python
        except Exception:
            continue  # try the next stem rather than giving up on the first failure
```

**Why:** This swallows every exception (permission errors, corrupt headers, missing files) silently. When all stems fail and the function returns `None`, the caller has zero visibility into which file failed or why, making kit-resolution failures hard to debug. Verification downgraded the practical impact to Medium because the populated `sr` field is "best-effort" and, per a cross-`drum_prep`/`ship_studios` grep, is never actually consumed — the real sample rate is re-derived during operations. The debuggability concern remains valid (especially for `strict=False` users who see warnings).

**Fix:** Log before continuing, e.g. `except Exception as exc: logger.warning("failed to read %s sample rate: %s", os.path.join(src_dir, s.name), exc); continue`.

### [HIGH] Missing test module for `drum_prep/overheads.py`

`tests/` (no `test_drum_prep_overheads.py`)

```
No test_drum_prep_overheads.py exists for drum_prep/overheads.py
```

**Why:** `resolve_overhead()` and `merge_overheads()` handle the overhead-mic resolution logic (L/R merging, optional phase-alignment). `resolve_overhead()` is only *indirectly* exercised — via `test_drum_prep_phase_align.py::test_phase_align_lr_overhead_pair`, which uses the default `align=False`; the `align=True` path (overheads.py:40-42) is untested. `merge_overheads()` (overheads.py:46) is never imported or called in any test — both of its branches (already-stereo early return, and the L/R merge case) are unverified, and the CLI `overheads` command is likewise untested. Verification noted partial indirect coverage justifies Medium, but the complete absence of `merge_overheads()` coverage keeps this a real test gap.

**Fix:** Add `tests/test_drum_prep_overheads.py` covering `resolve_overhead()` (stereo input; L/R pair with and without `align`) and `merge_overheads()` (both branches).

---

### [MEDIUM] Loudness anchor measured inconsistently with `flat` mode (mono anchor)

`drum_prep/mix.py:137`

```python
lufs_anchor = meter.integrated_loudness(io.to_stereo(ax) if not flat else ax)
```

**Why:** When `flat=True` and the anchor is mono (`[N,1]`), pyloudnorm measures it as mono (~-16.89 LUFS in the repro); when `flat=False`, `io.to_stereo()` makes it `[N,2]` (~-13.88 LUFS) — a ~3 dB swing for the same signal. Other mono stems are measured via `dsp.mono()` (1-D) at lines 158-159. Verification confirmed the discrepancy but found that in `flat` mode the mix math uses `gain=0.0` for all stems, so only the returned `anchor_lufs` *metadata* is affected, not the audio; in non-flat mode the anchor is already measured consistently — hence Medium, not High.

**Fix:** Always measure the anchor through `io.to_stereo(ax)` regardless of `flat`; the `flat` flag should skip balance/pan, not change how the anchor is metered.

### [MEDIUM] `STEMMY_MCP_ALLOWED_ROOTS` forwarded to the Gemini server but not validated by ship-studios

`ship_studios/config.py:78`

```
STEMMY_MCP_ALLOWED_ROOTS is listed in GEMINI_OVERRIDE_ENV and forwarded via _passthrough_env (line 244)
when set, but ship_studios does not validate whether file paths passed to gemini tools respect these roots
```

**Why:** The hub forwards the allow-list env var but performs no path validation of its own before calling Gemini tools (`mastering-feedback`, `check-streaming-targets`, `master-assistant`, `compare-audio-files`, …); confirmed via grep that no `Path.resolve()`/`is_relative_to()` checks exist in `pipelines.py`/`mcp_client.py`/`config.py`/`cli.py`. Verification downgraded from High to Medium because this is an intentional thin-client design: the README/CLAUDE.md document that enforcement lives in the Gemini subprocess (a controlled, owned component), and a related companion finding (the path-normalization item, now disputed below) showed the sibling server *does* resolve + parent-check paths. The remaining issue is design-clarity / defense-in-depth, not an active bypass.

**Fix:** Either add explicit `str(Path(path).resolve())` validation in the hub before calling Gemini path-taking tools (defense-in-depth), or document explicitly in CLAUDE.md that the allow-list is enforced solely by the Gemini server and the hub does not re-validate.

### [MEDIUM] Parabolic-interpolation delta can be unstable with very small denominators

`drum_prep/dsp.py:116`

```python
delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
```

**Why:** The guard only catches an *exactly*-zero denominator. With a tiny but non-zero curvature `den` (e.g. floating-point noise on a nearly-flat correlation peak), the division amplifies small `y0-y2` differences into huge sub-sample lag refinements; reproduced `den=-1e-6`, numerator `0.002` → `delta=-1000` samples, which would severely misalign `fractional_delay()` downstream. Impact is alignment-quality degradation in low-SNR edge cases, not a crash.

**Fix:** Use a magnitude threshold: `delta = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0` (consistent with the `1e-12` guard already used in `sub_design.py`).

### [MEDIUM] `normcorr` does not guard against NaN/Inf inputs

`drum_prep/dsp.py:40`

```python
def normcorr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    a = a[:n] - a[:n].mean()
    b = b[:n] - b[:n].mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))
```

**Why:** If either input carries NaN/Inf (from corrupted audio or an upstream FFT edge case), `normcorr` silently returns NaN/Inf, which propagates through `align_to()` into `phase_align()` results; downstream `_json_safe()` then converts NaN to `null` in the JSON, masking the computation error. The function already guards the `n==0` case, so an analogous finiteness guard is consistent. Medium because it requires upstream corruption to manifest.

**Fix:** After mean subtraction, add `if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)): return 0.0`.

### [MEDIUM] Pan-value clamping present in `stem_mix.py` but absent in `mix.py`

`drum_prep/mix.py:72`

```python
return base if perspective == "audience" else -base
```

**Why:** `stem_mix.py:75` clamps user-supplied pan with `np.clip(..., -1.0, 1.0)` precisely because an unclamped pan > 1 makes `cos()` produce negative gains (polarity inversion). `mix.py`'s `_role_pan()` (line 72) currently returns only `[-0.5, 0.5]`, so it is safe *today* — but the protection is inconsistent and would become a latent bug if `mix_kit()` ever exposed pan overrides. Verification confirmed it is currently safe, hence the downgrade toward Low/Medium.

**Fix:** Defensively clamp at the call site, e.g. `theta = np.clip(_role_pan(...), -1.0, 1.0)` at mix.py:175, matching the `stem_mix.py` pattern.

### [MEDIUM] No branch coverage for the flat-directory path in `_master_out`

`tests/test_pipelines.py:244`

```
test_batch_master_masters_dir_override tests ['a.wav','b.wav'] with explicit masters_dir (tested),
and test_batch_master_per_track_then_album_pass covers the projects/mix/ branch (tested),
but the flat-directory (parent.name != 'mix', no masters_dir) branch is NOT tested
```

**Why:** `_master_out` (pipelines.py:944-956) has three branches; the third (input not under a `mix/` parent and no `masters_dir` override → use `<parent>/masters/`) is unexercised. The logic appears correct; this is a coverage gap, not a defect.

**Fix:** Add `test_batch_master_default_layout_non_mix_path()` with paths like `['subdir/mix.wav','subdir/mix2.wav']` and no `masters_dir`, asserting masters land in the file's sibling `masters/`.

### [MEDIUM] `_profile_delta_curve` lacks direct unit tests for malformed inputs

`tests/test_pipelines.py:160`

```
_profile_delta_curve is tested only indirectly through test_house_curve_renders_match_eq_from_profile_delta
(happy path). No direct tests for missing freq_hz, non-numeric delta_db, partial/empty bands, non-dict input.
```

**Why:** The helper (pipelines.py:97-122) defensively returns `None` on many malformed shapes, but no test pins each branch. A regression could silently skip the `match-eq` render in `house_curve` (line 542). The sibling helper `_streaming_compliant` already has parametrized edge-case tests (`test_streaming_compliant_none_on_unexpected_shape`, line 968), establishing the precedent.

**Fix:** Add parametrized tests for: non-dict result, no `bands` key, empty `bands`, missing `freq_hz`, non-numeric `delta_db`, and wrong-type values — each asserting a non-raising `None`.

### [MEDIUM] Test gap: no coverage for "kick in" combined with "sub"

`tests/test_drum_prep_roles.py`

```
No test case for filenames like 'kick in - sub.aif' or 'kick in sub bass.aif'
```

**Why:** The companion code bug above went undetected precisely because no test asserts that an explicit `in`/`inside` keyword wins over implicit sub-type detection (`test_basic_role_mapping` only covers plain `kick in.aif`).

**Fix:** Add cases such as `('kick in - sub bass.aif', Role.KICK_IN)` and `('kick inside sub.aif', Role.KICK_IN)`.

---

## Documentation Review

### [HIGH] `reference-match` canonical recipe — step numbering / tool-identity drift

`CLAUDE.md:204`

```
4. `[L] apply-eq` — collapse the reconciled delta into a few shelves/bells (+ `tilt_db_per_octave`)
   and render the corrected mix (runs only when reconciled `eq_bands` are supplied). For a faithful render
   of the *whole* delta curve rather than a few bands, drive `[L] match-eq` instead …
```

**Why:** The coded pipeline (`pipelines.py::reference_match`, lines 426-503, asserted by `test_pipelines.py::test_reference_match_sequence`) always runs `match-eq`, with `apply-eq` as an *optional* residual layer. The prose inverts this: it labels step 4 as `apply-eq`, marks it conditional on `eq_bands`, and frames `match-eq` as an alternative ("instead"). The real order is (1) match-reference-numeric, (2) compare-to-reference, (3) compare-tonality, (4) **match-eq (always)**, (5) **apply-eq (conditional)**, (6) render-ab. Two verifiers confirmed; one argued it is documentation-accuracy rather than a functional defect (the code is correct) and leaned Medium — recorded as confirmed-High given it could mislead users about which params are required.

**Fix:** Renumber to the six-step actual order and rewrite step 4: "match-eq renders the source-minus-reference delta as a min/linear-phase FIR (always runs); apply-eq (optional) layers surgical bells/tilt when reconciled `eq_bands` are supplied," followed by render-ab.

### [HIGH] `fabfilter-pro-q-4.md` — Spectral Tilt marked unexposed in Part A but used as a live feature in Part B

`docs/vst/fabfilter-pro-q-4.md:92`

```
**Note:** the per-band **Spectral Tilt** parameter that FabFilter added in the **4.02** point release
is **not in the Pedalboard surface** here (we see `spectral_enabled` + `spectral_density` but no
`spectral_tilt`) — the installed build may predate 4.02, or the tilt isn't automation-exposed.
```

**Why:** Part B (~line 240) describes Spectral Tilt as a live triggering feature, which contradicts Part A's measured "not exposed on this rig." Adversarial verification split (1 confirm / 1 refute) and the adjusted severity settled at Medium, so this is carried in the Disputed section below — warnings already exist at lines 92 and 293, and the Part A/Part B measured-vs-synthesis split is intentional.

**Fix:** See the Disputed section.

### [MEDIUM] `loops-to-deliverables` SKILL — Recipe says `tag: true`, Pitfalls say it silently drops tags

`.claude/skills/loops-to-deliverables/SKILL.md:119`

```
Recipe step 6:  export-deliverables {path: <tagged loop>, ... tag: true}
Pitfall (l.117): `export-deliverables tag=true` silently drops the RIFF INFO chunk and `.tags.json`
                  sidecar. The success return lies. Treat export as un-tagged and re-tag afterward.
```

**Why:** The Recipe instructs the exact behavior the Pitfalls section warns is broken. Cross-confirmed by `build_loops.py` comments ("always export with tag=False, then tag after"), `projects/watercolors/track.md`, and `projects/ship-studios-drums/track.md` (soundfile `.rewrite.tmp` bug). Users following the Recipe will ship untagged files.

**Fix:** Make the Recipe match observed behavior — export with `tag: false`, then tag afterward (or fix the export tooling itself). The Pitfall is the accurate description.

### [MEDIUM] `loops-to-deliverables` SKILL — vague `tag-deliverable` output-path workaround

`.claude/skills/loops-to-deliverables/SKILL.md:124`

```
Pitfall: tag-deliverable in-place (out_path == path) fails (writes a <path>.rewrite.tmp).
Fix: tag with out_path != path — stage to a *sibling* dir using the **same basename**.
```

**Why:** The "same basename in a sibling dir" instruction is abstract, and the Recipe (line 69) shows no concrete naming pattern. Worse, the actual implementation (pipelines.py:797-800) uses a *different* working pattern: same directory with a filename suffix (`a.wav` → `a.master.wav` / `a.tagged.wav`). Both satisfy `out_path != path`, but the doc's prescribed pattern doesn't match the code. Verification downgraded to Low (the workaround is valid, just under-specified).

**Fix:** Add a concrete example to the Recipe that matches the code's suffix pattern, and cross-reference the Pitfall.

### [MEDIUM] `docs/gemini-audio/audio-understanding.md` — table lists tools outside the understand pipeline

`docs/gemini-audio/audio-understanding.md:24`

```
| **Perceptual mix/master critique** | … | analyze-mix-balance, detect-mix-issues, compare-to-reference,
  mastering-feedback, recommend-mastering-chain |
```

**Why:** `pipelines.py::understand_audio` (lines 858-926) calls only the six pure-understanding tools; the five listed critique tools belong to `mix_check`, `master_track`, and `reference_match`. A reader on an "audio understanding" page meets mastering tools from a different capability area — scope confusion.

**Fix:** Move the perceptual-critique row to a separate doc (or a clearly labeled "related Gemini tools beyond audio understanding" section), or add a header note that the table mixes understanding with critique tools.

### [MEDIUM] `docs/gemini-audio/README.md` — "11 Gemini perceptual tools" list is incomplete and context-ambiguous

`docs/gemini-audio/README.md:68`

```
stemmy-gemini-mcp is an audio-understanding server: 11 Gemini perceptual tools (transcribe,
describe-region, compare, classify, extract-events, summarize-long, audio-to-json, analyze-mix-balance,
detect-mix-issues, compare-to-reference, mastering-feedback)
```

**Why:** The list (1) abbreviates names (`describe-region` vs `describe-audio-region`, `compare` vs `compare-audio-files`); (2) labels the server "audio-understanding" while listing perceptual-critique tools; (3) omits at least `recommend-mastering-chain`, `master-assistant`, `critique-region`, `describe-loops`. CLAUDE.md marks 15 distinct Gemini tools. The "11" framing confuses which tools are understanding vs mastering.

**Fix:** Either narrow the list to the six understand-pipeline tools (transcribe-audio, describe-audio-region, extract-audio-events, classify-audio, compare-audio-files, audio-to-json) and move critique tools to a separate sentence, or relabel as the full Gemini surface with accurate count + full names.

### [MEDIUM] `docs/gemini-audio/README.md` — claims tools are "wired" that no pipeline calls

`docs/gemini-audio/README.md:7`

```
it is wired into the skill surface as the **`gemini-audio`** suite
```

**Why:** Line 69 lists `summarize-long` and the audio-understanding table lists `recommend-mastering-chain`, but neither appears in any pipeline (`understand_audio` does not call `summarize-long-audio`; there is no `mastering-plan` pipeline wiring `recommend-mastering-chain`). The "wired" claim therefore overreaches for these two tools.

**Fix:** Exclude `summarize-long-audio` and `recommend-mastering-chain` from the live-tools list and mark them as "documented reference tools, not yet wired into a pipeline" (or wire them).

### [MEDIUM] `docs/gemini-audio/README.md` — broken SECURITY.md link

`docs/gemini-audio/README.md:72`

```
([SECURITY.md](https://github.com/) of that repo)
```

**Why:** The link points at the bare GitHub homepage, so a reader chasing the stemmy-gemini security model lands nowhere useful.

**Fix:** Use the full URL, e.g. `https://github.com/<owner>/stemmy-gemini-mcp/blob/main/SECURITY.md` (owner to be confirmed against the actual sibling repo, which is absent from this worktree).

### [MEDIUM] `README.md` — "Six pipelines" headline contradicts the documented set and the "CLI subcommand" claim

`README.md:148`

```
Six pipelines, each available as a Claude Code skill/command and (where it
processes audio) as a CLI subcommand.
```

**Why:** Only five process-audio pipelines exist as async functions documented in the README (master-track, mix-check, reference-match, loops-to-deliverables, understand-audio); the sixth item, `new-track`, is "Pure filesystem" with no CLI subcommand, breaking the "each … as a CLI subcommand" promise. Line 273 of the same file says "the five pipelines," and `pipelines.py` actually has nine async functions. The count is internally inconsistent.

**Fix:** Change the headline to "Five pipelines …" and note `new-track` separately as filesystem-only (or enumerate all nine async functions with their grouping). Reconcile with line 273.

### [MEDIUM] `README.md` — "Project layout" says "the five pipelines"; headline says "six"

`README.md:273`

```
├── pipelines.py           the five pipelines as async functions
```

**Why:** Direct internal contradiction with line 148 ("Six pipelines"). Line 273 is the more accurate of the two (5 numbered pipeline functions), but neither value reflects the nine async functions actually in `pipelines.py` (the four extras: `batch_master`, `house_curve`, `stem_master`, `unmask_stems`).

**Fix:** Make line 148 and line 273 agree (recommended: "Five pipelines" for the user-facing audio workflows), and either document the four additional async helpers or state explicitly that they are not counted.

### [MEDIUM] `ship_studios/cli.py` — comment says "Five pipeline subcommands"; there are nine

`ship_studios/cli.py:4`

```python
A small click group that wires CLI args into the async pipeline functions
via the MCP Hub. Five pipeline subcommands (master, mix-check,
reference-match, loops, understand) plus a ``doctor``
```

**Why:** The CLI actually registers nine pipeline subcommands — master, house-curve, batch-master, unmask-stems, stem-master, mix-check, reference-match, loops, understand — plus `doctor`. The comment misrepresents the surface area for developers.

**Fix:** List all subcommands, or change to "Multiple pipeline subcommands" with the accurate enumeration.

### [MEDIUM] `CLAUDE.md` — `STEMMY_MCP_ALLOWED_ROOTS` row lacks format/enforcement detail

`CLAUDE.md:362`

```
| `STEMMY_MCP_ALLOWED_ROOTS` | optional `[G]` filesystem allow-list |
```

**Why:** No statement of expected format (colon-/comma-/newline-separated?), which side validates, or whether relative paths/symlinks are honored. Verification downgraded to Low (enforcement delegation is already documented in the README; the real gap is format specification of a pass-through var).

**Fix:** Expand to specify the delimiter and absolute-path expectation, and state that the Gemini server validates while the hub passes paths through unmodified.

### [MEDIUM] `docs/vst/distressor.md` — "All 12 are ENUMs" contradicts the table

`docs/vst/distressor.md:62`

```
| Param | Type | Range / values (measured) | GUI control |
… (table: bypass, ratio, detector, audio = string enums; input, attack, release, output, mix, headroom
   = numeric enums; power, master_bypass = bools)
```

**Why:** The summary calls all 12 params enums, but the table itself shows 4 string enums, 6 numeric enums, and 2 bools — the bools are not enums. Only the 3-4 string enums are the actual `apply-vst-chain` settability problem; the blanket statement obscures that.

**Fix:** Replace the blanket "All 12 are ENUMs" with "12 parameters: 4 string enums + 6 numeric enums + 2 bools," matching the table.

### [MEDIUM] `docs/vst/kit-bb-a5.md` — iLok/PACE caveat not carried into the `[[kit-bb-a5]]` skill description

`docs/vst/kit-bb-a5.md:14`

```
iLok/PACE plugin — verified-headless on THIS machine, a risk elsewhere. … if the authorization drifts,
re-screen with [[vst-verify]] before trusting a render. Never run an unlicensed/trial instance unattended …
```

**Why:** The doc is complete, but the skill description only says "iLok/PACE (verified-headless on this rig)" — it omits the drift / re-verify / never-run-trial-unattended warnings. A user invoking the skill on an unauthorized machine could render demo-noise without warning. Same gap applies to the N105 and N73 KIT skills. Downgraded to Medium because the skill correctly qualifies "on this rig," the doc is complete and linked, and CLAUDE.md globally flags iLok as a render-farm landmine.

**Fix:** Add the doc's §7 licensing warning to the `[[kit-bb-a5]]` (and N105/N73) skill preambles.

### [MEDIUM] `docs/vst/kit-bb-n73.md` — `pre_amp_saturation=TRUE` called "mandatory" but Part B treats sat-OFF as a valid effect

`docs/vst/kit-bb-n73.md:33`

```
`pre_amp_saturation=TRUE` is mandatory in Mic mode. With saturation ON … (~0.2–0.3 % THD). With
saturation OFF the Mic preamp is a raw high-gain amp that digitally CLIPS when driven …
```

**Why:** "Mandatory" is too absolute — Part A/B both document sat-OFF as a deliberate overdrive effect (23-46% THD). The same-sentence qualifier softens this, so it's a strong-language issue rather than a factual error; downgraded to Medium.

**Fix:** Change "mandatory" to "strongly recommended / required for transparent operation" and add: "sat-OFF is a raw clipping overdrive (23-46% THD) — use only for intentional distortion FX."

### [MEDIUM] `docs/vst/softube-transient-shaper.md` — iLok status not stated as crisply as peer docs

`docs/vst/softube-transient-shaper.md:29`

```
It renders headless via Pedalboard ([L] apply-vst-chain), iLok authorized here. Softube/iLok is usually a
render-farm landmine ([[vst]]) — re-verify load+render on any other machine.
```

**Why:** The render-farm risk is flagged, but unlike SSL/KIT/LA-6176 docs the authorization method (machine activation vs iLok Cloud, and Cloud's offline unsuitability) is not stated upfront — a critical detail for a render-farm candidate. The current text isn't incorrect; it just requires knowledge other docs supply.

**Fix:** Add a line specifying that Softube uses iLok/PACE (machine activation or USB dongle; iLok Cloud not suitable for offline) and to verify on each render node. (PACE specifics could not be verified read-only.)

### [MEDIUM] `docs/vst/studer-a800.md` — "harshness usually upstream" hedge + stray verification footnote

`docs/vst/studer-a800.md:20`

```
Lightly-driven tape DARKENS — *usually* a harshness cure, not the cause. … *(Verified 2026-06-03: an
adversarial web fact-check confirmed the measured darkening; it refuted only the over-absolute "almost
always upstream" wording — hence this scope.)*
```

**Why:** The parenthetical reads like a commit/review artifact accidentally left in the doc, and the surrounding prose still implies "usually upstream" despite admitting the original framing was over-absolute. The technical content (both upstream and tape-overdrive causes, with correct levers) is accurate, so this is a format/narrative-completeness issue → Medium.

**Fix:** Remove the footnote and rewrite to: "Harshness can be upstream OR from tape over-drive. Isolate & measure every stage — if the tape stage alone adds measured harsh odd-harmonics (`measure-distortion`), reduce Input / increase over-bias / pick a higher-headroom tape; if tape darkens the centroid, suspect the stage before it."

### [MEDIUM] `docs/vst/oxide-tape.md` — IPS claim inverts textbook tape behavior without explanation

`docs/vst/oxide-tape.md:37`

```
15 IPS = the warm, full-low setting; 7.5 IPS = the "more colored / frequency-shift" setting (leaner lows,
more upper energy). Note this **inverts** the textbook "slower = bigger bass head-bump"…
```

**Why:** The heading acknowledges the inversion but doesn't explain *why* this model differs from textbook tape, leaving the reader unsure if it's intentional voicing or a modeling artifact. Verification confirmed the measurement is accurate (band-low metrics back it) and the rationale exists downstream (lines 174-176), so this is a clarity/UX issue → Low.

**Fix:** Add an inline note that the speeds are voiced for practical mixing rather than spec accuracy, and that centroid is a balance metric, not an absolute warmth/harshness indicator.

### [MEDIUM] `docs/vst/pultec-meq-5.md` — "matches the +8 dB hardware ceiling" but measured +8.84 dB

`docs/vst/pultec-meq-5.md:25`

```
HIGH PEAK ≈ +0.9/unit → +8.8 dB max (matches the hardware's documented +8 dB ceiling, Part B)
```

**Why:** The plugin's own table shows +8.84 dB at dial 10, a 0.84 dB gap from the +8 dB hardware spec, so "matches" is imprecise. Verified the discrepancy is documented in the measured table (not hidden) and within typical tolerance → Low.

**Fix:** Phrase as "+8.84 dB max (within ±1 dB of the ~+8 dB hardware spec)" rather than claiming an exact match.

---

## Disputed (needs human judgment)

These three findings split during adversarial verification (1 confirm / 1 refute each); a human should adjudicate.

### [DISPUTED → MEDIUM] `fabfilter-pro-q-4.md` — Spectral Tilt unexposed (Part A) vs used as a feature (Part B)

`docs/vst/fabfilter-pro-q-4.md:92`

```
the per-band Spectral Tilt parameter … is not in the Pedalboard surface here … (Part B §3 still describes
Spectral Tilt's triggering effect as a feature)
```

The tension is real (Part A measured-on-this-rig vs Part B web-research synthesis). **Refuter:** warnings already exist at line 92 ("don't script it; not reachable"), line 293 (Pitfalls), and the Part A/Part B split is intentional — the proposed footnote is effectively already present. **Confirmer:** a reader skimming only §3 could still miss the caveats. Adjusted severity: Medium. **Judgment needed:** whether to add one more inline caveat in §3 or accept the existing warnings as sufficient.

### [DISPUTED → MEDIUM] `tape-j-37.md` — DAW-only passthrough warning supposedly missing from the skill

`docs/vst/tape-j-37.md:15`

```
It does NOT render through apply-vst-chain / the headless pipeline on this rig … its DSP never engages —
it passes audio through unprocessed (only a fixed latency offset).
```

**Refuter:** the `[[tape-j-37]]` SKILL.md description *already* leads with "CRITICAL: this plugin does NOT render headless … (measured passthrough) — it is DAW-only," and CLAUDE.md line 20 also flags it — so the warning is present in both the doc and the skill. **Confirmer:** observed the skill description as blank/empty in the system-reminder listing and flagged the doc-vs-skill gap, but agreed the doc itself is correct and downgraded to Medium. **Judgment needed:** confirm whether the deployed skill description actually carries the warning (the SKILL.md frontmatter shows it does); if so, this finding is effectively resolved.

### [DISPUTED → LOW] File paths to Gemini tools not normalized via `Path.resolve()`

`ship_studios/pipelines.py:205`

```
mastering-feedback is called with raw mix_path (line 205); check-streaming-targets uses out_path directly
(line 230) without Path.resolve()
```

**Confirmer:** the hub passes un-normalized relative/symlink paths to Gemini tools, which could bypass a naive prefix-matching allow-list. **Refuter:** the sibling Gemini server's `validate_paths()` (`_call.py:166-178`) *always* calls `Path.resolve()` and `validate_under_allowed_roots()` (`_call.py:74-95`) compares resolved paths via `root in resolved.parents` (not string prefixes), with `test_path_allowlist.py` confirming symlink-escape rejection — so the finding's premise (string-prefix matching) is factually wrong and the boundary is enforced. Adjusted severity: Low (defense-in-depth nicety in the hub, not a live vulnerability). **Judgment needed:** whether to add redundant `Path.resolve()` in the thin-client hub anyway. (Note: the sibling server was absent from this worktree; the refuter's evidence came from the companion finding's verification.)

---

## Minor / unverified

Condensed; low/nit and unverified items not detailed above.

- [LOW, confirmed] `docs/vst/ampex-atr-102.md:55` — "30 params" ambiguous: 28 audio params + 2 control bools depending on whether bools are counted. Clarify the count basis.
- [LOW, confirmed] `docs/vst/fairchild-660.md:50` — "all 12 params are enums" but numeric enums (input/thresh) are float-settable; only string/bool enums need the harness. Clarify.
- [LOW, confirmed] `docs/vst/helios-type-69.md:31` — bass-BOOST unreachable headless is documented but the Mic-drive/`apply-eq` workaround is buried in TL;DR point 4; front-load it.
- [LOW, confirmed] `docs/vst/softube-tape.md:32` — default state is "already hot" (Amount 7.8); the footgun warning exists but TL;DR ordering de-emphasizes it. Lead with it.
- [LOW, confirmed] `docs/vst/ssl-4k-e.md:104` — float-dict-vs-string-enum gotcha is in Part B §7 but not restated in §5; add the explicit float-settable vs string-enum lists.
- [LOW, confirmed] `docs/vst/ssl-native-channel-strip-2.md:67` — `lf_gain_db` measured ±16.5 dB (not the published ±20); documented with a warning, but add a TL;DR bullet so a 20 dB off-grid value isn't attempted.
- [LOW, confirmed] `docs/vst/studer-a800.md:27` — 30 IPS measures "darker" (centroid) while extending highs; add an explicit "don't characterize IPS brightness by centroid alone" note.
- [LOW, confirmed] `ship_studios/cli.py:155,157,176,178` — `raise … from None` suppresses the FileNotFoundError/JSONDecodeError chain. Intentional at the CLI validation boundary; use `from exc` (or omit) to preserve the root cause for debugging.
- [LOW, confirmed] `ship_studios/config.py` (security shard #3) — `STEMMY_MCP_ALLOWED_ROOTS` docs lack format/enforcement detail (duplicate-area of the CLAUDE.md:362 item; downgraded to Low).
- [LOW, unverified] `docs/vst/fabfilter-pro-mb.md:22` — "156 params" count is accurate but breakdown (6×21 + 30 globals) is buried; surface it in TL;DR.
- [LOW, unverified] `docs/vst/fabfilter-saturn-2.md:62` — "956 automatable parameters" lacks a transparent derivation; add the breakdown.
- [LOW, unverified] `docs/vst/hitsville-eq.md:20` — "RENDERS headless here — proven" should add a per-machine re-verify caveat to match the `[[vst]]` doctrine.
- [LOW, unverified] `docs/vst/kit-bb-n105.md:173` — Master-Buss is API-derived and GUI-only/not host-automatable; add the note in Part B §2.
- [LOW, unverified] `docs/vst/kit-bb-n73.md:41` — `master_bus_toggle` "(it wasn't on the N105)" assumes the reader has read the N105 doc; make the contrast explicit for standalone reading.
- [LOW, unverified] `docs/vst/la-6176.md:44` — "all 26 params are enums" not reflected in the `[[la-6176]]` skill description; add the preset-harness warning.
- [LOW, unverified] `docs/vst/manley-massive-passive.md:75` — "51 params" applies to the standard build; the MST build lacks an explicit param count.
- [LOW, unverified] `docs/vst/manley-variable-mu.md:37` — HEADROOM "inverted" described twice with slightly conflicting framing; unify the wording.
- [LOW, unverified] `docs/vst/manley-voxbox.md:4` — header says "four blocks" but signal flow lists six elements (includes output transformer); clarify functional vs signal-flow counting.
- [LOW, unverified] `docs/vst/oxide-tape.md:40` — `noise_reduct=true` default not explained vs its tonal inertness on a hot bus; add when-to-disable guidance.
- [LOW, unverified] `docs/vst/pultec-eqp-1a.md:69` — "12 parameters" doesn't clarify whether reserved/cosmetic params are included (cf. the Softube Tape doc's audio-vs-cruft split).
- [LOW, unverified] `docs/vst/pultec-meq-5.md:25` — DIP "saturates ~-11 dB by ~7" needs the practical consequence (dial 6-10 add little; set by ear).
- [LOW, unverified] `docs/vst/ssl-bus-compressor-2.md:164` — "X ratio" (>20:1, <∞, not a limiter) clarified only in Part B; front-load to TL;DR.
- [LOW, unverified] `drum_prep/dsp.py:204` — `interp_gain_db` doesn't assert `centers` is ascending (np.interp requires sorted xp); add a guard for external callers.
- [LOW, unverified] `drum_prep/dsp.py:34` — `mono()` docstring doesn't note that 1-D input is returned unchanged.
- [LOW, unverified] `drum_prep/roles.py:62` — overhead L/R ambiguity if both "left" and "right" tokens appear (returns OVERHEAD_L); document or handle as stereo/ambiguous.
- [LOW, unverified] `README.md:273` (duplicate-area of the confirmed README drift) — "the five pipelines" vs six+ documented; reconcile or enumerate all nine async functions.
- [LOW, unverified] `scripts/mcp_launch.py:35` — `_console_for` ternary falls back to GEMINI_CONSOLE_SCRIPT for any non-LOOPS key; make it a dict lookup that raises KeyError.
- [NIT, unverified] `docs/vst/pultec-hlf-3c.md:21` — "iLok account, no dongle" uses non-standard phrasing vs the "no-iLok" shorthand elsewhere; standardize.
- [NIT, unverified] `docs/vst/vibe-analog-machines.md:11` — Verve→Vibe rename handling is thorough and correct; flagged as a positive example, no fix needed.

---

## Coverage & gaps

**Well covered:** the core functional modules — `drum_prep/dsp.py`, `kit.py`, `roles.py`, `mix.py`, `stem_mix.py`, `overheads.py` — and the hub (`pipelines.py`, `cli.py`, `config.py`, `mcp_client.py`, `scripts/mcp_launch.py`), plus the documentation corpus (`CLAUDE.md`, `README.md`, `docs/gemini-audio/`, all `docs/vst/*` field guides, and the `.claude/skills/` prose). 21 review units spanned DSP numerics, async safety, silent failures, security/trust boundary, test coverage, and doc-integrity dimensions.

**Files not reviewed line-by-line** (covered only by broad directory prefix or excluded by scope): module init/entry files (`drum_prep/__init__.py`, `drum_prep/__main__.py`, `ship_studios/__init__.py`, `tests/__init__.py`), test infrastructure/fixtures (`tests/conftest.py`, `tests/drumkit_synth.py`), the individual `tests/test_*.py` implementations, `tests/test_vst_harness.py`, `tests/test_scripts_mix.py`, `.gitignore`, and `uv.lock`.

**Dimensional gaps:**
- Integration testing against the live MCP servers — the sibling `stemmy-loops-mcp` / `stemmy-gemini-mcp` checkouts were **absent from this worktree**, so all server-interaction claims were verified against the hub's recording fakes and the in-repo contract, not live tools.
- End-to-end pipeline execution scenarios (the suite asserts ordered tool-call logs, not live output).
- Error-recovery / rollback paths and persistence/state across pipeline runs.
- Async/concurrency safety beyond the pipelines unit.
- Performance profiling / benchmarking.
- VCS and dependency-pin config (`uv.lock`, `.gitignore`) and module import-cycle detection.

Intentionally out of scope: `presets/` (JSON configs), `scripts/` (one-off helpers, also excluded from ruff/mypy by design), `projects/` (user data), `demo/` artifacts, and cache dirs.

---

## Method

This review was produced by the **repo-review fan-out workflow**: read-only review agents were dispatched by dimension (code: DSP numerics, async safety, silent failures, security/trust boundary, test coverage; docs: CLAUDE.md contract drift, wikilink/twin integrity, pipeline-order lockstep, and VST/Gemini/skill consistency), each producing candidate findings. Every finding then passed through an **adversarial verification** stage in which independent verifiers attempted to both confirm and refute it against the actual files — recording `confirmed`/`refuted` counts and an `adjusted_severity`. Findings that split (1 confirm / 1 refute) are surfaced in the Disputed section rather than asserted; several originally-High items were downgraded to Medium/Low when verification showed the documented behavior was already mitigated or the code path was currently safe. Confidence and per-finding verify notes informed the severities reported above.

**Important caveat:** the two sibling MCP servers (`../stemmy-loops-mcp`, `../stemmy-gemini-mcp`) were **not present in this worktree**. All findings that touch server behavior were verified against the ship-studios hub, its contract in `CLAUDE.md`, the recorded-tool-call test fakes, and (for the disputed path-normalization item) the companion finding's evidence — not against running servers. Claims about server-side enforcement (e.g. Gemini `validate_paths` resolving symlinks) should be re-confirmed when the siblings are checked out alongside this repo.
