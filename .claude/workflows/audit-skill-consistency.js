export const meta = {
  name: 'audit-skill-consistency',
  description: 'One validator agent per skill (~97) checks each SKILL.md for drift: [[wikilinks]] resolve to a real skill or doc, referenced MCP/CLI tool names match the EXACT CLAUDE.md tool surface (hyphen-vs-underscore matters), docs/*.md refs exist, the [L]/[G]+key labeling is correct (the recurring bug: a [G] gemini tool mislabeled keyless, or an [L] pure-DSP tool mislabeled as needing GEMINI_API_KEY), and YAML frontmatter (name/description/argument-hint) is complete. Reduce to a categorized drift report. Agents read their own files; the script just fans out one agent per skill dir. args = { skills:[dir], validSkills?, validTools?, validDocs?, geminiTools?, loopsDspTools? } — all gathered INLINE.',
  phases: [
    { title: 'Validate', detail: 'one agent per skill reads its SKILL.md and checks all drift classes' },
    { title: 'Report',   detail: 'reduce findings into a categorized drift report (by class, by severity)' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const skills = A.skills || []
if (!skills.length) {
  return { error: 'no skills — pass args.skills = [dir,...] (gather inline: ls -d .claude/skills/*/)' }
}
const ctx = {
  validSkills:   A.validSkills   || [],
  validTools:    A.validTools    || [],
  validDocs:     A.validDocs     || [],
  geminiTools:   A.geminiTools   || [],
  loopsDspTools: A.loopsDspTools || [],
}
log(`auditing ${skills.length} skills (validTools=${ctx.validTools.length}, geminiTools=${ctx.geminiTools.length})`)

const FINDINGS = {
  type: 'object',
  additionalProperties: false,
  properties: {
    frontmatterOk: { type: 'boolean', description: 'name + description + argument-hint all present & non-empty' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          class:    { type: 'string', enum: ['broken-wikilink', 'tool-name-drift', 'missing-doc', 'key-label-bug', 'frontmatter', 'other'] },
          severity: { type: 'string', enum: ['error', 'warn'] },
          ref:      { type: 'string', description: 'the offending token (e.g. [[foo]], apply_eq, docs/x.md)' },
          detail:   { type: 'string', description: 'what is wrong + the correct value if known' },
        },
        required: ['class', 'severity', 'ref', 'detail'],
      },
    },
  },
  required: ['frontmatterOk', 'issues'],
}

const list = a => (a && a.length) ? a.join(', ') : '(none supplied — derive it yourself with ls/find/grep)'
const validatorPrompt = s =>
  `You are a documentation linter for ONE Claude Code skill: ".claude/skills/${s}/SKILL.md". Read that file.\n` +
  `Report EVERY drift issue you find (empty issues array if clean):\n` +
  `1) WIKILINKS: every [[name]] must resolve to a real skill dir OR a docs target. Valid skills: ${list(ctx.validSkills)}. ` +
  `If a [[x]] is not a known skill, check whether it is a doc (e.g. docs/gemini-audio); if neither → class=broken-wikilink, severity=error.\n` +
  `2) TOOL NAMES: every referenced MCP/CLI tool name must EXACTLY match (hyphen vs underscore included) one of the valid tools: ${list(ctx.validTools)}. ` +
  `A drifted name (e.g. apply_eq for apply-eq, render_mastered for render-mastered) → class=tool-name-drift, severity=error. ` +
  `Ignore python script names like apply_vst_preset.py and pipeline FUNCTION names (master_track) — those legitimately use underscores.\n` +
  `3) DOC PATHS: every docs/….md reference must exist. Known docs: ${list(ctx.validDocs)} (or run \`test -f <path>\`). Missing → class=missing-doc, severity=error.\n` +
  `4) KEY LABELS (recurring bug): tools that NEED GEMINI_API_KEY are the [G] gemini tools: ${list(ctx.geminiTools)}. ` +
  `Pure-DSP NO-key [L] tools: ${list(ctx.loopsDspTools)}. If the skill says a [G] tool is "no key / pure DSP", ` +
  `or says an [L]/pure-DSP tool "needs GEMINI_API_KEY", that is a key-label-bug, severity=error.\n` +
  `5) FRONTMATTER: name + description + argument-hint must all be present & non-empty → frontmatterOk; otherwise add class=frontmatter, severity=error for each missing field.\n` +
  `Return frontmatterOk and the issues array.`

// ---- Phase 1: validate, batched to respect ≤16 concurrency (97 > 16) ----------------------------
phase('Validate')
const SKILL_BATCH = 16
const batches = []
for (let i = 0; i < skills.length; i += SKILL_BATCH) batches.push(skills.slice(i, i + SKILL_BATCH))

const findings = (await pipeline(
  batches,
  b => parallel(b.map(s => () =>
    agent(validatorPrompt(s),
      { label: `audit:${s}`, phase: 'Validate', schema: FINDINGS, agentType: 'general-purpose' },
    ).then(r => ({ skill: s, frontmatterOk: r ? !!r.frontmatterOk : false, issues: (r && r.issues) || [] })),
  )),
)).flat().filter(Boolean)

// ---- Phase 2: reduce → categorized report -------------------------------------------------------
phase('Report')
const flat = findings.flatMap(f => f.issues.map(i => ({ skill: f.skill, ...i })))
const byClass = {}
flat.forEach(i => { (byClass[i.class] = byClass[i.class] || []).push(i) })
const errors = flat.filter(i => i.severity === 'error')
const dirtySkills = findings.filter(f => f.issues.length || !f.frontmatterOk).map(f => f.skill)
log(`audited ${findings.length} skills — ${errors.length} errors across ${dirtySkills.length} skills`)
return {
  summary: { skills: findings.length, issues: flat.length, errors: errors.length, dirtySkills: dirtySkills.length },
  byClass,
  cleanSkills: findings.filter(f => !f.issues.length && f.frontmatterOk).map(f => f.skill),
  findings,
}
