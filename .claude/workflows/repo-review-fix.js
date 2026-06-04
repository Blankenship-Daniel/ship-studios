export const meta = {
  name: 'repo-review-fix',
  description: 'Apply every finding from reviews/REPO-REVIEW.md. Fans out edit agents partitioned by DISJOINT file groups (no two agents touch the same file), then runs one centralized CI gate (pytest + ruff + mypy + wikilink integrity).',
  phases: [
    { title: 'Apply', detail: 'one edit agent per disjoint file group' },
    { title: 'Verify', detail: 'central CI gate: pytest + ruff + mypy + wikilinks' },
  ],
}

// ---- shared guardrails -------------------------------------------------------------------------
const GROUND =
  'GUARDRAILS (violating any of these is worse than leaving a finding unfixed):\n' +
  '- READ each in-scope file IN FULL before editing. Make the MINIMAL precise edit for each finding; do NOT touch unrelated lines.\n' +
  '- NEVER run `ruff format` or reformat whole files. NEVER run uv/pytest/mypy (a central verify step handles it). You MAY run `python3 -c "import ast; ast.parse(open(PATH).read())"` to confirm a Python edit still parses.\n' +
  '- Do NOT change DSP numeric BEHAVIOR on the happy path. The guard fixes only change edge-case/error/NaN handling.\n' +
  '- Do NOT add Path.resolve()/path validation to ship_studios/pipelines.py or its tool-call args — tests/test_pipelines.py asserts EXACT args and it would break the contract. Security is documentation-only where stated.\n' +
  '- In CLAUDE.md keep tool-name spellings EXACT (hyphen vs underscore) and [L]/[G] prefixes intact.\n' +
  '- For skills, edit the SKILL.md BODY/preamble, NOT the YAML frontmatter `description` (that drives triggering).\n' +
  '- Touch ONLY the files listed for your group. Do NOT edit reviews/REPO-REVIEW.md or anything under memory/.\n' +
  'REPO GROUND TRUTH: pipelines.py has 5 user-facing async pipelines + 4 helpers (batch_master/house_curve/stem_master/unmask_stems) = 9 async fns. ruff line-length 100, EXCLUDES scripts/ & presets/; mypy targets only ship_studios + drum_prep. Sibling MCP servers (../stemmy-*-mcp) are ABSENT here.'

const EDITLOG = {
  type: 'object', additionalProperties: false,
  properties: {
    applied: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, finding: { type: 'string' }, change: { type: 'string' } },
      required: ['file', 'finding', 'change'] } },
    skipped: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, finding: { type: 'string' }, reason: { type: 'string' } },
      required: ['file', 'finding', 'reason'] } },
    notes: { type: 'string' },
  },
  required: ['applied', 'skipped'],
}

const GATE = {
  type: 'object', additionalProperties: false,
  properties: {
    pytest: { type: 'string', description: 'pass/fail summary + any FAILED node ids' },
    ruff: { type: 'string' },
    mypy: { type: 'string' },
    wikilinks: { type: 'string', description: 'any dangling [[link]] introduced, or "clean"' },
    pass: { type: 'boolean' },
    failures: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['pytest', 'ruff', 'mypy', 'pass', 'failures'],
}

// ---- groups (each owns a DISJOINT set of files) ------------------------------------------------
const GROUPS = [
  // ===== CODE =====
  { id: 'code-roles', files: ['drum_prep/roles.py', 'tests/test_drum_prep_roles.py'], findings: [
    "drum_prep/roles.py:77 — [HIGH] 'kick in' misdetected as kick_sub when a filename has BOTH an 'in'/'inside' token AND a 'sub' token. The line-79 comment promises explicit 'in'/'inside' is honored but no such check exists before `if has_tok(\"sub\")`. FIX: add an explicit in/inside check immediately BEFORE the sub check, e.g. `if has_tok(\"in\", \"inside\") or has_sub(\"inside\"): return Role.KICK_IN, conf`. Resulting precedence: beater -> out/outside/front/reso -> in/inside (NEW) -> sub -> default KICK_IN. First confirm has_tok matches whole tokens (so 'in' won't match substrings) and that existing cases ('kick in.aif', 'kick sub.aif', bare 'kick.aif') keep their current result.",
    "drum_prep/roles.py:62 — [LOW] overhead L/R ambiguity: if BOTH 'left' and 'right' qualifiers appear it returns OVERHEAD_L. FIX (preferred): if both left and right tokens are present, return Role.OVERHEAD (full stereo) before the L/R branches. If any existing test would break, instead just add a clarifying comment documenting the OVERHEAD_L tie-break. Pick the option that keeps the suite green.",
    "tests/test_drum_prep_roles.py — [MEDIUM] add regression cases proving explicit in/inside wins over sub: ('kick in - sub bass.aif', Role.KICK_IN) and ('kick inside sub.aif', Role.KICK_IN). Match the existing parametrization style in this file.",
  ] },
  { id: 'code-overheads-test', files: ['tests/test_drum_prep_overheads.py'], findings: [
    "tests/test_drum_prep_overheads.py — [HIGH] CREATE this new test module (none exists). First READ drum_prep/overheads.py, tests/test_drum_prep_phase_align.py, tests/conftest.py and tests/drumkit_synth.py to learn the fixtures/synthesis helpers. Cover: resolve_overhead() with (a) a single stereo input (early return), (b) an L/R pair with align=False, (c) an L/R pair with align=True (the overheads.py:40-42 path); and merge_overheads() BOTH branches (already-stereo early return; the L/R merge case). Keep it fully offline (synthesize signals, no network/keys/real audio files).",
  ] },
  { id: 'code-kit', files: ['drum_prep/kit.py'], findings: [
    "drum_prep/kit.py:95 — [HIGH] `except Exception: continue` in _try_samplerate swallows every error silently. FIX: log before continuing. Add a module logger if absent (`import logging` + `logger = logging.getLogger(__name__)`) and change to `except Exception as exc: logger.warning(\"failed to read %s sample rate: %s\", <path-expr>, exc); continue`. Read the function to use the correct path expression and follow any existing logging convention in the package.",
  ] },
  { id: 'code-mix', files: ['drum_prep/mix.py'], findings: [
    "drum_prep/mix.py:137 — [MEDIUM] anchor loudness metered inconsistently in flat mode (mono vs stereo ~3 dB swing). FIX: always meter the anchor through io.to_stereo(ax): change `meter.integrated_loudness(io.to_stereo(ax) if not flat else ax)` to `meter.integrated_loudness(io.to_stereo(ax))`. The flat flag should skip balance/pan, not change how the anchor is metered.",
    "drum_prep/mix.py:175 — [MEDIUM] pan not clamped (stem_mix.py clamps to [-1,1] to avoid cos() polarity inversion). FIX: defensively clamp at the _role_pan call site, e.g. `theta = np.clip(_role_pan(...), -1.0, 1.0)`. Read to find the exact call site (~line 175) and apply matching the stem_mix.py pattern.",
  ] },
  { id: 'code-dsp', files: ['drum_prep/dsp.py'], findings: [
    "drum_prep/dsp.py:116 — [MEDIUM] parabolic-interp guard only catches exactly-zero denominator; a tiny den explodes the sub-sample delta. FIX: `delta = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0` (matches the 1e-12 guard already used in sub_design.py).",
    "drum_prep/dsp.py:40 — [MEDIUM] normcorr has no NaN/Inf guard. FIX: after mean subtraction add `if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): return 0.0` (mirrors the existing n==0 guard).",
    "drum_prep/dsp.py:204 — [LOW] interp_gain_db doesn't ensure `centers` is ascending (np.interp requires sorted xp). FIX: add a defensive guard for external callers (e.g. `if np.any(np.diff(centers) < 0): raise ValueError(\"centers must be ascending\")`) AND/OR a docstring precondition note. Confirm internal callers pass ascending centers so the guard never fires in the suite.",
    "drum_prep/dsp.py:34 — [LOW] mono() docstring should note that 1-D input is returned unchanged. FIX: add that sentence to the docstring (no behavior change).",
  ] },
  { id: 'code-cli-config', files: ['ship_studios/cli.py', 'ship_studios/config.py'], findings: [
    "ship_studios/cli.py:4 — [MEDIUM] module docstring says 'Five pipeline subcommands' but nine are registered. FIX: enumerate the actual nine (master, house-curve, batch-master, unmask-stems, stem-master, mix-check, reference-match, loops, understand) plus doctor — or say 'Multiple pipeline subcommands (...)' with the accurate list. Read the registrations to confirm the exact names.",
    "ship_studios/cli.py:155,157,176,178 — [LOW] `raise ... from None` suppresses the FileNotFoundError/JSONDecodeError cause chain. FIX: bind the except as `exc` and use `raise ... from exc` to preserve the root cause at the CLI validation boundary. Read each site to apply correctly.",
    "ship_studios/config.py — [LOW/design-clarity] STEMMY_MCP_ALLOWED_ROOTS is forwarded but not validated by the hub. Do NOT add validation to call sites. INSTEAD add a short clarifying comment where STEMMY_MCP_ALLOWED_ROOTS is handled (GEMINI_OVERRIDE_ENV / _passthrough_env) stating: the allow-list is ENFORCED by the Gemini subprocess (which Path.resolve()-normalizes + parent-checks resolved paths); the hub passes paths through unmodified.",
  ] },
  { id: 'code-pipelines-test', files: ['tests/test_pipelines.py'], findings: [
    "tests/test_pipelines.py — [MEDIUM] add test_batch_master_default_layout_non_mix_path(): inputs like ['subdir/mix.wav','subdir/mix2.wav'] with NO masters_dir override, asserting masters land in the file's sibling masters/ dir (the third branch of _master_out, pipelines.py ~944-956). Read _master_out + the existing batch_master tests to match the harness/style.",
    "tests/test_pipelines.py — [MEDIUM] add parametrized tests for _profile_delta_curve (pipelines.py ~97-122) malformed inputs, each asserting it returns None without raising: non-dict result, missing 'bands' key, empty 'bands', a band missing 'freq_hz', non-numeric 'delta_db', and wrong-type values. Mirror the style of test_streaming_compliant_none_on_unexpected_shape.",
  ] },
  { id: 'code-scripts', files: ['scripts/mcp_launch.py'], findings: [
    "scripts/mcp_launch.py:35 — [LOW] _console_for ternary falls back to the GEMINI console script for ANY non-LOOPS key. FIX: replace with an explicit dict lookup keyed by the known server keys that raises KeyError on an unknown key. (scripts/ is excluded from ruff/mypy, so keep the edit minimal and self-consistent.)",
  ] },

  // ===== DOCS =====
  { id: 'doc-claude', files: ['CLAUDE.md'], findings: [
    "CLAUDE.md (reference-match Canonical pipeline) — [HIGH] the prose inverts the coded order: it labels step 4 `[L] apply-eq` (conditional) and frames `[L] match-eq` as an alternative ('instead'), but pipelines.py::reference_match ALWAYS runs match-eq, with apply-eq as the OPTIONAL residual. FIX: READ ship_studios/pipelines.py::reference_match AND tests/test_pipelines.py::test_reference_match_sequence to get the EXACT ordered tool calls, then rewrite the recipe to lockstep. Target order: (1) [G] match-reference-numeric, (2) [G] compare-to-reference, (3) [L] compare-tonality, (4) [L] match-eq (ALWAYS runs — render the reconciled delta as a min/linear-phase FIR), (5) [L] apply-eq (OPTIONAL residual — only when reconciled eq_bands are supplied), (6) [L] render-ab. Preserve tool spellings + [L]/[G].",
    "CLAUDE.md:362 — [MEDIUM] the STEMMY_MCP_ALLOWED_ROOTS env-var row lacks format/enforcement detail. FIX: expand the row to state the delimiter + that absolute paths are expected, and that the GEMINI server validates (Path.resolve + parent-check) while the hub passes paths through unmodified. Match the wording to the README allow-list note if present.",
  ] },
  { id: 'doc-readme', files: ['README.md'], findings: [
    "README.md:148 vs :273 — [MEDIUM] 'Six pipelines' (148) contradicts 'the five pipelines' (273); new-track has no CLI subcommand though 148 implies each does; pipelines.py actually has nine async fns. FIX: change 148 to 'Five pipelines' for the user-facing audio workflows, note new-track separately as filesystem-only (no CLI subcommand), reconcile with 273, and optionally note the four extra async helpers (batch_master, house_curve, stem_master, unmask_stems) are not counted among the five. Read the file to apply precisely.",
  ] },
  { id: 'doc-gemini', files: ['docs/gemini-audio/README.md', 'docs/gemini-audio/audio-understanding.md'], findings: [
    "docs/gemini-audio/audio-understanding.md:24 — [MEDIUM] the capability table lists perceptual-critique tools (analyze-mix-balance, detect-mix-issues, compare-to-reference, mastering-feedback, recommend-mastering-chain) that are NOT part of the understand pipeline. FIX: move that row to a clearly-labeled 'related Gemini tools beyond audio understanding' section, or add a header note that those belong to mix-check / master-track / reference-match.",
    "docs/gemini-audio/README.md:68-69 — [MEDIUM] the '11 Gemini perceptual tools' list abbreviates names (describe-region, compare), mislabels understanding vs critique, and omits tools. FIX: narrow to the six understand-pipeline tools with EXACT names (transcribe-audio, describe-audio-region, extract-audio-events, classify-audio, compare-audio-files, audio-to-json) and move critique tools to a separate sentence — OR relabel as the full Gemini surface with an accurate count + full names. Cross-check spellings against CLAUDE.md sections 1 and 4.",
    "docs/gemini-audio/README.md:7 & :69 — [MEDIUM] 'wired' overclaims for summarize-long-audio and recommend-mastering-chain (no pipeline calls them). FIX: mark these two as 'documented reference tools, not yet wired into a pipeline' rather than wired.",
    "docs/gemini-audio/README.md:72 — [MEDIUM] broken SECURITY.md link points at the bare https://github.com/ homepage. FIX: grep this repo for the stemmy-gemini-mcp repo URL/owner (.mcp.json, pyproject.toml, other docs); if found, link the real .../stemmy-gemini-mcp/blob/main/SECURITY.md; if the owner is NOT discoverable in this worktree, replace the bare-homepage href with plain text referencing 'the stemmy-gemini-mcp repo's SECURITY.md' (no misleading link).",
  ] },
  { id: 'doc-loops-skill', files: ['.claude/skills/loops-to-deliverables/SKILL.md'], findings: [
    "SKILL.md (Recipe step 6, ~line 119) vs the Pitfall (~line 117) — [MEDIUM] the Recipe says export-deliverables tag:true, but the Pitfall warns tag=true silently drops the RIFF INFO chunk + .tags.json sidecar. FIX: change the Recipe to export with tag:false then tag afterward (make the Recipe match the accurate Pitfall and the 'export tag=False then tag after' pattern).",
    "SKILL.md (~line 124) — [LOW] the tag-deliverable out_path workaround ('same basename in a sibling dir') doesn't match the code's actual working pattern (pipelines.py ~797-800 uses the same dir with a filename suffix: a.wav -> a.master.wav / a.tagged.wav). FIX: add a concrete example matching the code's suffix pattern and cross-reference the Pitfall.",
  ] },
  { id: 'doc-vst-1', files: ['docs/vst/distressor.md', 'docs/vst/fairchild-660.md', 'docs/vst/ampex-atr-102.md', 'docs/vst/pultec-eqp-1a.md', 'docs/vst/pultec-meq-5.md'], findings: [
    "docs/vst/distressor.md:62 — [MEDIUM] 'All 12 are ENUMs' contradicts the table (4 string enums + 6 numeric enums + 2 bools). FIX: replace with '12 parameters: 4 string enums + 6 numeric enums + 2 bools' and note only the string enums are the apply-vst-chain settability problem.",
    "docs/vst/fairchild-660.md:50 — [LOW] 'all 12 params are enums' but numeric enums (input/thresh) are float-settable; only string/bool enums need the harness. FIX: clarify which are float-settable vs string/bool-enum (harness-only).",
    "docs/vst/ampex-atr-102.md:55 — [LOW] '30 params' is ambiguous (28 audio params + 2 control bools). FIX: clarify the count basis.",
    "docs/vst/pultec-eqp-1a.md:69 — [LOW] '12 parameters' doesn't say whether reserved/cosmetic params are counted. FIX: clarify (cf. the Softube Tape doc's audio-vs-cruft split).",
    "docs/vst/pultec-meq-5.md:25 — [LOW] (a) 'matches the +8 dB hardware ceiling' but measured +8.84 dB — rephrase as '+8.84 dB max (within ±1 dB of the ~+8 dB hardware spec)'. (b) the DIP 'saturates ~-11 dB by ~7' note should add the practical consequence (dials 6-10 add little; set by ear).",
  ] },
  { id: 'doc-vst-2', files: ['docs/vst/kit-bb-a5.md', 'docs/vst/kit-bb-n73.md', 'docs/vst/kit-bb-n105.md', '.claude/skills/kit-bb-a5/SKILL.md', '.claude/skills/kit-bb-n73/SKILL.md', '.claude/skills/kit-bb-n105/SKILL.md'], findings: [
    "[MEDIUM] The kit-bb-a5 / kit-bb-n73 / kit-bb-n105 SKILL.md files omit the iLok/PACE drift / re-verify / never-run-trial-unattended warning that the docs (§7) carry. FIX: add a one-line licensing caveat to each skill's BODY preamble (NOT the frontmatter description), e.g. 'iLok/PACE: verified-headless on THIS rig only — if authorization drifts, re-screen with [[vst-verify]] before trusting a render; never run an unlicensed/trial instance unattended.'",
    "docs/vst/kit-bb-n73.md:33 — [MEDIUM] pre_amp_saturation=TRUE called 'mandatory' but Part B treats sat-OFF as a valid overdrive effect. FIX: change 'mandatory' to 'strongly recommended / required for transparent operation' and add: 'sat-OFF is a raw clipping overdrive (23-46% THD) — use only for intentional distortion FX.'",
    "docs/vst/kit-bb-n105.md:173 — [LOW] Master-Buss is API-derived and GUI-only / not host-automatable; add that note in Part B §2.",
    "docs/vst/kit-bb-n73.md:41 — [LOW] master_bus_toggle '(it wasn't on the N105)' assumes the reader has read the N105 doc; make the contrast self-contained.",
  ] },
  { id: 'doc-vst-3', files: ['docs/vst/studer-a800.md', 'docs/vst/oxide-tape.md', 'docs/vst/softube-tape.md', 'docs/vst/softube-transient-shaper.md'], findings: [
    "docs/vst/studer-a800.md:20 — [MEDIUM] 'harshness usually upstream' hedge + a stray '(Verified 2026-06-03: adversarial web fact-check...)' footnote that reads like a review artifact. FIX: remove the footnote and rewrite to: 'Harshness can be upstream OR from tape over-drive. Isolate & measure every stage — if the tape stage alone adds measured harsh odd-harmonics (measure-distortion), reduce Input / increase over-bias / pick a higher-headroom tape; if tape darkens the centroid, suspect the stage before it.'",
    "docs/vst/studer-a800.md:27 — [LOW] 30 IPS measures 'darker' (centroid) while extending highs; add a 'don't characterize IPS brightness by centroid alone' note.",
    "docs/vst/oxide-tape.md:37 — [LOW] the IPS claim inverts textbook tape behavior; add an inline note that the speeds are voiced for practical mixing not spec accuracy, and centroid is a balance metric not an absolute warmth indicator (rationale already at ~lines 174-176).",
    "docs/vst/oxide-tape.md:40 — [LOW] noise_reduct=true default not explained vs its tonal inertness on a hot bus; add when-to-disable guidance.",
    "docs/vst/softube-tape.md:32 — [LOW] default state is already hot (Amount 7.8); lead the TL;DR with that footgun warning.",
    "docs/vst/softube-transient-shaper.md:29 — [MEDIUM] iLok status not stated as crisply as peer docs. FIX: add a line that Softube uses iLok/PACE (machine activation or USB dongle; iLok Cloud not suitable for offline) and to verify load+render on each render node (phrase as the peer SSL/KIT docs do; PACE specifics unverifiable read-only).",
  ] },
  { id: 'doc-vst-4', files: ['docs/vst/ssl-4k-e.md', 'docs/vst/ssl-native-channel-strip-2.md', 'docs/vst/ssl-bus-compressor-2.md', 'docs/vst/helios-type-69.md'], findings: [
    "docs/vst/ssl-4k-e.md:104 — [LOW] the float-dict-vs-string-enum gotcha is in Part B §7 but not in §5; add explicit float-settable vs string-enum lists to §5.",
    "docs/vst/ssl-native-channel-strip-2.md:67 — [LOW] lf_gain_db measured ±16.5 dB (not the published ±20); add a TL;DR bullet so a 20 dB off-grid value isn't attempted.",
    "docs/vst/ssl-bus-compressor-2.md:164 — [LOW] the 'X ratio' (>20:1, <∞, not a limiter) is clarified only in Part B; front-load it to the TL;DR.",
    "docs/vst/helios-type-69.md:31 — [LOW] the bass-BOOST-unreachable-headless workaround (Mic-drive / apply-eq) is buried in TL;DR point 4; front-load it.",
  ] },
  { id: 'doc-vst-5', files: ['docs/vst/manley-massive-passive.md', 'docs/vst/manley-variable-mu.md', 'docs/vst/manley-voxbox.md', 'docs/vst/la-6176.md', '.claude/skills/la-6176/SKILL.md'], findings: [
    "docs/vst/manley-massive-passive.md:75 — [LOW] '51 params' applies to the standard build; the MST build lacks an explicit param count. FIX: note the MST build's count or state it differs / wasn't measured.",
    "docs/vst/manley-variable-mu.md:37 — [LOW] HEADROOM 'inverted' is described twice with slightly conflicting framing; unify the wording.",
    "docs/vst/manley-voxbox.md:4 — [LOW] header says 'four blocks' but the signal flow lists six elements (incl. output transformer); clarify functional-block vs signal-flow-element counting.",
    "docs/vst/la-6176.md:44 + .claude/skills/la-6176/SKILL.md — [LOW] 'all 26 params are enums' is not reflected in the [[la-6176]] skill; add the preset-harness warning to the la-6176 SKILL.md body.",
  ] },
  { id: 'doc-vst-6', files: ['docs/vst/fabfilter-pro-mb.md', 'docs/vst/fabfilter-saturn-2.md', 'docs/vst/fabfilter-pro-q-4.md', 'docs/vst/hitsville-eq.md', 'docs/vst/pultec-hlf-3c.md'], findings: [
    "docs/vst/fabfilter-pro-mb.md:22 — [LOW] '156 params' is accurate but the breakdown (6×21 + 30 globals) is buried; surface it in the TL;DR.",
    "docs/vst/fabfilter-saturn-2.md:62 — [LOW] '956 automatable parameters' lacks a transparent derivation; add the breakdown.",
    "docs/vst/fabfilter-pro-q-4.md:92 & §3 (~line 240) — [DISPUTED->MEDIUM] Part A says per-band Spectral Tilt is NOT exposed on this rig; §3 describes its triggering as a live feature. FIX (conservative): add ONE inline caveat in §3 where Spectral Tilt is described, cross-referencing the Part A note (line 92) that spectral_tilt is not in the Pedalboard surface here, so it's GUI-only / not scriptable. Do NOT delete the §3 synthesis.",
    "docs/vst/hitsville-eq.md:20 — [LOW] 'RENDERS headless here — proven' should add a per-machine re-verify caveat to match the [[vst]] doctrine.",
    "docs/vst/pultec-hlf-3c.md:21 — [NIT] 'iLok account, no dongle' uses non-standard phrasing vs the 'no-iLok' shorthand elsewhere; standardize the phrasing (keep the meaning).",
  ] },
  { id: 'doc-tape-j37', files: ['docs/vst/tape-j-37.md', '.claude/skills/tape-j-37/SKILL.md'], findings: [
    "[DISPUTED->verify] tape-j-37: the DAW-only passthrough warning should appear in BOTH docs/vst/tape-j-37.md and the [[tape-j-37]] SKILL.md. VERIFY both carry it crisply. If the SKILL.md BODY lacks a one-line pointer ('does NOT render headless — DAW-only; bounce in the DAW then hand the result back; use a headless tape instead'), add it to the body. If both already cover it, make NO change and report it as already-covered in skipped[].",
  ] },
]

// ---- Phase 1: Apply (parallel; disjoint files => safe; barrier before verify) -------------------
phase('Apply')
log(`applying fixes across ${GROUPS.length} disjoint file groups`)
const editPrompt = g =>
  'You are a precise, senior engineer applying ALREADY-TRIAGED review findings to the ship-studios repo. Working dir = repo root.\n\n' +
  `FILE GROUP: ${g.id}\nYOU OWN ONLY THESE FILES (touch nothing else): ${g.files.join(', ')}\n\n` +
  'FINDINGS TO FIX (apply every one; each is verified-real):\n' + g.findings.map((f, i) => `${i + 1}. ${f}`).join('\n') + '\n\n' +
  GROUND + '\n\n' +
  'METHOD: read each owned file in full -> apply the minimal edit for each finding -> (for .py) confirm it still parses with python3 ast -> record each change. If a finding is genuinely already satisfied, put it in skipped[] with the reason. Return applied + skipped + notes.'

const results = await parallel(GROUPS.map(g => () =>
  agent(editPrompt(g), { label: `fix:${g.id}`, phase: 'Apply', schema: EDITLOG, agentType: 'general-purpose' })
    .then(r => ({ id: g.id, ...(r || { applied: [], skipped: [], notes: 'no result' }) }))))

const ok = results.filter(Boolean)
const totalApplied = ok.reduce((n, r) => n + (r.applied || []).length, 0)
const totalSkipped = ok.reduce((n, r) => n + (r.skipped || []).length, 0)
log(`apply done: ${totalApplied} edits applied, ${totalSkipped} skipped across ${ok.length} groups`)

// ---- Phase 2: Verify (single agent, single env => no uv race) ----------------------------------
phase('Verify')
const gate = await agent(
  'You are the CI gate for the ship-studios repo (read-only verification — do NOT fix anything). Working dir = repo root. Run, in order, and capture the TAIL of each:\n' +
  '1. `uv sync --extra drum-prep` (provision DSP test deps + dev tools).\n' +
  '2. `uv run --no-sync pytest -q` (FULL suite). Report pass/fail counts + every FAILED node id.\n' +
  '3. `uv run --no-sync ruff check` (report any violation with file:line).\n' +
  '4. `uv run --no-sync mypy` (report any error with file:line).\n' +
  '5. Wikilink integrity: `grep -rhoE "\\[\\[[^]]+\\]\\]" CLAUDE.md docs .claude/skills | sort -u`, then for each [[name]] confirm a `.claude/skills/<name>/` directory exists. Report any DANGLING link, but ONLY flag ones plausibly introduced/affected by edits to: CLAUDE.md, README.md, docs/**, .claude/skills/** (the files this fix run touched).\n' +
  'If `uv` is unavailable, say so explicitly and fall back to `python3 -m pytest` etc., noting it in notes. Set pass=true ONLY if pytest, ruff, and mypy are all clean. List concrete failures in failures[] (each: "file:line — what").',
  { label: 'ci-gate', phase: 'Verify', schema: GATE, agentType: 'general-purpose' })

return {
  groups: ok.length,
  applied: totalApplied,
  skipped: totalSkipped,
  per_group: ok.map(r => ({ id: r.id, applied: (r.applied || []).length, skipped: (r.skipped || []).length, notes: r.notes || '' })),
  gate,
}
