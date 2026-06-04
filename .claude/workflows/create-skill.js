export const meta = {
  name: 'create-skill',
  description: 'Author a new, convention-correct SKILL.md for this repo end-to-end via a research → draft → adversarial-review → revise fan-out. RESEARCH (parallel): a conventions agent reads exemplar SKILL.md files to extract the exact frontmatter + section shape; a subject agent GROUNDS the skill in reality (runs the researchCommands / reads the docUrls so the recipe cites real flags/tools, not hallucinations); a neighborhood agent validates the proposed [[related]] links against the real skill list and flags duplication. DRAFT: one agent synthesizes a complete SKILL.md. REVIEW (parallel, adversarial): three lenses — triggering/frontmatter, lint/convention (wikilinks resolve, tool names exact incl. hyphen-vs-underscore, [L]/[G]+key labels, argument-hint present), and technical accuracy vs the grounded facts. REVISE: one agent folds every issue into the final SKILL.md. The script writes nothing — it RETURNS { path, name, content, ... } and the SESSION writes the file (then run audit-skill-consistency on it). Gather args INLINE first (ls -d .claude/skills/*/ for validSkills; pick 1-3 exemplar SKILL.md; the CLAUDE.md tool surface for validTools). args = { name(kebab), summary, triggers[], kind?, subject:{description, researchCommands?[], docUrls?[], seedFacts?}, related?[], validSkills?[], validDocs?[], validTools?[], exemplars?[] }.',
  phases: [
    { title: 'Research', detail: 'parallel: conventions (read exemplars) + subject (run/verify the real surface) + neighborhood (validate related, find duplication)' },
    { title: 'Draft',    detail: 'one agent synthesizes the full SKILL.md from the research' },
    { title: 'Review',   detail: 'parallel adversarial lenses: triggering/frontmatter, lint/convention, technical accuracy' },
    { title: 'Revise',   detail: 'one agent folds every issue into the final SKILL.md + changelog' },
  ],
}

// ---- args (may arrive as an object OR a JSON string) -------------------------------------------
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const name = (A.name || '').trim()
if (!name || !/^[a-z0-9][a-z0-9-]*$/.test(name)) {
  return { error: `args.name must be a kebab-case slug (got ${JSON.stringify(A.name)})` }
}
const path = `.claude/skills/${name}/SKILL.md`

const spec = {
  name,
  summary: A.summary || '',
  triggers: A.triggers || [],
  kind: A.kind || 'pipeline', // pipeline | reference | plugin | workflow-wrapper | local-dsp
  subject: A.subject || {},
  related: A.related || [],
}
const ctx = {
  validSkills: A.validSkills || [],
  validDocs:   A.validDocs   || [],
  validTools:  A.validTools  || [],
  exemplars:   A.exemplars   || ['.claude/skills/de-ess/SKILL.md', '.claude/skills/gemini-audio/SKILL.md'],
}
const list = a => (a && a.length) ? a.join(', ') : '(none supplied — derive it yourself with ls/grep)'

log(`create-skill "${name}" (kind=${spec.kind}) → ${path}`)
log(`  triggers=${spec.triggers.length} related=${spec.related.length} validSkills=${ctx.validSkills.length} exemplars=${ctx.exemplars.length}`)

// ===============================================================================================
// Phase 1 — RESEARCH (barrier: the draft genuinely needs ALL THREE outputs synthesized together)
// ===============================================================================================
phase('Research')

const NEIGHBORHOOD = {
  type: 'object',
  additionalProperties: false,
  properties: {
    relatedValid:    { type: 'array', items: { type: 'string' }, description: 'proposed [[related]] that DO resolve to a real skill/doc' },
    relatedBroken:   { type: 'array', items: { type: 'string' }, description: 'proposed [[related]] that do NOT resolve (drop or fix these)' },
    suggestedRelated:{ type: 'array', items: { type: 'string' }, description: 'additional real, on-topic skills worth linking' },
    duplicationRisk: { type: 'string', description: 'closest existing skill(s) and whether this new skill overlaps / how to differentiate' },
  },
  required: ['relatedValid', 'relatedBroken', 'suggestedRelated', 'duplicationRisk'],
}

const conventionsPrompt =
  `You are extracting the WRITING CONVENTIONS for a ship-studios Claude Code skill so a new one matches the house style. ` +
  `Read these exemplar SKILL.md files: ${list(ctx.exemplars)}. Also skim CLAUDE.md for the [L]/[G] tool-labeling convention. ` +
  `Return a tight style guide (plain prose, no preamble) covering EXACTLY: ` +
  `(1) the YAML frontmatter keys and order (name, description, argument-hint) and what makes a GOOD trigger-rich description ` +
  `(starts with "Use when…", packs natural-language trigger phrases in quotes, ends with the surface it uses e.g. "Stemmy MCP" / "Local DSP"); ` +
  `(2) the canonical body section order actually used (e.g. # Title, Goal, Prerequisites, Recipe (ordered, measure-before/after), Outputs, Reporting to the user, Pitfalls, Related) — note which sections a "${spec.kind}" skill should keep vs drop; ` +
  `(3) the conventions for [[wikilinks]], the [L]/[G] server prefixes, and the GEMINI_API_KEY/no-key labeling; ` +
  `(4) tone: terse, imperative, bold the load-bearing rule. Quote 1-2 short real lines as models.`

const subj = spec.subject
const subjectPrompt =
  `You are GROUNDING a new skill named "${name}" in reality so its recipe cites real behavior, not guesses. ` +
  `Subject: ${subj.description || spec.summary}. ` +
  (subj.seedFacts ? `\nKnown-good seed facts (verify + extend, do not just parrot):\n${subj.seedFacts}\n` : '') +
  ((subj.researchCommands && subj.researchCommands.length)
    ? `\nRUN these commands (Bash) and record what actually happens — exact flags, output shape, error/trust gates, exit codes:\n` +
      subj.researchCommands.map((c, i) => `  ${i + 1}. ${c}`).join('\n') + '\n'
    : `\nNo commands supplied — inspect the relevant CLI/tool's --help and any obvious behavior yourself (Bash/Read).\n`) +
  ((subj.docUrls && subj.docUrls.length) ? `\nAlso consult (WebFetch): ${subj.docUrls.join(', ')}\n` : '') +
  `\nReturn a FACTS sheet (plain prose/bullets): the exact invocation(s), every flag that matters, output formats, ` +
  `auth/trust/rate-limit gotchas, and — critically — how this subject RELATES TO BUT DIFFERS FROM anything already in the repo ` +
  `(e.g. a CLI vs the MCP-server tools). Mark anything you could NOT verify as ⚠️ UNVERIFIED.`

const neighborhoodPrompt =
  `You are validating the WIKILINK NEIGHBORHOOD for a new skill "${name}" (summary: ${spec.summary}). ` +
  `The ONLY valid [[wikilink]] targets are these skills: ${list(ctx.validSkills)} — plus these doc targets: ${list(ctx.validDocs)}. ` +
  `Proposed related links to check: ${list(spec.related)}. ` +
  `For each proposed link decide if it resolves (relatedValid) or not (relatedBroken). ` +
  `Then suggest additional genuinely on-topic existing skills worth linking (suggestedRelated). ` +
  `Finally, name the closest existing skill(s) and assess duplicationRisk — does "${name}" overlap an existing skill, and if so how should the new skill differentiate itself or should it instead extend the existing one? Read SKILL.md files as needed to judge.`

const [styleGuide, groundedFacts, neighborhood] = await parallel([
  () => agent(conventionsPrompt,   { label: 'research:conventions', phase: 'Research', agentType: 'general-purpose' }),
  () => agent(subjectPrompt,       { label: 'research:subject',     phase: 'Research', agentType: 'general-purpose' }),
  () => agent(neighborhoodPrompt,  { label: 'research:neighborhood', phase: 'Research', agentType: 'general-purpose', schema: NEIGHBORHOOD }),
])

const safeNb = neighborhood || { relatedValid: spec.related, relatedBroken: [], suggestedRelated: [], duplicationRisk: '(neighborhood agent returned nothing)' }
const finalRelated = Array.from(new Set([...(safeNb.relatedValid || []), ...(safeNb.suggestedRelated || [])]))
log(`research done — related: ${finalRelated.length} valid (${(safeNb.relatedBroken || []).length} dropped); dup-risk noted`)

// ===============================================================================================
// Phase 2 — DRAFT
// ===============================================================================================
phase('Draft')

const DRAFT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    content:   { type: 'string', description: 'the COMPLETE SKILL.md: YAML frontmatter (--- name/description/argument-hint ---) then the markdown body' },
    rationale: { type: 'string', description: 'one paragraph: the key decisions (kind, what was kept/dropped, how it differentiates from neighbors)' },
  },
  required: ['content', 'rationale'],
}

const draftPrompt =
  `Write the COMPLETE SKILL.md for a ship-studios Claude Code skill named "${name}" (kind: ${spec.kind}).\n\n` +
  `=== HOUSE STYLE (follow exactly) ===\n${styleGuide}\n\n` +
  `=== GROUNDED FACTS (the recipe MUST match these; do not invent flags/tools) ===\n${groundedFacts}\n\n` +
  `=== SKILL SPEC ===\nsummary: ${spec.summary}\n` +
  `trigger phrases to weave into the description: ${list(spec.triggers)}\n` +
  `valid [[related]] links to use (only these resolve): ${list(finalRelated)}\n` +
  `duplication note to respect: ${safeNb.duplicationRisk}\n\n` +
  `=== HARD REQUIREMENTS ===\n` +
  `- YAML frontmatter with name: ${name}, a "Use when…" trigger-rich description quoting several of the phrases above and ending with the surface it uses, and an argument-hint.\n` +
  `- Body sections appropriate to a "${spec.kind}" skill, in the house order.\n` +
  `- Every [[wikilink]] MUST be one of the valid related links above (no others).\n` +
  `- Label any referenced tools with the correct [L]/[G] prefix and state key/no-key correctly. If it references a shell CLI, show the exact command(s).\n` +
  `- Terse, imperative, bold the load-bearing rules. Include a Pitfalls section with the real gotchas from the grounded facts.\n` +
  `Return the full file content and your rationale.`

const draft = await agent(draftPrompt, { label: 'draft', phase: 'Draft', schema: DRAFT })
if (!draft || !draft.content) return { error: 'draft agent returned no content', path, name }

// ===============================================================================================
// Phase 3 — REVIEW (barrier: the revise step genuinely needs ALL review lenses at once)
// ===============================================================================================
phase('Review')

const REVIEW = {
  type: 'object',
  additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    ok:   { type: 'boolean', description: 'true only if zero error-severity issues' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          severity: { type: 'string', enum: ['error', 'warn'] },
          area:     { type: 'string', description: 'frontmatter | wikilink | tool-name | key-label | accuracy | structure | tone | other' },
          detail:   { type: 'string', description: 'what is wrong' },
          fix:      { type: 'string', description: 'the concrete correction to apply' },
        },
        required: ['severity', 'area', 'detail', 'fix'],
      },
    },
  },
  required: ['lens', 'ok', 'issues'],
}

const head = `Here is a DRAFT SKILL.md for "${name}".\n\n--- BEGIN DRAFT ---\n${draft.content}\n--- END DRAFT ---\n\n`
const reviewLenses = [
  {
    key: 'triggering',
    prompt: head +
      `Review ONLY the TRIGGERING + FRONTMATTER quality. Will Claude reliably pick this skill when it should? ` +
      `Check: frontmatter has name + a "Use when…" description rich with natural-language trigger phrases + argument-hint (all present, non-empty); ` +
      `the description states the surface it uses; it is neither so narrow it misses obvious phrasings nor so broad it false-fires. ` +
      `Set lens="triggering". Report issues with concrete fixes.`,
  },
  {
    key: 'lint',
    prompt: head +
      `Review ONLY CONVENTION/LINT compliance (you are the same linter as audit-skill-consistency). ` +
      `(1) Every [[wikilink]] must resolve to a real skill or doc. Valid skills: ${list(ctx.validSkills)}. Valid docs: ${list(ctx.validDocs)}. A non-resolving [[x]] = error.\n` +
      `(2) Every referenced MCP/CLI tool name must EXACTLY match (hyphen vs underscore included). Valid tools: ${list(ctx.validTools)}. A drifted name = error. (Shell invocations like \`gemini -p\` and python script names are fine.)\n` +
      `(3) [L]/[G] + key labels: [G] gemini-model tools need GEMINI_API_KEY; pure-DSP [L] (and the keyless [G] DSP tools) do not. A mislabel = error.\n` +
      `(4) argument-hint present & non-empty.\n` +
      `Set lens="lint". Report issues with concrete fixes.`,
  },
  {
    key: 'accuracy',
    prompt: head +
      `Review ONLY TECHNICAL ACCURACY against these ground-truth facts:\n${groundedFacts}\n\n` +
      `Flag any claim in the draft that contradicts or is unsupported by the facts — invented flags, wrong output format, a recipe step that would not actually work, or a missing critical gotcha (e.g. an auth/trust gate). ` +
      `Also flag anything the draft states with confidence that the facts marked ⚠️ UNVERIFIED. Set lens="accuracy". Report issues with concrete fixes.`,
  },
]

const reviews = (await parallel(reviewLenses.map(L => () =>
  agent(L.prompt, { label: `review:${L.key}`, phase: 'Review', schema: REVIEW })
))).filter(Boolean)

const allIssues = reviews.flatMap(r => (r.issues || []).map(i => ({ lens: r.lens, ...i })))
const errorIssues = allIssues.filter(i => i.severity === 'error')
log(`review: ${allIssues.length} issues (${errorIssues.length} errors) across ${reviews.length} lenses`)

// ===============================================================================================
// Phase 4 — REVISE (skip if the panel was clean)
// ===============================================================================================
phase('Revise')

let finalContent = draft.content
let changelog = []
let residualWarnings = allIssues.filter(i => i.severity === 'warn').map(i => `[${i.lens}/${i.area}] ${i.detail}`)

if (allIssues.length) {
  const FINAL = {
    type: 'object',
    additionalProperties: false,
    properties: {
      content:          { type: 'string', description: 'the FINAL corrected SKILL.md (full file)' },
      changelog:        { type: 'array', items: { type: 'string' }, description: 'one line per change applied' },
      residualWarnings: { type: 'array', items: { type: 'string' }, description: 'any issue intentionally NOT applied, with why' },
    },
    required: ['content', 'changelog', 'residualWarnings'],
  }
  const issueText = allIssues
    .map(i => `- [${i.severity}][${i.lens}/${i.area}] ${i.detail}  → FIX: ${i.fix}`)
    .join('\n')
  const revisePrompt =
    `Apply this review to the DRAFT and return the FINAL SKILL.md. Fix EVERY error; apply warns unless they conflict with a fact or the house style (then explain in residualWarnings).\n\n` +
    `--- DRAFT ---\n${draft.content}\n--- END DRAFT ---\n\n--- ISSUES ---\n${issueText}\n--- END ISSUES ---\n\n` +
    `Keep everything that was already correct. Do not introduce new unresolved [[wikilinks]] (valid: ${list(finalRelated)}). Return content + changelog + residualWarnings.`

  const revised = await agent(revisePrompt, { label: 'revise', phase: 'Revise', schema: FINAL })
  if (revised && revised.content) {
    finalContent = revised.content
    changelog = revised.changelog || []
    residualWarnings = revised.residualWarnings || residualWarnings
  } else {
    residualWarnings.unshift('revise agent returned nothing — returning the unrevised draft')
  }
} else {
  log('review panel clean — no revise needed')
}

return {
  path,
  name,
  kind: spec.kind,
  content: finalContent,
  rationale: draft.rationale,
  related: finalRelated,
  duplicationRisk: safeNb.duplicationRisk,
  review: {
    lenses: reviews.map(r => ({ lens: r.lens, ok: r.ok, issues: r.issues.length })),
    errors: errorIssues.length,
    total: allIssues.length,
  },
  changelog,
  residualWarnings,
  nextSteps: [
    `Write the returned content to ${path}`,
    `Add the one-line pointer to .claude/skills if an index exists`,
    `Run the audit-skill-consistency workflow on "${name}" to confirm zero drift`,
  ],
}
