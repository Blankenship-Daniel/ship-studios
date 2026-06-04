export const meta = {
  name: 'harmony',
  description: 'Integration review of the RECENT MERGE WINDOW on main — verifies parallel-merged PRs "play nicely together." Enumerates the commit window (git), re-runs the deterministic GATE on the merged tip (pytest/ruff/mypy/lint_skills) to catch union-breakage no single-PR CI sees, fans out one read-only agent per INTEGRATION dimension (gate-failure-triage, pipeline-lockstep-drift, skill-doc-semantic-conflict, rename-vs-references, name-slug-collision, dep-lockfile-coherence, cross-pr-logic-conflict) scoped to the changed-file subset + in-window commits, composes /audit-pipeline-lockstep + /audit-skill-consistency for the mechanical drift, adversarially verifies each finding, and synthesizes a prioritized report. Distinct from /repo-review (whole-repo, not window-scoped). args = { since?, head?, window?(default 8), gate?(default true), live?(default false), fix?(default false), out?(default "reviews/HARMONY-REVIEW.md"), changedFiles?, commits?, prs?, gateResults?, dimensions? }.',
  whenToUse: 'After several parallel agent-worktree PRs merged to main and you want to catch cross-PR INTEGRATION problems no single-PR review sees. Pairs with /repo-review-fix to apply the findings.',
  phases: [
    { title: 'Window',     detail: 'ONE agent enumerates the recent merge window (git): SINCE..HEAD, changed files→commit attribution, in-window PRs' },
    { title: 'Gate',       detail: 'ONE serial agent re-runs the deterministic gate on the merged tip (pytest/ruff/mypy/lint_skills [+live]) — the union-breakage check' },
    { title: 'Review',     detail: 'one read-only agent per INTEGRATION dimension over the changed-file subset (two compose the existing audits), then adversarial refuters per finding' },
    { title: 'Synthesize', detail: 'dedupe, coverage-critic, write the prioritized HARMONY report' },
    { title: 'Fix',        detail: 'opt-in: apply only safe mechanical fixes (mirrors repo-review)' },
  ],
}

// ---- args (defensive: may arrive as object OR JSON string) --------------------------------------
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const SINCE = A.since || null
const HEAD = A.head || 'HEAD'
const WINDOW = (Number.isInteger(A.window) && A.window > 0) ? A.window : 8
const GATE_ON = A.gate !== false
const LIVE = !!A.live
const FIX = !!A.fix
const OUT = A.out || 'reviews/HARMONY-REVIEW.md'
let changedFiles = Array.isArray(A.changedFiles) ? A.changedFiles : null
let gateResults = A.gateResults || null
log(`harmony: since=${SINCE || `last ${WINDOW} merges`} head=${HEAD} gate=${GATE_ON} live=${LIVE} fix=${FIX} out=${OUT}`)

// ---- schemas (all additionalProperties:false) --------------------------------------------------
const WINDOW_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    since: { type: 'string', description: 'resolved start ref/sha (exclusive)' },
    head:  { type: 'string' },
    range: { type: 'string', description: '"<since>..<head>"' },
    prCount: { type: 'number' },
    prs: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { sha: { type: 'string' }, title: { type: 'string' } }, required: ['sha', 'title'] } },
    changedFiles: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: {
        path: { type: 'string' },
        status: { type: 'string', description: 'A/M/D/R (most significant)' },
        commits: { type: 'array', items: { type: 'string' }, description: 'non-merge shas that touched it' },
      }, required: ['path', 'status', 'commits'] } },
    notes: { type: 'string' },
  },
  required: ['since', 'head', 'range', 'changedFiles'],
}

const GATE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pytest:     { type: 'string', description: 'pass/fail counts + every FAILED node id' },
    ruff:       { type: 'string' },
    mypy:       { type: 'string' },
    lintSkills: { type: 'string', description: 'scripts/lint_skills.py output / clean' },
    live:       { type: 'string', description: 'live-contract result, or "not run" / "skipped (siblings absent)"' },
    pass:       { type: 'boolean', description: 'true ONLY if pytest+ruff+mypy+lint_skills all clean' },
    failures:   { type: 'array', items: { type: 'string' }, description: 'every failure "file:line — what"' },
    unionBreakage: { type: 'array', items: { type: 'string' }, description: 'failures that would NOT occur on any single in-window PR alone' },
    notes:      { type: 'string' },
  },
  required: ['pytest', 'ruff', 'mypy', 'lintSkills', 'pass', 'failures'],
}

const FINDINGS = {
  type: 'object', additionalProperties: false,
  properties: {
    findings: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        title:    { type: 'string', description: 'one specific line, no fluff' },
        category: { type: 'string', enum: ['gate-union-break', 'pipeline-lockstep', 'skill-doc-conflict', 'rename-vs-ref', 'name-collision', 'dep-coherence', 'cross-pr-logic', 'consistency', 'other'] },
        severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'nit'] },
        file:     { type: 'string', description: 'repo-relative PRIMARY location' },
        line:     { type: 'integer', description: '0 if not line-specific' },
        evidence: { type: 'string', description: 'exact quoted offending text' },
        why:      { type: 'string', description: 'why it breaks the merged union' },
        fix:      { type: 'string', description: 'concrete suggested fix' },
        commits:  { type: 'array', items: { type: 'string' }, description: 'in-window shas that introduced/interact in this finding' },
        crossPR:  { type: 'boolean', description: 'true = genuine interaction of ≥2 in-window changes; false = single-PR bug surfaced in-window' },
        confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
      },
      required: ['title', 'category', 'severity', 'file', 'line', 'evidence', 'why', 'fix', 'commits', 'crossPR', 'confidence'],
    } },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object', additionalProperties: false,
  properties: {
    verdict:           { type: 'string', enum: ['confirmed', 'refuted', 'needs-human'] },
    located:           { type: 'boolean', description: 'did you find the cited file:line?' },
    inWindow:          { type: 'boolean', description: 'are the cited commits within the review range (not pre-existing)?' },
    adjusted_severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'nit'] },
    rationale:         { type: 'string', description: 'what you checked; quote the line you read' },
    grounded_by:       { type: 'string', enum: ['read-file', 'git-log', 'ran-ruff', 'ran-mypy', 'ran-pytest', 'grep', 'none'] },
  },
  required: ['verdict', 'located', 'inWindow', 'adjusted_severity', 'rationale', 'grounded_by'],
}

const COVERAGE = {
  type: 'object', additionalProperties: false,
  properties: {
    uncovered_files: { type: 'array', items: { type: 'string' }, description: 'changed files no dimension reviewed' },
    gaps:            { type: 'array', items: { type: 'string' } },
    notes:           { type: 'string' },
  },
  required: ['uncovered_files', 'gaps'],
}

const REPORT = {
  type: 'object', additionalProperties: false,
  properties: {
    report_path: { type: 'string' },
    written:     { type: 'boolean' },
    summary:     { type: 'string', description: '3-5 sentence executive summary + the one-line integration verdict' },
  },
  required: ['report_path', 'written', 'summary'],
}

const FIXLOG = {
  type: 'object', additionalProperties: false,
  properties: {
    applied: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, change: { type: 'string' } }, required: ['file', 'change'] } },
    skipped: { type: 'array', items: { type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, reason: { type: 'string' } }, required: ['file', 'reason'] } },
    notes:   { type: 'string' },
  },
  required: ['applied', 'skipped'],
}

// ---- shared ground truth (harmony preamble + the repo-review block) ------------------------------
const GROUND_TRUTH =
  'HARMONY GROUND TRUTH — only flag REAL cross-change INTEGRATION issues:\n' +
  '- You are reviewing the recent MERGE WINDOW, not the whole repo. A pre-existing issue untouched by an in-window commit is OUT OF SCOPE (that is /repo-review).\n' +
  '- Prefer findings where ≥2 in-window changes INTERACT (a rename in PR-A breaks a reference added in PR-B; two PRs add the same skill/slug/tool name; a dep bump in PR-A breaks code added in PR-B; one PR reorders a pipeline, another asserts the old order). Single-PR bugs are LOWER priority here unless the merge UNION surfaces them.\n' +
  '- A green per-PR CI does NOT prove the union is green — that is exactly what the Gate phase re-checks on the merged tip.\n' +
  '- The merged-tip GATE (pytest/ruff/mypy/lint_skills) is the hub\'s OFFLINE suite — it needs NO siblings/API keys and runs fine in a worktree. Only the optional --live contract test is siblings-gated. So if the gate was SKIPPED, it is because --no-gate was passed, NOT because siblings are absent — never attribute a skipped gate to absent siblings.\n' +
  '- The ../stemmy-loops-mcp / ../stemmy-gemini-mcp siblings are ABSENT in this worktree; never require them — degrade gracefully.\n' +
  '\n' +
  'REPO GROUND TRUTH — do NOT flag these as issues:\n' +
  '- ship_studios/pipelines.py has 5 user-facing async pipelines (master_track, mix_check, reference_match, loops_to_deliverables, understand_audio) + 4 helpers (batch_master, house_curve, stem_master, unmask_stems) = 9 async fns. CLAUDE.md\'s "six lifecycle stages" and the "Canonical pipelines" section are DIFFERENT taxonomies — 6-vs-5 is NOT a drift.\n' +
  '- ruff line-length is 100 and EXCLUDES scripts/, presets/, projects/. mypy targets ONLY ship_studios + drum_prep (py3.12). pytest asyncio_mode=auto, testpaths=["tests"]. Findings inside excluded dirs are OUT OF SCOPE.\n' +
  '- docs/vst/ plugin field guides each have a twin [[<plugin>]] skill; pipeline FUNCTION names (master_track) and python script names (apply_vst_preset.py) legitimately use underscores — only MCP TOOL names use hyphens.'

// ---- helpers (deterministic; no Date.now / Math.random) -----------------------------------------
const RANK = { critical: 0, high: 1, medium: 2, low: 3, nit: 4 }
const sev = s => (s in RANK ? RANK[s] : 5)
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)

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
      cur.commits = Array.from(new Set([...(cur.commits || []), ...(f.commits || [])]))
      cur.crossPR = cur.crossPR || f.crossPR
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

// ================================================================================================
// Phase 1: Window
// ================================================================================================
phase('Window')
let win
if (changedFiles && changedFiles.length) {
  win = {
    since: SINCE || '(caller-supplied)', head: HEAD,
    range: `${SINCE || '(caller-supplied)'}..${HEAD}`,
    prCount: (A.prs || []).length, prs: A.prs || [], changedFiles, notes: 'caller-supplied changedFiles',
  }
  log(`window: caller-supplied (${changedFiles.length} changed files)`)
} else {
  win = await agent(
    'You are a read-only git historian. Working dir = the repo root. Compute the recent MERGE WINDOW on `' + HEAD + '`.\n' +
    'STEPS (use Bash, read-only — never commit/checkout/mutate):\n' +
    (SINCE
      ? `1. SINCE is provided: "${SINCE}". Use it as the exclusive window start.\n`
      : `1. Find the window start: \`git log --merges -n ${WINDOW} --format=%H ${HEAD}\`. Take the LAST (oldest) sha S; set SINCE = "S^1" (the commit just before that oldest in-window merge). If there are fewer than ${WINDOW} merges in history, set SINCE to the root commit (\`git rev-list --max-parents=0 ${HEAD} | tail -1\`).\n`) +
    '2. range = "<SINCE>..' + HEAD + '".\n' +
    '3. PRs: `git log --merges <range> --format="%H %s"` → prs[] = {sha, title}. (Titles look like "Merge pull request #NN from <branch>".)\n' +
    '4. Changed files: `git log --no-merges --name-status <range>`. Aggregate per file → { path, status (A/M/D/R; for a rename use R and report the NEW path), commits:[the non-merge shas that touched it] }. Report EVERY changed path (the review depends on completeness). If a file was renamed, note the old→new in the status detail of `notes`.\n' +
    'Return the WINDOW object. If the range is empty (no commits), return changedFiles:[] with an explanatory note.',
    { label: 'window', phase: 'Window', schema: WINDOW_SCHEMA, agentType: 'Explore' },
  )
}
if (!win || !(win.changedFiles || []).length) {
  log('window empty — nothing to review')
  return { error: 'no changes in window', range: win && win.range, head: HEAD }
}
changedFiles = win.changedFiles
const prs = win.prs || []
const range = win.range
const prCount = win.prCount || prs.length
log(`window: ${range} — ${prCount} PRs, ${changedFiles.length} changed files`)

// ================================================================================================
// Phase 2: Gate (single serial agent — honest ground truth; concurrent runs would race the env)
// ================================================================================================
phase('Gate')
let gate = gateResults
if (GATE_ON && !gate) {
  gate = await agent(
    'You are the CI gate for the ship-studios repo, RE-RUN ON THE MERGED TIP (`' + HEAD + '`) — read-only verification, do NOT fix anything. Working dir = repo root. Run, in order, and capture the TAIL of each:\n' +
    '1. `uv sync --extra drum-prep` (provision DSP test deps + dev tools).\n' +
    '2. `uv run --no-sync pytest -q` (FULL offline suite). Report pass/fail counts + every FAILED node id.\n' +
    '3. `uv run --no-sync ruff check` (report any violation file:line).\n' +
    '4. `uv run --no-sync mypy` (report any error file:line).\n' +
    '5. `uv run --no-sync python scripts/lint_skills.py` (skill/doc contract lint: wikilinks resolve, frontmatter present, [G]-keyless label bug). Report its output (exit 0 = clean).\n' +
    (LIVE
      ? '6. `SHIP_STUDIOS_LIVE_CONTRACT=1 uv run --no-sync pytest tests/test_pipelines.py -k live` — opens the REAL sibling servers IF present. It SELF-SKIPS when ../stemmy-*-mcp are absent — a skip is EXPECTED here and is NOT a failure (record it in `live`).\n'
      : '(live-contract test NOT requested — do not run it; set live="not run".)\n') +
    'If `uv` is unavailable, say so explicitly and fall back to `python3 -m pytest` / `python3 -m ruff` etc., noting it in `notes` — do NOT fail the whole gate on tooling absence.\n' +
    'For EACH failure, classify it: a UNION-BREAKAGE is a failure that would NOT happen on any single in-window PR alone — a name/symbol clash, a duplicate definition, a half-merged import, a test asserting an order another PR changed, a dependency two PRs bumped differently. List those in unionBreakage[]; pre-existing / single-PR failures go in failures[] only (a failure can appear in both if it is both new AND union-caused).\n' +
    'Set pass=true ONLY if pytest + ruff + mypy + lint_skills are all clean. Return the GATE object.',
    { label: 'gate', phase: 'Gate', schema: GATE_SCHEMA, agentType: 'general-purpose' },
  )
} else if (!GATE_ON) {
  log('gate skipped (--no-gate)')
}
if (gate) log(`gate: pass=${gate.pass} failures=${(gate.failures || []).length} unionBreakage=${(gate.unionBreakage || []).length}`)

const gateMd = gate
  ? 'MERGED-TIP GATE (ground truth — already run; do NOT re-run it):\n' +
    `- pass: ${gate.pass}\n- pytest: ${gate.pytest}\n- ruff: ${gate.ruff}\n- mypy: ${gate.mypy}\n- lint_skills: ${gate.lintSkills || 'n/a'}\n` +
    (gate.live ? `- live-contract: ${gate.live}\n` : '') +
    ((gate.failures || []).length ? `- failures: ${gate.failures.join(' | ')}\n` : '') +
    ((gate.unionBreakage || []).length ? `- UNION-BREAKAGE: ${gate.unionBreakage.join(' | ')}\n` : '')
  : 'GATE SKIPPED (--no-gate): the merged-tip suite was not re-run; do NOT assume the union is green.'

// ================================================================================================
// Phase 3: Review -> Verify (pipeline; no inter-stage barrier)
// ================================================================================================
const paths = changedFiles.map(f => f.path)
const touched = re => paths.some(p => re.test(p))
const hasNewOrRenamed = changedFiles.some(f => { const s = (f.status || '')[0]; return s === 'A' || s === 'R' })
const gateFailed = !!(gate && gate.pass === false)
const changedSkillDirs = Array.from(new Set(
  paths.map(p => { const m = /^\.claude\/skills\/([^/]+)\//.exec(p); return m ? m[1] : null }).filter(Boolean)))

const ALL_DIMS = [
  { id: 'gate-failure-triage', area: 'gate failures on the merged tip', active: gateFailed,
    focus: 'For EACH entry in the gate ground-truth failures / unionBreakage above, find the in-window commit(s) that caused it (git log/show on the implicated files), classify union-break vs single-PR, and give the root cause + a concrete fix. Set crossPR=true and category=gate-union-break for union-breaks.' },
  { id: 'pipeline-lockstep-drift', area: 'CLAUDE.md ↔ pipelines.py ↔ test_pipelines.py', delegate: 'lockstep',
    active: touched(/^ship_studios\/pipelines\.py$/) || touched(/^tests\/test_pipelines\.py$/) || touched(/^CLAUDE\.md$/),
    focus: '(delegated to /audit-pipeline-lockstep) ordered tool-call drift across prose ↔ code ↔ test introduced by the merge.' },
  { id: 'skill-doc-semantic-conflict', area: 'skill/doc coherence + semantic conflicts', delegate: 'skill',
    active: touched(/^\.claude\/skills\//) || touched(/^docs\//) || touched(/^CLAUDE\.md$/),
    focus: 'BEYOND the mechanical lint (delegated to /audit-skill-consistency for the changed skills): two in-window edits that produce CONTRADICTORY or DUPLICATED CLAUDE.md prose; two new/edited skills with colliding or overlapping trigger phrases; a skill whose guidance now contradicts another in-window change; a doc claim a sibling in-window change made false. Read both sides of each suspected conflict.' },
  { id: 'rename-vs-references', area: 'renames vs stale references', active: true,
    focus: 'A tool / skill / function / class / wikilink target / CLI flag / config key / env var RENAMED or REMOVED by one in-window commit but still REFERENCED (import, call, [[wikilink]], CLAUDE.md tool table, pipeline tool-call, doc, test) by another in-window change or a stale doc the merge left behind. Grep BOTH the new name and the old name across the whole tree; the dangling reference is the finding.' },
  { id: 'name-slug-collision', area: 'duplicate names/slugs added in parallel', active: hasNewOrRenamed,
    focus: 'Two in-window changes (or a new thing vs the existing tree) that introduce the SAME skill dir name, skill `name:` frontmatter slug, workflow `name`, MCP tool name, [[wikilink]] target, memory slug, or a duplicate Python function/class/test name; or a new name that SHADOWS an existing symbol. List the colliding paths + the commits.' },
  { id: 'dep-lockfile-coherence', area: 'pyproject.toml / uv.lock coherence', active: touched(/^pyproject\.toml$/) || touched(/^uv\.lock$/),
    focus: 'Two in-window changes that bump/add CONFLICTING dependency versions or extras; uv.lock out of sync with pyproject.toml; a new import added by one PR not covered by another PR\'s dependency/extra change; extra/optional-group gating drift. (The gate above is the ground truth for whether the union actually installs + imports.)' },
  { id: 'cross-pr-logic-conflict', area: 'cross-PR logic / contract conflicts', active: changedFiles.length > 1,
    focus: 'Semantic interactions a per-PR review misses: two in-window commits editing adjacent logic in the SAME module with incompatible assumptions; a function/contract/constant one PR changed that another PR\'s in-window change now violates; a shared config/constant edited two different ways; a behavior one PR\'s test asserts that another PR\'s code change breaks. Read BOTH sides of each suspected interaction before flagging; set crossPR=true.' },
]
let dims = ALL_DIMS.filter(d => d.active)
if (Array.isArray(A.dimensions) && A.dimensions.length) dims = dims.filter(d => A.dimensions.includes(d.id))
log(`integration dimensions: ${dims.length} active (${dims.map(d => d.id).join(', ') || 'none'})`)

const tag = (u, arr) => (arr || []).map((f, i) => ({ ...f, id: `${u.id}#${i}`, unit: u.id, unitArea: u.area }))

const reviewPrompt = u =>
  'You are a meticulous, senior INTEGRATION reviewer of the ship-studios repo\'s RECENT MERGE WINDOW. STRICTLY READ-ONLY: never Edit/Write/mutate.\n\n' +
  `REVIEW WINDOW: ${range} (${prCount} merged PRs).\nDIMENSION: ${u.id} — ${u.area}\nHUNT FOR: ${u.focus}\n\n` +
  `CHANGED FILES IN WINDOW (path, status, attributing commits):\n${JSON.stringify(changedFiles)}\n\n` +
  `PRs IN WINDOW:\n${JSON.stringify(prs)}\n\n` +
  GROUND_TRUTH + '\n\n' + gateMd + '\n\n' +
  'METHOD:\n' +
  '1. Inspect the in-window diffs with READ-ONLY git: `git show <sha> -- <file>`, `git diff ' + range + ' -- <file>`, `git log ' + range + ' -- <file>`, plus Read/Grep on the current files. Grep the WHOLE tree for cross-references, not just the changed files.\n' +
  '2. Flag ONLY real cross-change INTEGRATION problems that fit THIS dimension. A pre-existing issue untouched by an in-window commit is OUT OF SCOPE. Prefer findings where ≥2 in-window changes interact — set crossPR=true and list the attributing commits in `commits`. A genuine single-PR bug the union surfaced may be crossPR=false.\n' +
  '3. Each finding: a precise file:line, the exact quoted offending text as evidence, why it breaks the merged union, a concrete fix, and the commit shas involved.\n' +
  '4. Prefer FEW HIGH-QUALITY findings (return AT MOST 12). An empty findings array is a valid, valuable result.'

const refutePrompt = f =>
  'You are an ADVERSARIAL verifier on an integration review of a recent merge window. Default stance: this finding is WRONG until you prove otherwise. READ-ONLY.\n\n' +
  `REVIEW RANGE: ${range}\n` +
  `FINDING:\n- title: ${f.title}\n- category: ${f.category} | claimed severity: ${f.severity} | crossPR: ${f.crossPR}\n- location: ${f.file}:${f.line}\n- commits: ${(f.commits || []).join(', ') || '(none cited)'}\n- evidence: ${f.evidence}\n- why: ${f.why}\n- proposed fix: ${f.fix}\n\n` +
  GROUND_TRUTH + '\n\n' +
  'DO:\n1. Open the file and locate line ' + f.line + ' / the cited text. If you CANNOT locate it, return verdict=refuted, located=false (kill hallucinated locations).\n' +
  '2. Confirm IN-WINDOW: are the cited commits within ' + range + ' (e.g. `git merge-base --is-ancestor <sha> ' + HEAD + '` and not an ancestor of the range start)? If the issue PRE-DATES the window (not touched by any in-window commit) → set inWindow=false and verdict=refuted (out of scope; that is /repo-review).\n' +
  '3. Try hard to refute: false positive? already handled elsewhere? out-of-scope (excluded dir)? a misreading? mis-severitied? not actually a cross-change interaction?\n' +
  '4. Ground by actually reading the file + the relevant git diff (and for code, optionally one ruff/mypy/pytest command).\n' +
  '5. Return confirmed / refuted / needs-human; you may downgrade via adjusted_severity even when confirming.'

const mapSeverity = s => (s === 'error' ? 'high' : 'low')

const lockstepUnit = async (u) => {
  const sub = await workflow('audit-pipeline-lockstep', {})
  const raw = []
  ;(sub && sub.results || []).forEach(r => (r.issues || []).forEach(iss => raw.push({
    title: `pipeline lockstep drift: ${r.pipeline} (${iss.class})`,
    category: 'pipeline-lockstep', severity: mapSeverity(iss.severity),
    file: 'ship_studios/pipelines.py', line: 0, evidence: iss.detail,
    why: `prose ↔ code ↔ test drift for the "${r.pipeline}" pipeline surfaced in the merge window`,
    fix: 'reconcile CLAUDE.md "Canonical pipelines" prose ↔ pipelines.py ↔ tests/test_pipelines.py to one ordered tool-call sequence',
    commits: [], crossPR: false, confidence: 'medium', _delegated: true,
  })))
  log(`review ${u.id} (delegated): ${raw.length} finding(s)`)
  return { unit: u, findings: tag(u, raw) }
}

const skillUnit = async (u) => {
  // (a) mechanical drift on the changed skills via the existing audit
  const out = []
  if (changedSkillDirs.length) {
    const sub = await workflow('audit-skill-consistency', { skills: changedSkillDirs })
    ;(sub && sub.findings || []).forEach(fd => (fd.issues || []).forEach(iss => out.push({
      title: `skill drift: ${fd.skill} (${iss.class})`,
      category: 'skill-doc-conflict', severity: mapSeverity(iss.severity),
      file: `.claude/skills/${fd.skill}/SKILL.md`, line: 0, evidence: `${iss.ref} — ${iss.detail}`,
      why: 'SKILL.md drift in a skill changed during the merge window',
      fix: iss.detail, commits: [], crossPR: false, confidence: 'medium', _delegated: true,
    })))
  }
  // (b) the SEMANTIC layer the lint can't catch (one read-only agent)
  const r = await agent(reviewPrompt(u), { label: `review:${u.id}`, phase: 'Review', schema: FINDINGS, agentType: 'Explore' })
  const semantic = (r && r.findings) || []
  log(`review ${u.id}: ${out.length} mechanical + ${semantic.length} semantic finding(s)`)
  return { unit: u, findings: tag(u, [...out, ...semantic]) }
}

const reviewStage = async (u) => {
  if (u.delegate === 'lockstep') return await lockstepUnit(u)
  if (u.delegate === 'skill') return await skillUnit(u)
  const r = await agent(reviewPrompt(u), { label: `review:${u.id}`, phase: 'Review', schema: FINDINGS, agentType: 'Explore' })
  if (!r) { log(`⚠ dimension ${u.id} returned no result`); return null }
  const findings = tag(u, r.findings)
  log(`review ${u.id}: ${findings.length} finding(s)`)
  return { unit: u, findings }
}

const verifyStage = async (rev) => {
  if (!rev) return null
  const tight = !!(budget.total && budget.remaining() < budget.total * 0.2)
  const verified = await parallel(rev.findings.map(f => async () => {
    // Delegated findings were already agent-verified by the sub-audit; trust them, skip re-refute.
    if (f._delegated) return { ...f, verified: false, status: 'confirmed', adjusted_severity: f.severity }
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
const reviewed = dims.length ? (await pipeline(dims, reviewStage, verifyStage)).filter(Boolean) : []
const allFindings = reviewed.flat().filter(Boolean)
const kept = allFindings.filter(f => f.status !== 'refuted')
const deduped = dedupe(kept)
const refutedCount = allFindings.length - kept.length
log(`findings: ${allFindings.length} raw, ${refutedCount} refuted, ${deduped.length} after dedupe`)

// ================================================================================================
// Phase 4: Synthesize
// ================================================================================================
phase('Synthesize')
const critic = await agent(
  'You assess COVERAGE of an integration review of a merge window (read-only). Compare the changed-file list against the dimensions that ran, and list changed files that NO dimension reviewed (note whether each is intentionally low-risk, e.g. a lockfile, a generated file, scratch under artifacts/).\n\n' +
  `REVIEW RANGE: ${range}\nCHANGED FILES: ${JSON.stringify(paths)}\n` +
  `DIMENSIONS THAT RAN: ${JSON.stringify(dims.map(d => d.id))}\n` +
  `GATE: ${gate ? `pass=${gate.pass}` : 'skipped'}\n\n` +
  'Return uncovered_files + gaps + notes.',
  { label: 'coverage-critic', phase: 'Synthesize', schema: COVERAGE, agentType: 'Explore' },
)

const totals = { critical: 0, high: 0, medium: 0, low: 0, nit: 0 }
deduped.forEach(f => { const s = f.adjusted_severity || f.severity; if (s in totals) totals[s]++ })
const disputed = deduped.filter(f => f.status === 'disputed').length
const crossPRCount = deduped.filter(f => f.crossPR).length
const unionBreakages = (gate && gate.unionBreakage || []).length
log(`totals: ${JSON.stringify(totals)} | crossPR=${crossPRCount} | unionBreak=${unionBreakages} | disputed=${disputed}`)

const report = await agent(
  'You are the report writer for an INTEGRATION review of a recent merge window. Write a clear, prioritized Markdown report and SAVE it (use Bash `mkdir -p` for the parent dir, then Write).\n\n' +
  `OUTPUT PATH: ${OUT}\nREVIEW RANGE: ${range}\nSEVERITY TOTALS: ${JSON.stringify(totals)} (disputed=${disputed}, crossPR=${crossPRCount})\n\n` +
  'STRUCTURE:\n' +
  '1. Title + one-paragraph executive summary + a severity totals table + a **Window header**: the range, the list of in-window PRs (sha + title), and the GATE verdict (pass/fail; union-breakage count).\n' +
  '2. "## Union-breakage (merged-tip gate)" — THE HEADLINE: the gate failures + every crossPR/gate-union-break finding. If the gate passed and there are none, say so plainly.\n' +
  '3. "## Cross-PR interaction findings" — crossPR:true findings grouped by severity (critical→nit). Each as a line `file:line — [SEV] title` then an evidence code block, **Why**, **Fix**, and **Commits** (which PRs/shas interact).\n' +
  '4. "## Single-PR findings surfaced in-window" — crossPR:false findings, condensed (one line each, same `file:line — [SEV] … FIX: …` format).\n' +
  '5. "## Disputed (needs human judgment)" — status=disputed findings.\n' +
  '6. "## Minor / unverified" — low/nit + unverified, condensed.\n' +
  '7. "## Coverage & gaps" — from the coverage data (changed files no dimension reviewed).\n' +
  '8. "## Method" — the window strategy (last-N-merges or --since), the merged-tip gate re-run, the per-dimension fan-out + adversarial verification, and that sibling MCP servers were absent in this worktree.\n' +
  'Use the SAME `file:line — [SEV] … FIX: …` finding-line format as reviews/REPO-REVIEW.md so /repo-review-fix can consume this report.\n\n' +
  `GATE JSON: ${JSON.stringify(gate || { skipped: true })}\n\n` +
  `IN-WINDOW PRs: ${JSON.stringify(prs)}\n\n` +
  `FINDINGS JSON (deduped + verified): ${JSON.stringify(deduped)}\n\n` +
  `COVERAGE JSON: ${JSON.stringify(critic || {})}\n\n` +
  'Do not invent findings beyond the JSON. End the summary with a one-line verdict: "integration-healthy" (gate green + no confirmed crossPR criticals/highs) or "integration-broken" otherwise. Return report_path, written, and a 3-5 sentence summary.',
  { label: 'report-writer', phase: 'Synthesize', schema: REPORT, agentType: 'general-purpose' },
)

// ================================================================================================
// Phase 5: opt-in safe mechanical fixes
// ================================================================================================
let fixResult = null
if (FIX) {
  phase('Fix')
  const SAFE_CATS = ['skill-doc-conflict', 'rename-vs-ref', 'consistency']
  const SAFE_SEV = ['low', 'nit', 'medium']
  const safe = deduped.filter(f => f.status !== 'disputed' && SAFE_CATS.includes(f.category) && SAFE_SEV.includes(f.adjusted_severity || f.severity))
  if (!safe.length) { log('fix: no safe mechanical findings to apply'); fixResult = { applied: [], skipped: [], notes: 'none eligible' } }
  else {
    fixResult = await agent(
      'You apply ONLY safe, mechanical fixes from an integration review (read each file first; make the minimal edit; verify it still parses; touch nothing else; never reformat). Then append an "## Auto-fixes applied" section to the report file.\n\n' +
      `REPORT FILE: ${OUT}\n` +
      'ELIGIBLE FIXES (apply only these; skip anything needing judgment, DSP-behavior changes, tool-call-order changes, or frontmatter `description` edits): ' + JSON.stringify(safe.map(f => ({ id: f.id, file: f.file, line: f.line, category: f.category, evidence: f.evidence, fix: f.fix }))) + '\n\n' +
      'Rules: keep tool-name spellings EXACT (hyphen vs underscore) + [L]/[G] prefixes intact; edit SKILL.md BODY not the YAML frontmatter description; do NOT touch ship_studios/pipelines.py tool-call args (tests assert them). If a fix is risky, skip it with a reason. Return applied + skipped + notes.',
      { label: 'safe-fixer', phase: 'Fix', schema: FIXLOG, agentType: 'general-purpose' },
    )
    log(`fix: applied=${(fixResult && fixResult.applied || []).length} skipped=${(fixResult && fixResult.skipped || []).length}`)
  }
}

return {
  report_path: (report && report.report_path) || OUT,
  written: !!(report && report.written),
  range,
  prCount,
  gate: gate || null,
  totals,
  disputed,
  total_findings: deduped.length,
  refuted: refutedCount,
  crossPR_count: crossPRCount,
  union_breakages: unionBreakages,
  coverage_gaps: (critic && critic.uncovered_files || []).length,
  fixes: fixResult,
  summary: (report && report.summary) || null,
}
