export const meta = {
  name: 'fold-learnings',
  description: "Classify + draft a concrete patch for each candidate SESSION LEARNING in parallel, and adversarially check whether it's already captured or belongs in the proposed home. Phase 1 CLASSIFY fans out one agent per learning — each greps the user-memory store (MEMORY.md + slugs), CLAUDE.md, and the candidate target SKILL.md, applies the routing taxonomy (sharpens one skill -> edit its body; a repeatable how-to -> new skill via /create-skill; N-way parallel -> a new workflow; cross-cutting doctrine -> CLAUDE.md Rules/Field-notes/tool-table; a measured/tool/session-local fact or a preference -> a memory entry), and drafts the EXACT patch text. Phase 2 CHALLENGE fans out one skeptic per route to re-grep and try to prove it redundant or mis-homed. Phase 3 REDUCE merges them into a ranked plan (a block downgrades to needs-decision; already-covered flips to skip). The SESSION harvests the in-context learnings, owns the AskUserQuestion approval gate, and writes every file (workflows can't prompt or touch the fs) — including driving /create-skill for approved new skills. args = { learnings:[{title,detail}|string], memoryDir?, claudeMdPath?, skillsDir?, validSkills?[], validTools?[], validWorkflows?[] }.",
  phases: [
    { title: 'Classify',  detail: 'one agent per learning -> dedupe-grep + route + draft the exact patch' },
    { title: 'Challenge', detail: 'one skeptic per routed learning -> already-covered / wrong-home?' },
    { title: 'Reduce',    detail: 'merge route + challenge into a ranked plan (block -> needs-decision, covered -> skip)' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const learnings = (A.learnings || []).map((l, i) => {
  if (typeof l === 'string') return { title: l.slice(0, 80), detail: l }
  return { title: l.title || `learning ${i + 1}`, detail: l.detail || l.title || '' }
}).filter(l => l.detail)

const memoryDir   = A.memoryDir   || '/Users/ship/.claude/projects/-Users-ship-Documents-code-ship-studios/memory'
const claudeMd    = A.claudeMdPath || 'CLAUDE.md'
const skillsDir   = A.skillsDir   || '.claude/skills'
const validSkills = A.validSkills || []
const validTools  = A.validTools  || []
const validWfs    = A.validWorkflows || []

if (!learnings.length) {
  return { error: 'pass args.learnings = [{title,detail}|string, ...] — the SESSION harvests them in-context first' }
}
const list = a => (a && a.length) ? a.join(', ') : '(none supplied — derive it yourself with ls/grep)'
const lslug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40)
log(`fold-learnings: ${learnings.length} candidate(s) · memory=${memoryDir} · skills=${skillsDir}`)

// The routing taxonomy, shared by both phases (kept identical to the fold-learnings SKILL.md table).
const TAXONOMY =
  `ROUTING (first match wins; the action is usually to EDIT an existing artifact, not just append):\n` +
  `  - sharpens a recipe ONE existing skill owns (gotcha/prereq/corrected fact/link) -> EDIT ${skillsDir}/<n>/SKILL.md (## Pitfalls / ## Prerequisites / a corrected step / ## Related)\n` +
  `  - a reusable MULTI-STEP procedure someone re-runs -> NEW skill (home="new-skill", action="drive-create-skill"; the SESSION drives /create-skill)\n` +
  `  - a PARALLEL fan-out / judge-panel / batch / cross-checked procedure over N items -> NEW ${skillsDir.replace('skills', 'workflows')}/<n>.js (home="new-workflow")\n` +
  `  - REPO-WIDE doctrine (spans many skills / the whole pipeline) -> ${claudeMd} (### Rules bullet · ### Field notes gotcha · a ## Combined tool surface row · a ## Canonical pipelines step)\n` +
  `  - a MEASURED / tool-specific / session-local fact, plugin behaviour, approved signature, API/version finding -> a MEMORY entry (${memoryDir}/<kebab>.md + a MEMORY.md line); memoryType reference (durable how-to) or project (repo state/decision)\n` +
  `  - a USER PREFERENCE / feedback -> MEMORY (memoryType feedback or user), UNLESS it's really a public reusable recipe (then new-skill)\n` +
  `  - a DEPRECATED command/flag -> guidance only (home="defer"): do NOT recreate command wrappers\n` +
  `  - "automate on every X" (hook/agent) -> the repo uses NO hooks and NO durable agents; home="defer" with a recommendation note (only route to settings.json hooks / a new agent on explicit user request)\n` +
  `MNEMONIC: sharpens one skill -> edit its body; repeatable how-to -> new skill; N-way parallel -> workflow; cross-cutting doctrine -> CLAUDE.md; measured/tool/session-local fact or preference -> memory. CLAUDE.md loads every turn — keep it lean; default a bare fact to memory.`

const CLASSIFY = {
  type: 'object',
  additionalProperties: false,
  properties: {
    title:        { type: 'string' },
    home:         { type: 'string', enum: ['memory', 'skill-edit', 'new-skill', 'new-workflow', 'claude-md', 'commands', 'defer'] },
    target:       { type: 'string', description: 'EXACT path + section, e.g. ".claude/skills/de-ess/SKILL.md ## Pitfalls" or "<memoryDir>/<slug>.md" or "CLAUDE.md ### Field notes"' },
    memoryType:   { type: 'string', enum: ['user', 'feedback', 'project', 'reference', ''], description: 'only when home=memory; else ""' },
    action:       { type: 'string', enum: ['create', 'append-section', 'append-bullet', 'drive-create-skill', 'append-index', 'edit-existing', 'recommend'] },
    patch:        { type: 'string', description: 'the EXACT text to write — a full memory file w/ frontmatter + the MEMORY.md index line, the CLAUDE.md bullet, the skill-body bullet, or the /create-skill args JSON. Keep house style; no secrets.' },
    dedupeStatus: { type: 'string', enum: ['new', 'update-existing', 'already-captured'] },
    dedupeRef:    { type: 'string', description: 'the existing entry/section it duplicates or should update, if any (path or MEMORY.md line); else ""' },
    confidence:   { type: 'number', description: '0..1 confidence in the chosen home' },
    rationale:    { type: 'string', description: 'one sentence: the discriminating signal that picked this home' },
  },
  required: ['title', 'home', 'target', 'action', 'patch', 'dedupeStatus', 'confidence', 'rationale'],
}

const CHALLENGE = {
  type: 'object',
  additionalProperties: false,
  properties: {
    title:         { type: 'string' },
    agrees:        { type: 'boolean', description: 'true if the proposed home + dedupe verdict survive scrutiny' },
    betterHome:    { type: 'string', enum: ['memory', 'skill-edit', 'new-skill', 'new-workflow', 'claude-md', 'commands', 'defer', ''], description: 'a different home if you disagree; else ""' },
    alreadyCovered:{ type: 'boolean', description: 'true if this is already recorded somewhere (cite it in evidence)' },
    evidence:      { type: 'string', description: 'the file/line you grepped that proves your verdict' },
    severity:      { type: 'string', enum: ['block', 'warn', 'none'] },
  },
  required: ['title', 'agrees', 'alreadyCovered', 'evidence', 'severity'],
}

// ---- Phases 1+2 PIPELINED: each learning flows classify -> challenge independently (no barrier) --
phase('Classify')
const merged = (await pipeline(
  learnings,
  (l, _orig, i) => agent(
    `You ROUTE one candidate session-learning to the durable home in this repo that it best IMPROVES, and ` +
    `draft the EXACT patch. All your tool calls are READ-ONLY (grep/read) — you write NOTHING; the session writes.\n\n` +
    `LEARNING #${i + 1}: ${l.title}\n${l.detail}\n\n` +
    `Context paths (use ABSOLUTE for memory): memoryDir=${memoryDir} · CLAUDE.md=${claudeMd} · skillsDir=${skillsDir}\n` +
    `Valid skill dirs: ${list(validSkills)}\nValid tool names (exact, hyphen-vs-underscore): ${list(validTools)}\n\n` +
    `STEP 1 — DEDUPE FIRST: grep before you route so you don't double-record:\n` +
    `  grep -ri "<keyword>" "${memoryDir}/MEMORY.md"   (and read the matching <slug>.md)\n` +
    `  grep -rn "<keyword>" ${skillsDir}/<likely-skill>/SKILL.md\n` +
    `  grep -n "<keyword>" ${claudeMd}\n` +
    `Set dedupeStatus = already-captured (then skip), update-existing (cite dedupeRef), or new.\n\n` +
    `STEP 2 — ROUTE using:\n${TAXONOMY}\n\n` +
    `STEP 3 — DRAFT the EXACT patch text in house style, with NO secrets (scrub keys/tokens):\n` +
    `  - memory: a full file with frontmatter (name/description/metadata{node_type:memory,type:<memoryType>}) ` +
    `THEN on a new line the MEMORY.md index line "- [Title](<slug>.md) — summary".\n` +
    `  - claude-md: the single bullet, matching the existing shape ("- **lead-in** — gotcha." / "- **Imperative.** why.").\n` +
    `  - skill-edit: the bullet/line to append (any [[wikilink]] MUST resolve to a real skill dir or docs stem — never a memory slug or a workflow name).\n` +
    `  - new-skill: the /create-skill args as JSON {name,summary,triggers,subject:{description,seedFacts},related} (the session runs the workflow).\n` +
    `  - new-workflow: a one-paragraph spec of the fan-out (the session hand-authors the .js).\n` +
    `Return the full CLASSIFY object. target must be an exact path + section.`,
    { label: `classify:${lslug(l.title)}`, phase: 'Classify', schema: CLASSIFY, agentType: 'general-purpose' },
  ).then(r => r ? { ...r, title: r.title || l.title, _learning: l } : null),
  (route, l, i) => {
    if (!route) return null
    return agent(
      `You are a SKEPTIC. Try to REFUTE the proposed routing of a session-learning — prove it is already ` +
      `captured, or that a different home is correct. All tool calls READ-ONLY. Default to severity "warn" ` +
      `(not "block") unless you are confident.\n\n` +
      `LEARNING #${i + 1}: ${l.title}\n${l.detail}\n\n` +
      `PROPOSED: home=${route.home} · target=${route.target} · action=${route.action} · dedupeStatus=${route.dedupeStatus} ` +
      `· dedupeRef=${route.dedupeRef || '(none)'}\nRationale: ${route.rationale}\n\n` +
      `Re-grep independently: ${memoryDir}/MEMORY.md + slugs, ${claudeMd}, and the candidate ${skillsDir}/<n>/SKILL.md. ` +
      `Check: (a) is this fact ALREADY recorded somewhere? (cite file/line in evidence) (b) is the home wrong per the ` +
      `taxonomy below? (c) would this bloat CLAUDE.md when memory would do?\n${TAXONOMY}\n\n` +
      `Return CHALLENGE: agrees, alreadyCovered, betterHome (or ""), evidence (the file/line you read), severity ` +
      `(block only if it would create a duplicate or clearly wrong home; warn for a nit; none if the route is solid).`,
      { label: `challenge:${lslug(l.title)}`, phase: 'Challenge', schema: CHALLENGE, agentType: 'general-purpose' },
    ).then(ch => ({ ...route, challenge: ch || null }))
  },
)).filter(Boolean)

// ---- Phase 3 REDUCE: fold the skeptic's verdict into a status (pure JS, no agent) ----------------
phase('Reduce')
const plan = merged.map(r => {
  const ch = r.challenge || {}
  let status = 'proposed'
  if (r.dedupeStatus === 'already-captured' || ch.alreadyCovered) status = 'skip-already-captured'
  else if (ch.severity === 'block') status = 'needs-decision'
  else if (ch.betterHome && ch.betterHome !== r.home) status = 'needs-decision'
  else if (ch.agrees === false) status = 'review'
  const { _learning, ...rest } = r
  return { ...rest, status }
})
const conflicts = plan.filter(p => p.status === 'needs-decision' || p.status === 'review')
const byHome = plan.reduce((m, p) => { m[p.home] = (m[p.home] || 0) + 1; return m }, {})

log(`fold-learnings: ${plan.length} routed · ${conflicts.length} need a decision · homes=${JSON.stringify(byHome)}`)
return {
  summary: { candidates: learnings.length, routed: plan.length, conflicts: conflicts.length, byHome },
  plan,
  conflicts,
}
