export const meta = {
  name: 'repo-review',
  description: 'In-depth CODE + DOCUMENTATION review of the ship-studios repo. Fans out read-only review agents by dimension (DSP numerics, async safety, silent failures, security, tests; CLAUDE.md contract drift, wikilink/twin integrity, pipeline-order drift, vst/gemini/skill consistency), adversarially verifies each finding, then synthesizes a prioritized markdown report. args = { scope?: "all"|"code"|"docs" (default all), focus?: string[] (unit-id/area substrings), out?: string (default "reviews/REPO-REVIEW.md"), fix?: boolean (default false — opt-in safe mechanical auto-fixes) }.',
  phases: [
    { title: 'Scout', detail: 'inventory the repo (git ls-files + wc -l)' },
    { title: 'Review', detail: 'one read-only agent per (dimension × area) unit, then adversarial refuters per finding (tiered by severity)' },
    { title: 'Synthesize', detail: 'dedupe, coverage-critic, write the prioritized report' },
    { title: 'Fix', detail: 'opt-in: apply only safe mechanical fixes' },
  ],
}

// ---- args (defensive: may arrive as object OR JSON string) --------------------------------------
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const scope = (A.scope === 'code' || A.scope === 'docs') ? A.scope : 'all'
const focus = Array.isArray(A.focus) ? A.focus : []
const OUT = A.out || 'reviews/REPO-REVIEW.md'
const FIX = !!A.fix
log(`repo-review: scope=${scope} fix=${FIX} focus=[${focus.join(',')}] out=${OUT}`)

// ---- schemas ------------------------------------------------------------------------------------
const INVENTORY = {
  type: 'object', additionalProperties: false,
  properties: {
    codeFiles: { type: 'array', items: { type: 'string' }, description: 'repo-relative .py paths under ship_studios/ and drum_prep/' },
    testFiles: { type: 'array', items: { type: 'string' } },
    docFiles:  { type: 'array', items: { type: 'string' }, description: 'tracked .md paths' },
    skills:    { type: 'array', items: { type: 'string' }, description: 'skill directory names under .claude/skills/' },
    vstGuides: { type: 'array', items: { type: 'string' }, description: 'docs/vst/*.md excluding README.md and any inventory file' },
    notes:     { type: 'string' },
  },
  required: ['codeFiles', 'docFiles', 'skills', 'vstGuides'],
}

const FINDINGS = {
  type: 'object', additionalProperties: false,
  properties: {
    findings: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        title:    { type: 'string', description: 'one specific line, no fluff' },
        kind:     { type: 'string', enum: ['code', 'docs'] },
        category: { type: 'string', enum: ['correctness','dsp-numerics','async-safety','error-handling','security','type-safety','test-gap','dead-code','simplify','doc-drift','link-integrity','tool-name','frontmatter','consistency','prose'] },
        severity: { type: 'string', enum: ['critical','high','medium','low','nit'] },
        file:     { type: 'string', description: 'repo-relative PRIMARY location' },
        line:     { type: 'integer', description: '0 if not line-specific' },
        evidence: { type: 'string', description: 'exact quoted offending text' },
        why:      { type: 'string', description: 'why it is wrong / the impact' },
        fix:      { type: 'string', description: 'concrete suggested fix' },
        refs:     { type: 'array', items: { type: 'string' } },
        confidence:{ type: 'string', enum: ['high','medium','low'] },
      },
      required: ['title','kind','category','severity','file','line','evidence','why','fix','confidence'],
    } },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object', additionalProperties: false,
  properties: {
    verdict:           { type: 'string', enum: ['confirmed','refuted','needs-human'] },
    located:           { type: 'boolean', description: 'did you find the cited file:line?' },
    adjusted_severity: { type: 'string', enum: ['critical','high','medium','low','nit'] },
    rationale:         { type: 'string', description: 'what you checked; quote the line you read' },
    grounded_by:       { type: 'string', enum: ['read-file','ran-ruff','ran-mypy','ran-pytest','grep','none'] },
  },
  required: ['verdict','located','adjusted_severity','rationale','grounded_by'],
}

const COVERAGE = {
  type: 'object', additionalProperties: false,
  properties: {
    uncovered_files: { type: 'array', items: { type: 'string' } },
    gaps:            { type: 'array', items: { type: 'string' }, description: 'areas/dimensions no unit covered' },
    notes:           { type: 'string' },
  },
  required: ['uncovered_files','gaps'],
}

const REPORT = {
  type: 'object', additionalProperties: false,
  properties: {
    report_path: { type: 'string' },
    written:     { type: 'boolean' },
    summary:     { type: 'string', description: '3-5 sentence executive summary' },
  },
  required: ['report_path','written','summary'],
}

const FIXLOG = {
  type: 'object', additionalProperties: false,
  properties: {
    applied: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, change: { type: 'string' } }, required: ['file','change'] } },
    skipped: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, reason: { type: 'string' } }, required: ['file','reason'] } },
    notes:   { type: 'string' },
  },
  required: ['applied','skipped'],
}

// ---- shared ground truth (prevents the known false positives) -----------------------------------
const GROUND_TRUTH =
  'REPO GROUND TRUTH — do NOT flag these as issues:\n' +
  '- ship_studios/pipelines.py has EXACTLY 5 async pipelines (master_track, mix_check, reference_match, loops_to_deliverables, understand_audio). CLAUDE.md\'s "six lifecycle stages" and the "Canonical pipelines" section are DIFFERENT taxonomies (lifecycle stages; SKILL-level pipelines like logic-extract / multitrack-triage). 6-vs-5 is NOT a drift.\n' +
  '- tests/test_mcp_client.py is NOT empty: it has 11 real async tests.\n' +
  '- ruff line-length is 100 and EXCLUDES scripts/, presets/, projects/. mypy targets ONLY ship_studios + drum_prep (py3.12). pytest asyncio_mode=auto, testpaths=["tests"]. Findings inside excluded dirs are OUT OF SCOPE.\n' +
  '- docs/vst/ has 32 plugin field guides (+ README + inventory); each has a twin [[<plugin>]] skill.\n' +
  '- Sibling MCP servers (../stemmy-loops-mcp, ../stemmy-gemini-mcp) are ABSENT in this worktree; never require them — degrade gracefully.'

// ---- helpers (deterministic; no Date.now / Math.random) -----------------------------------------
const RANK = { critical: 0, high: 1, medium: 2, low: 3, nit: 4 }
const sev = s => (s in RANK ? RANK[s] : 5)
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
const shard = (arr, n) => { const o = Array.from({ length: n }, () => []); (arr || []).forEach((x, i) => o[i % n].push(x)); return o }

function dedupe(findings) {
  const map = new Map()
  for (const f of findings) {
    const key = `${f.file}|${f.category}|${slug(f.title)}`
    const cur = map.get(key)
    const fSev = f.adjusted_severity || f.severity
    if (!cur) { map.set(key, { ...f, adjusted_severity: fSev, dupes: 1 }) }
    else {
      cur.dupes++
      if (sev(fSev) < sev(cur.adjusted_severity)) cur.adjusted_severity = fSev
      cur.refs = Array.from(new Set([...(cur.refs || []), ...(f.refs || [])]))
    }
  }
  return [...map.values()].sort((a, b) =>
    sev(a.adjusted_severity) - sev(b.adjusted_severity) || a.file.localeCompare(b.file))
}

function verifiersFor(s, tight) {
  if (s === 'critical' || s === 'high') return tight ? 1 : 2
  if (s === 'medium') return tight ? 0 : 1
  return 0 // low / nit skip verification
}

// ---- review units -------------------------------------------------------------------------------
const CODE_UNITS = [
  { id: 'code-dsp-core',       kind: 'code', area: 'drum_prep DSP numerics (ported, critical)', paths: ['drum_prep/dsp.py', 'drum_prep/phase_align.py'],
    focus: 'Numerical correctness of the ported numerics: normalized cross-correlation, fractional-delay, FFT ops, zero-phase (real symmetric) EQ; envelope-coarse→waveform-refine alignment with NO half-period slips; edge cases (empty/very short signals, dtype, NaN/inf, length preservation, polarity). The guardrails in CLAUDE.md (coherent time-domain sum not power-sum; zero-phase EQ; cuts→all stems, boosts→owners) must hold.' },
  { id: 'code-kit-roles',      kind: 'code', area: 'kit / role detection', paths: ['drum_prep/kit.py', 'drum_prep/roles.py', 'drum_prep/overheads.py'],
    focus: 'Role auto-detection heuristics, partner-pair wiring, overhead-mode inference, manifest (kit.json) override correctness, dataclass invariants, fx-return exclusion from phase-align.' },
  { id: 'code-refmatch-tone',  kind: 'code', area: 'reference-match + tonal DSP', paths: ['drum_prep/reference_match.py', 'drum_prep/tune.py', 'drum_prep/sub_design.py', 'drum_prep/normalize.py', 'drum_prep/stereo_merge.py'],
    focus: 'Coherent kit-sum measurement, per-stem corrective-curve distribution (cuts→all, boosts→owners), one global headroom trim, resampling correctness, L/R pairing heuristics.' },
  { id: 'code-mix-qc-io',      kind: 'code', area: 'mix / qc / audition / io', paths: ['drum_prep/mix.py', 'drum_prep/qc.py', 'drum_prep/audition.py', 'drum_prep/stem_mix.py', 'drum_prep/chain.py', 'drum_prep/io.py'],
    focus: 'Loudness (LUFS) balance + panning math, ITU-R BS.1770 loudness-matched A/B, inter-stem correlation / mono-sum, and the 24-bit-AIFF-with-.wav-name I/O trap (read/write paths).' },
  { id: 'code-hub-client',     kind: 'code', area: 'MCP client hub + config (async)', paths: ['ship_studios/mcp_client.py', 'ship_studios/config.py'],
    focus: 'Async session lifecycle / context-manager cleanup, timeout wrapping, cancellation, structured-vs-text result fallback, env + path/dir resolution, Optional handling. MAY run `uv run mypy ship_studios` (read-only) to ground type findings.' },
  { id: 'code-pipelines',      kind: 'code', area: 'pipelines vs their test contract', paths: ['ship_studios/pipelines.py', 'tests/test_pipelines.py'],
    focus: 'The 5 pipelines: tool-call ORDER + args vs the asserted server_tool_sequence / args_for in test_pipelines.py; platform / severity / service vocabulary mapping; only-verified-tool-names. A reordered/renamed call must match the test.' },
  { id: 'code-cli',            kind: 'code', area: 'CLI surfaces', paths: ['ship_studios/cli.py', 'drum_prep/cli.py'],
    focus: 'Arg parsing, exit codes, ExceptionGroup flattening (preserve the real error), error surfacing to the user, lazy imports.' },
  { id: 'code-silent-failures',kind: 'code', area: 'silent failures (cross-cutting)', paths: ['ship_studios/', 'drum_prep/'],
    focus: 'Bare/broad except, swallowed exceptions, except-pass, fallbacks that mask real failures, missing re-raise, errors logged-then-ignored. Grep-seed then judge each.' },
  { id: 'code-security',       kind: 'code', area: 'security / trust boundary', paths: ['ship_studios/config.py', 'drum_prep/io.py', '.mcp.json', '.env.example'],
    focus: 'Is STEMMY_MCP_ALLOWED_ROOTS actually ENFORCED (not just read)? Path traversal in path/file handling; no API key (GEMINI_API_KEY/ANTHROPIC_API_KEY) logged/echoed; .env.example ships only placeholders; the `uv --directory ../stemmy-*-mcp` sibling-repo invocation as a trust boundary.' },
  { id: 'code-test-coverage',  kind: 'code', area: 'test coverage + fixtures', paths: ['tests/'],
    focus: 'Module→test mapping (every ship_studios/* and drum_prep/* has a test), weak/absent assertions, untested branches, drumkit_synth realism, the FakeSession/RecordingHub contracts, the offline guarantee (no network/keys/audio).' },
]

const DOC_STATIC = [
  { id: 'doc-contract-drift',  kind: 'docs', area: 'CLAUDE.md contract drift', paths: ['CLAUDE.md', 'docs/mix-master-capability-roadmap.md', 'ship_studios/pipelines.py', 'tests/test_pipelines.py'],
    focus: 'Tool-name spelling (hyphen vs underscore) in CLAUDE.md vs names actually used in pipelines.py / asserted in test_pipelines.py; the [L]=45 / [G]=23 tool counts vs the roadmap + tables; and diff each "Canonical pipelines" prose recipe against the test\'s ordered server_tool_sequence. HONOR the three distinct "six" senses (see ground truth) — do not emit a 6-vs-5 finding.' },
  { id: 'doc-link-integrity',  kind: 'docs', area: 'wikilink + twin-pairing integrity', paths: ['.claude/skills/', 'CLAUDE.md', 'docs/'],
    focus: 'Every [[wikilink]] (grep -rEo "\\[\\[[^]]+\\]\\]") resolves to an existing .claude/skills/<name>/ dir; every docs/*.md reference resolves to a file; and the vst↔skill twins pair BOTH ways (each docs/vst/<plugin>.md has a [[<plugin>]] skill and each per-plugin skill links its docs/vst/<plugin>.md). Report dangling links precisely.' },
  { id: 'doc-skill-frontmatter',kind: 'docs', area: 'skill frontmatter', paths: ['.claude/skills/'],
    focus: 'Every SKILL.md has valid YAML frontmatter with name / description / argument-hint; name matches its directory; no duplicate names; description triggers are accurate and not contradictory.' },
  { id: 'doc-gemini-audio',    kind: 'docs', area: 'gemini-audio docs consistency', paths: ['docs/gemini-audio/', '.mcp.json'],
    focus: 'README index routes the 4 audio areas correctly; the "NOT wired" markers (speech/live/music) vs "wired" (understanding) match reality (.mcp.json = 2 servers, gemini read-only); the "Gemini hears ~16 kbps mono → meters own loudness/peak/stereo" claim is stated consistently across the docs + gemini skills.' },
  { id: 'doc-drumprep',        kind: 'docs', area: 'drum-prep docs ↔ code', paths: ['drum_prep/cli.py', 'CLAUDE.md', 'README.md'],
    focus: 'The drum-prep subcommands/flags + mic roles + kit.json contract + the "Guardrails (do not change)" DSP principles described in CLAUDE.md/README/skills vs what drum_prep/cli.py + dsp.py actually implement.' },
  { id: 'doc-toplevel-drift',  kind: 'docs', area: 'top-level cross-file drift', paths: ['README.md', 'CLAUDE.md', '.env.example', '.mcp.json', 'pyproject.toml'],
    focus: 'README ↔ CLAUDE.md drift (setup commands, tool surface, pipeline list); env-var names documented vs .env.example; server names/paths vs .mcp.json; python version + extras vs pyproject.toml; ruff exclude list claims vs pyproject.' },
]

// ---- main ---------------------------------------------------------------------------------------
// Phase 1: Scout
phase('Scout')
const inv = await agent(
  'You are a read-only repo scout. Working dir is the repo root. Using Bash, produce an accurate inventory:\n' +
  '- codeFiles: `git ls-files "ship_studios/*.py" "drum_prep/*.py"` (repo-relative).\n' +
  '- testFiles: `git ls-files "tests/*.py"`.\n' +
  '- docFiles: `git ls-files "*.md"`.\n' +
  '- skills: the directory names under .claude/skills/ that contain a SKILL.md (`ls .claude/skills`).\n' +
  '- vstGuides: `git ls-files "docs/vst/*.md"` EXCLUDING README.md and any "*inventory*" / "*installed*" file.\n' +
  'Do not modify anything. Return the inventory object.',
  { label: 'scout', phase: 'Scout', schema: INVENTORY, agentType: 'Explore' },
)
if (inv) log(`scout: ${(inv.codeFiles || []).length} code, ${(inv.docFiles || []).length} docs, ${(inv.skills || []).length} skills, ${(inv.vstGuides || []).length} vst guides`)
else log('scout: no inventory returned — using static globs for sharded units')

// Build dynamic (volume-heavy) doc units from the scout inventory.
const vstShards = shard((inv && inv.vstGuides) || ['docs/vst/ (all plugin guides)'], 3)
const skillShards = shard((inv && inv.skills) || ['(all under .claude/skills/)'], 2)
const DOC_DYNAMIC = [
  ...vstShards.map((files, i) => ({ id: `doc-vst-${i + 1}`, kind: 'docs', area: `vst field guides (shard ${i + 1}/3)`, paths: files,
    focus: 'For each plugin guide in this shard: does its claimed param count / character / headless-build (uaudio vs UAD twin) / iLok claims stay internally consistent AND match its twin [[<plugin>]] skill description? Flag contradictions, stale claims, broken structure.' })),
  ...skillShards.map((names, i) => ({ id: `doc-skills-quality-${i + 1}`, kind: 'docs', area: `skill prose/triggering (shard ${i + 1}/2)`, paths: (names[0] && names[0].startsWith('(')) ? ['.claude/skills/'] : names.map(n => `.claude/skills/${n}/SKILL.md`),
    focus: 'Description triggering quality + internal contradictions (e.g. a skill claiming "no API key / pure DSP" that actually calls a Gemini tool; wrong [L]/[G] server attribution; stale status). Link/frontmatter mechanics are covered by other units — focus on prose accuracy + contradictions.' })),
]

let units = [...CODE_UNITS, ...DOC_STATIC, ...DOC_DYNAMIC]
if (scope === 'code') units = units.filter(u => u.kind === 'code')
if (scope === 'docs') units = units.filter(u => u.kind === 'docs')
if (focus.length) units = units.filter(u => focus.some(k => u.id.includes(k) || u.area.toLowerCase().includes(k.toLowerCase())))
if (!units.length) return { error: `no units selected for scope=${scope} focus=[${focus.join(',')}]` }
log(`review units: ${units.length} (${units.map(u => u.id).join(', ')})`)

// Phase 2: Review -> Verify (pipeline; no inter-stage barrier)
const reviewPrompt = u =>
  `You are a meticulous, senior ${u.kind === 'code' ? 'CODE' : 'DOCUMENTATION'} reviewer auditing the ship-studios repo. You are STRICTLY READ-ONLY: never Edit/Write/mutate.\n\n` +
  `REVIEW UNIT: ${u.id} — ${u.area}\nSCOPE (review ONLY these paths): ${u.paths.join(', ')}\nHUNT FOR: ${u.focus}\n\n` +
  GROUND_TRUTH + '\n\n' +
  'METHOD:\n' +
  '1. Read every in-scope file IN FULL (Read; use Grep/Glob/Bash to locate). ' +
  (u.kind === 'code'
    ? 'You MAY run READ-ONLY grounding scoped exactly as CI: `uv run ruff check <file>`, `uv run mypy ship_studios drum_prep`, `uv run pytest -k <name> -q`. If `uv`/env is unavailable, fall back to static analysis and record grounded_by accordingly.\n'
    : 'You MAY run grep/ripgrep + ls to verify names/links/twins mechanically.\n') +
  '2. For each REAL problem record a finding with a precise file:line, the exact quoted offending text as evidence, why it is wrong/impactful, and a concrete fix.\n' +
  '3. Prefer FEW HIGH-QUALITY findings. Return AT MOST the 15 most important. If scope is clean, return an empty findings array (a valid, valuable result).\n' +
  '4. Set kind to ' + JSON.stringify(u.kind) + ' on every finding.'

const refutePrompt = f =>
  'You are an ADVERSARIAL verifier on a repo review. Default stance: this finding is WRONG until you prove otherwise. READ-ONLY.\n\n' +
  `FINDING:\n- title: ${f.title}\n- category: ${f.category} | claimed severity: ${f.severity}\n- location: ${f.file}:${f.line}\n- evidence: ${f.evidence}\n- why: ${f.why}\n- proposed fix: ${f.fix}\n\n` +
  GROUND_TRUTH + '\n\n' +
  'DO:\n1. Open the file and locate line ' + f.line + ' / the cited text. If you CANNOT locate it, return verdict=refuted, located=false (kill hallucinated locations).\n' +
  '2. Try hard to refute: false positive? already handled? out-of-scope (excluded dir)? misreading? mis-severitied?\n' +
  '3. Ground by actually reading the file (and for code, optionally the one relevant ruff/mypy/pytest command).\n' +
  '4. Return confirmed / refuted / needs-human; you may downgrade via adjusted_severity even when confirming.'

const reviewStage = async (u) => {
  const r = await agent(reviewPrompt(u), { label: `review:${u.id}`, phase: 'Review', schema: FINDINGS, agentType: 'Explore' })
  if (!r) { log(`⚠ unit ${u.id} returned no result`); return null }
  const findings = (r.findings || []).map((f, i) => ({ ...f, id: `${u.id}#${i}`, unit: u.id, unitArea: u.area }))
  log(`review ${u.id}: ${findings.length} finding(s)`)
  return { unit: u, findings }
}

const verifyStage = async (rev) => {
  if (!rev) return null
  const tight = !!(budget.total && budget.remaining() < budget.total * 0.2)
  const verified = await parallel(rev.findings.map(f => async () => {
    const n = verifiersFor(f.severity, tight)
    if (n === 0) return { ...f, verified: false, status: 'unverified', adjusted_severity: f.severity }
    const verdicts = (await parallel(Array.from({ length: n }, (_, k) => () =>
      agent(refutePrompt(f), { label: `verify:${f.id}:${k}`, phase: 'Verify', schema: VERDICT, agentType: 'Explore' }),
    ))).filter(Boolean)
    if (!verdicts.length) return { ...f, verified: false, status: 'unverified', adjusted_severity: f.severity }
    const confirmed = verdicts.filter(v => v.verdict === 'confirmed').length
    const refuted = verdicts.filter(v => v.verdict === 'refuted').length
    const sevs = verdicts.map(v => v.adjusted_severity).filter(Boolean)
    const adj = sevs.length ? sevs.reduce((a, b) => (sev(b) < sev(a) ? b : a)) : f.severity
    const hi = f.severity === 'critical' || f.severity === 'high'
    let status
    if (confirmed > refuted) status = 'confirmed'
    else if (confirmed === refuted && hi) status = 'disputed'
    else status = 'refuted'
    return { ...f, verified: true, status, confirmed, refuted, adjusted_severity: adj, verify_notes: verdicts.map(v => v.rationale).join(' | ') }
  }))
  return verified.filter(Boolean)
}

phase('Review')
const reviewed = (await pipeline(units, reviewStage, verifyStage)).filter(Boolean)
const allFindings = reviewed.flat().filter(Boolean)
const kept = allFindings.filter(f => f.status !== 'refuted')
const deduped = dedupe(kept)
const refutedCount = allFindings.length - kept.length
log(`findings: ${allFindings.length} raw, ${refutedCount} refuted, ${deduped.length} after dedupe`)

// Phase 3: Synthesize
phase('Synthesize')
const coveredPaths = Array.from(new Set(units.flatMap(u => u.paths)))
const critic = await agent(
  'You assess COVERAGE of a repo review (read-only). Compare the repo file inventory against the paths the review units covered, and list files/areas that NO unit reviewed (note whether each is intentionally out of scope, e.g. scripts/, presets/, demo/, generated files).\n\n' +
  `INVENTORY: ${JSON.stringify({ codeFiles: (inv && inv.codeFiles) || [], testFiles: (inv && inv.testFiles) || [], docFiles: (inv && inv.docFiles) || [], skills: ((inv && inv.skills) || []).length, vstGuides: (inv && inv.vstGuides) || [] })}\n\n` +
  `COVERED PATH PREFIXES: ${JSON.stringify(coveredPaths)}\n` +
  `UNIT IDS: ${JSON.stringify(units.map(u => u.id))}\n\n` +
  'Return uncovered_files + gaps + notes.',
  { label: 'coverage-critic', phase: 'Synthesize', schema: COVERAGE, agentType: 'Explore' },
)

const totals = { critical: 0, high: 0, medium: 0, low: 0, nit: 0 }
deduped.forEach(f => { const s = f.adjusted_severity || f.severity; if (s in totals) totals[s]++ })
const disputed = deduped.filter(f => f.status === 'disputed').length
log(`totals: ${JSON.stringify(totals)} | disputed=${disputed}`)

const report = await agent(
  'You are the report writer for a repo code+docs review. Write a clear, prioritized Markdown report and SAVE it (use Bash `mkdir -p` for the parent dir, then Write).\n\n' +
  `OUTPUT PATH: ${OUT}\nSCOPE: ${scope}\nSEVERITY TOTALS: ${JSON.stringify(totals)} (disputed=${disputed})\n\n` +
  'STRUCTURE:\n' +
  '1. Title + one-paragraph executive summary + a severity totals table.\n' +
  '2. "## Code Review" — confirmed findings grouped by severity (critical→nit). Each: `### [SEV] title` then file:line, an evidence code block, **Why**, **Fix**.\n' +
  '3. "## Documentation Review" — same format for docs findings.\n' +
  '4. "## Disputed (needs human judgment)" — the status=disputed findings.\n' +
  '5. "## Minor / unverified" — low/nit + unverified findings, condensed (one line each).\n' +
  '6. "## Coverage & gaps" — from the coverage data.\n' +
  '7. "## Method" — note the workflow, the adversarial verification, and that sibling MCP servers were absent in this worktree.\n\n' +
  `FINDINGS JSON (already deduped + verified): ${JSON.stringify(deduped)}\n\n` +
  `COVERAGE JSON: ${JSON.stringify(critic || {})}\n\n` +
  'Do not invent findings beyond the JSON. Return report_path, written, and a 3-5 sentence summary.',
  { label: 'report-writer', phase: 'Synthesize', schema: REPORT, agentType: 'general-purpose' },
)

// Phase 4: opt-in safe mechanical fixes
let fixResult = null
if (FIX) {
  phase('Fix')
  const SAFE_CATS = ['link-integrity', 'tool-name', 'frontmatter', 'prose']
  const SAFE_SEV = ['low', 'nit', 'medium']
  const safe = deduped.filter(f => f.status !== 'disputed' && SAFE_CATS.includes(f.category) && SAFE_SEV.includes(f.adjusted_severity || f.severity))
  if (!safe.length) { log('fix: no safe mechanical findings to apply'); fixResult = { applied: [], skipped: [], notes: 'none eligible' } }
  else {
    fixResult = await agent(
      'You apply ONLY safe, mechanical fixes from a review (read each file first; make the minimal edit; verify; touch nothing else). Then append an "## Auto-fixes applied" section to the report file.\n\n' +
      `REPORT FILE: ${OUT}\n` +
      'ELIGIBLE FIXES (apply only these; skip anything that needs judgment or is ambiguous): ' + JSON.stringify(safe.map(f => ({ id: f.id, file: f.file, line: f.line, category: f.category, evidence: f.evidence, fix: f.fix }))) + '\n\n' +
      'Rules: do NOT change code logic, DSP numerics, tool-call order, or anything beyond the listed mechanical fix. If a fix is risky, skip it with a reason. Return applied + skipped + notes.',
      { label: 'safe-fixer', phase: 'Fix', schema: FIXLOG, agentType: 'general-purpose' },
    )
    log(`fix: applied=${(fixResult && fixResult.applied || []).length} skipped=${(fixResult && fixResult.skipped || []).length}`)
  }
}

return {
  report_path: (report && report.report_path) || OUT,
  written: !!(report && report.written),
  scope,
  totals,
  disputed,
  total_findings: deduped.length,
  refuted: refutedCount,
  coverage_gaps: (critic && critic.uncovered_files || []).length,
  fixes: fixResult,
  summary: (report && report.summary) || null,
}
