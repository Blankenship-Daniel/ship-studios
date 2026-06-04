export const meta = {
  name: 'warm-bus-shootout',
  description: 'Score N pre-rendered drum-bus (or any audio) variants for the user\'s WARM + tight-bottom drum-bus preference. A thin PRESET over the `audio-shootout` workflow: injects the warm-drum-bus intent + warmth/tightness/life criteria, then delegates the multi-lens Gemini judge panel. Hybrid: render the variants inline first (deterministic DSP), then fan out the perceptual judging. args = { variants:[{name,spec?,path(ABSOLUTE),meters?}], criteria?:[{key,q}], intent?, genre?, anchorPath? }.',
  phases: [
    { title: 'Delegate', detail: 'forward the warm preset to the audio-shootout workflow' },
  ],
}

// ---- warm-drum-bus preset over the neutral audio-shootout mechanism -----------------------------
// Defensive: args may arrive as an object OR a JSON string depending on how it was passed.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const intent = A.intent ||
  'a WARM drum bus with a TIGHT, controlled low end — warmth from tape + tilt, never a bright EQ boost'
const genre = A.genre || 'rock'
const criteria = A.criteria || [
  { key: 'warmth',    q: 'WARMTH / tonal richness — full and warm, NOT dull or muddy' },
  { key: 'tightness', q: 'TIGHT, CONTROLLED low end — punchy bottom with no boom, bloom, or flubby sub' },
  { key: 'life',      q: 'TRANSIENT LIFE / punch — the kit breathes and hits, NOT over-glued or squashed' },
]

log(`warm-bus-shootout → audio-shootout; variants=${(A.variants || []).length}`)

// Delegate to the general judge panel with the warm preset injected. One level of nesting only.
return await workflow('audio-shootout', {
  variants: A.variants,
  criteria,
  intent,
  genre,
  anchorPath: A.anchorPath,
})
