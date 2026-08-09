#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>

//==============================================================================
/**
    The distance curve, in one place.

    Both the audio thread and the UI's curve display derive from these tables, so
    what you see is by construction what you hear -- there is no second copy of
    the numbers to fall out of step.

    THE MODEL. Distance has four spectral signatures, and this maps all four onto
    one axis:

      1. Proximity effect     -- a close directional mic gains low end; a distant
                                 one loses it.
      2. Room low-mid buildup -- a distant source in a room accumulates ~300 Hz
                                 "box"/"cavern".
      3. Direct-sound presence-- direct sound carries 2-5 kHz detail and bite that
                                 is lost with distance.
      4. Air absorption       -- HF attenuates with distance. Negligible below
                                 ~2 kHz, severe above 8 kHz. The strongest cue,
                                 hence the largest move.

    Honest limit: EQ is NOT the dominant distance cue -- direct-to-reverberant
    ratio is. This reads convincingly over roughly the first half of its range and
    then starts sounding merely dark rather than far.
*/
namespace ShipStudios
{

struct BandSpec
{
    enum class Type { lowShelf, bell, highShelf };

    Type  type;
    float freqHz;
    float q;
    float closeDb;   // gain at distance = +1 (closest)
    float farDb;     // gain at distance = -1 (furthest)
    const char* name;   // the physical cue this band models, for the UI
};

/** The curve. Anchored to this repo's own measured far<->close axis: the
    `when-the-levee-breaks` recipe (distant/cavernous: bell 200 +2.0 q0.9,
    high_shelf 7000 -4.0) and `back-in-black` (present/closest: bell 450 -2.0
    de-box, bell 3500 +1.5 snap, high_shelf 9000 +1.0).

    Note band 1 departs from both: those recipes BOOST the low shelf, but they are
    drum-bus taste moves wanting weight from tape. The distance model wants the
    proximity effect instead, with the room's low-mid arriving separately via
    band 2.

    The repo hard-codes 5-7 kHz as the harshness trap. Band 3 sits below it and
    band 4 above it, so nothing boosts directly into the guard.
*/
inline constexpr std::array<BandSpec, 4> factoryBands { {
    { BandSpec::Type::lowShelf,   110.0f, 0.707f,  6.0f,  -5.0f, "PROXIMITY" },
    { BandSpec::Type::bell,       300.0f, 0.900f, -4.0f,   5.0f, "ROOM"      },
    { BandSpec::Type::bell,      3200.0f, 1.000f,  4.0f,  -8.0f, "PRESENCE"  },
    { BandSpec::Type::highShelf, 8000.0f, 0.707f,  3.0f, -18.0f, "AIR"       },
} };

/** Shaping exponent applied to |d| before scaling a band's endpoint gain.

    Above 1.0 the curve is superlinear: gentle either side of centre, dramatic
    only at the extremes. That is what lets the endpoints be this large without
    the fader becoming unusable for small moves -- at half travel you get
    0.5^1.35 = 39% of the endpoint rather than 50%, so mid-fader still lands near
    the subtler curve this replaced while the ends reach much further.

    It is also the better physical fit: none of these cues scales linearly with
    distance, and all of them change fastest close to the source.
*/
inline constexpr float curveExponent = 1.35f;

//==============================================================================
/**
    Where each band is ALLOWED to be placed when adapted to a source.

    The factory frequencies are a good average and wrong in the specific: one
    kit's boxiness sits at 240 Hz and another's at 380. Adapting moves each band
    onto the material -- but only inside these ranges, so a pathological source
    (a sine, near-silence, heavy noise) cannot produce a nonsense curve.

    PRESENCE's upper bound is not arbitrary: it keeps the band below this repo's
    hard-coded 5-7 kHz harshness guard, so an adapted curve can never aim a
    close-side boost into it.
*/
struct BandRange { float minHz, maxHz, searchLoHz, searchHiHz; };

inline constexpr std::array<BandRange, 4> bandRanges { {
    {   60.0f,   200.0f,    40.0f,   250.0f },   // PROXIMITY
    {  150.0f,   500.0f,   120.0f,   500.0f },   // ROOM
    { 1500.0f,  4500.0f,  1500.0f,  4500.0f },   // PRESENCE
    { 5000.0f, 12000.0f,  4000.0f, 16000.0f },   // AIR
} };

/** Minimum spacing between adjacent bands, as a frequency ratio. Without this a
    source with all its energy in one place could collapse two bands onto each
    other, which the loudness compensation is not designed for. */
inline constexpr float minBandRatio = 1.5f;

//==============================================================================
/**
    What the source IS -- the one judgement worth asking a model for.

    MEASURED, not guessed, where possible. Gemini supplies `material` only:
    tested on real drum material it got the source right 3/3, but its ambience
    read inverted (it called a room mic "moderate" and overheads "roomy"), and on
    an empty file it still answered confidently. So ambience is derived from
    crest factor here, and the model is never asked for a number.
*/
enum class Material
{
    unknown,
    kick, snare, overheads, drumKit,   // a kick mic and an overhead pair are NOT
    bass, vocal, fullMix, other        // the same problem, though both are "drums"
};

struct SourceProfile
{
    Material material = Material::unknown;
    bool roomy = false;          // measured from crest, not asked
    bool geminiUsed = false;
    juce::String note;
};

/** Classification shifts the SEARCH WINDOW; it never supplies a value.

    The split below is the point of the finer taxonomy: a kick's PRESENCE is
    beater click at ~3 kHz and its AIR is nearly irrelevant, while an overhead
    pair's PRESENCE is stick attack and its AIR is the entire cymbal wash an
    octave higher. Collapsing both into "drums" aimed the same two windows at
    two completely different problems. */
inline std::array<BandRange, 4> rangesFor (Material material) noexcept
{
    auto r = bandRanges;

    switch (material)
    {
        case Material::kick:
            // Fundamental is low and the useful "room" is the boxy shell knock.
            // AIR barely exists on a kick mic -- keep it high so a misfire
            // cannot drag the shelf down into the beater click.
            r[0] = {   40.0f,  120.0f,   30.0f,  140.0f };
            r[1] = {  150.0f,  400.0f,  120.0f,  450.0f };
            r[2] = { 2000.0f, 4500.0f, 2000.0f, 4500.0f };
            r[3] = { 6000.0f, 12000.0f, 5000.0f, 16000.0f };
            break;

        case Material::snare:
            // PROXIMITY is the drum's own fundamental (~180-250), ROOM is the
            // boxiness above it, PRESENCE the crack, AIR the wire sizzle.
            r[0] = {  100.0f,  250.0f,   80.0f,  280.0f };
            r[1] = {  250.0f,  600.0f,  220.0f,  650.0f };
            r[2] = { 2500.0f, 4500.0f, 2500.0f, 4500.0f };
            r[3] = { 6000.0f, 14000.0f, 5500.0f, 16000.0f };
            break;

        case Material::overheads:
            // Cymbal-dominated: the air knee sits an octave above a close mic's,
            // and searching from 4 kHz would find the stick attack instead.
            r[1] = {  200.0f,  500.0f,  180.0f,  550.0f };
            r[2] = { 2500.0f, 4500.0f, 2500.0f, 4500.0f };
            r[3] = { 7000.0f, 16000.0f, 6000.0f, 18000.0f };
            break;

        case Material::drumKit:
            // A whole kit or drum bus -- the old "drums" behaviour.
            r[2] = { 2500.0f, 4500.0f, 2500.0f, 4500.0f };
            r[3] = { 5000.0f, 12000.0f, 6000.0f, 16000.0f };
            break;

        case Material::bass:
            // "Presence" on bass is string and growl, roughly an octave and a
            // half below where it sits on a drum. Well clear of the harshness
            // guard, so the derived Q stays at 1.0.
            r[0] = {   40.0f,  120.0f,   30.0f,  140.0f };
            r[1] = {  150.0f,  400.0f,  120.0f,  400.0f };
            r[2] = {  900.0f, 2500.0f,  800.0f, 2500.0f };
            break;

        case Material::vocal:
            // Vocal presence sits lower than a drum transient, and the
            // proximity effect on a close vocal is real and low.
            r[0] = {   80.0f,  180.0f,   60.0f,  200.0f };
            r[2] = { 1500.0f, 4000.0f, 2000.0f, 4000.0f };
            break;

        case Material::fullMix:
            // A finished mix is already balanced -- stay near factory.
            r[1] = {  200.0f,  400.0f,  180.0f,  450.0f };
            r[2] = { 2500.0f, 4000.0f, 2500.0f, 4000.0f };
            break;

        case Material::unknown:
        case Material::other:
        default:
            break;
    }

    return r;
}

/** Per-band gain for a normalised distance in [-1, +1]. Piecewise-linear per
    side so each band can be asymmetric (air cuts far harder than it boosts near).

    At d == 0 every band returns exactly 0 dB, which is a gain factor of exactly
    1.0. RBJ then yields A == 1, making the biquad's numerator and denominator
    identical -- H(z) == 1, a bit-exact passthrough. Centre really is untouched.
*/
/** Extreme mode multiplier. Scales the AMOUNT of processing -- EQ gains,
    compressor ratio and threshold -- but deliberately NOT the attack/release
    times, which are character rather than amount. Doubling those would put the
    far attack at 0.0045 ms, which is meaningless.

    Smoothed at runtime rather than switched, so toggling it mid-playback ramps
    instead of stepping. */
inline constexpr float extremeScale = 2.0f;

inline float bandGainDb (const BandSpec& band, float d, float scale) noexcept
{
    if (d > 0.0f) return band.closeDb * std::pow ( d, curveExponent) * scale;
    if (d < 0.0f) return band.farDb   * std::pow (-d, curveExponent) * scale;

    return 0.0f;   // exact, so the centre position is exactly unity at any scale
}

/** Keeps a band's corner below Nyquist at any sample rate. */
inline float safeFrequency (const BandSpec& band, double sampleRate) noexcept
{
    return juce::jmin (band.freqHz, (float) (sampleRate * 0.45));
}

/** Audio-thread-safe coefficients: returns by value, allocates nothing.
    Assign through an existing state Ptr -- `*duplicator.state = ...`. */
inline std::array<float, 6> makeArrayCoefficients (const BandSpec& band,
                                                   float d,
                                                   double sampleRate,
                                                   float scale) noexcept
{
    using AC = juce::dsp::IIR::ArrayCoefficients<float>;

    // NB gainFactor is a LINEAR factor, not dB. Passing dB here would read 0.0
    // as -inf gain -- i.e. silence at the "flat" setting.
    const auto gain = juce::Decibels::decibelsToGain (bandGainDb (band, d, scale));
    const auto freq = safeFrequency (band, sampleRate);

    switch (band.type)
    {
        case BandSpec::Type::lowShelf:  return AC::makeLowShelf   (sampleRate, freq, band.q, gain);
        case BandSpec::Type::highShelf: return AC::makeHighShelf  (sampleRate, freq, band.q, gain);
        case BandSpec::Type::bell:
        default:                        return AC::makePeakFilter (sampleRate, freq, band.q, gain);
    }
}

/** Ref-counted coefficients. ALLOCATES -- never call this from processBlock.
    For prepareToPlay, the compensation table, and the UI's curve display. */
inline juce::dsp::IIR::Coefficients<float>::Ptr makeCoefficientsPtr (const BandSpec& band,
                                                                     float d,
                                                                     double sampleRate,
                                                                     float scale)
{
    using C = juce::dsp::IIR::Coefficients<float>;

    const auto gain = juce::Decibels::decibelsToGain (bandGainDb (band, d, scale));
    const auto freq = safeFrequency (band, sampleRate);

    switch (band.type)
    {
        case BandSpec::Type::lowShelf:  return C::makeLowShelf   (sampleRate, freq, band.q, gain);
        case BandSpec::Type::highShelf: return C::makeHighShelf  (sampleRate, freq, band.q, gain);
        case BandSpec::Type::bell:
        default:                        return C::makePeakFilter (sampleRate, freq, band.q, gain);
    }
}

//==============================================================================
/**
    Dynamics that follow the same fader.

    Compression has no distance of its own -- it amplifies whatever already sits
    in the quiet part of the signal. Point it at dry detail and the source moves
    closer; point it at a room tail and it moves away. With no ambience stage in
    the chain yet, the lever that IS available is transient handling:

      CLOSE  slow attack  -> onsets survive intact, sustain and low-level detail
                             come up. Dense and punchy: a near source.
      FAR    fast attack  -> onsets are softened the way reverb smears them, and
                             a slow release lifts decay tails. A distant source.

    So the two ends are not "more" and "less" compression -- they are opposite
    ballistics. That is why one ratio knob wired to the fader would fight itself.

    Honest limit: without a wet stage the far end reads as "crushed" more than
    "far". The EQ darkening carries most of the distance; this deepens it.
*/
struct CompressorSpec
{
    float ratio;
    float thresholdDb;
    float attackMs;
    float releaseMs;
};

inline constexpr CompressorSpec closeCompressor { 3.0f, -18.0f, 30.0f, 120.0f };

// The far attack is 0.3 ms, not the "a few ms" that reads as fast on a spec
// sheet. Anything slower arrives AFTER the peak: it compresses the body while
// the transient passes untouched, which RAISES crest and sharpens the onset --
// the exact opposite of the intent. Measured: 2 ms attack took crest from
// 24.7 to 27.5 dB on a percussive test signal.
inline constexpr CompressorSpec farCompressor   { 4.0f, -24.0f,  0.3f, 300.0f };

inline constexpr float neutralAttackMs  = 20.0f;
inline constexpr float neutralReleaseMs = 200.0f;
inline constexpr float compressorKneeDb = 6.0f;

struct CompressorSettings
{
    float ratio;
    float thresholdDb;
    float attackMs;
    float releaseMs;
};

/** Compressor settings for a normalised distance. At d == 0 this returns ratio
    1.0 and threshold 0 dBFS -- mathematically inert, whatever the audio. */
inline CompressorSettings compressorFor (float d, float scale) noexcept
{
    const auto base   = std::pow (std::abs (d), curveExponent);
    const auto amount = base * scale;
    const auto& target = d < 0.0f ? farCompressor : closeCompressor;

    CompressorSettings s;

    // Clamped so an extreme setting stays a compressor rather than a gate-like
    // brickwall on quiet material.
    s.ratio       = juce::jlimit (1.0f, 20.0f, 1.0f + (target.ratio - 1.0f) * amount);
    s.thresholdDb = juce::jmax (-60.0f, target.thresholdDb * amount);

    // Times interpolate geometrically: 2 ms and 300 ms are two octaves apart in
    // opposite directions, and a linear blend would spend most of the travel in
    // the wrong decade.
    // Times interpolate on the UNSCALED amount: 2x means more compression, not a
    // different compressor. base is already in [0, 1].
    s.attackMs  = neutralAttackMs  * std::pow (target.attackMs  / neutralAttackMs,  base);
    s.releaseMs = neutralReleaseMs * std::pow (target.releaseMs / neutralReleaseMs, base);

    return s;
}

// NB there is deliberately no makeup field here. Makeup cannot be derived from
// the settings alone: the static curve's reduction at 0 dBFS is the MAXIMUM
// possible, and real programme sits far below full scale, so using it
// over-compensates by however much headroom the source has (measured: +7.8 LU).
// The processor instead tracks the gain reduction it is actually applying and
// gives that back, which is level- and material-independent.

/** Static-curve gain reduction (positive dB) for an input level, soft knee.
    Shared with the editor so the drawn transfer curve is the real one. */
inline float compressorGainReductionDb (const CompressorSettings& s, float inputDb) noexcept
{
    const auto slope = 1.0f - 1.0f / juce::jmax (1.0f, s.ratio);
    const auto over  = inputDb - s.thresholdDb;
    const auto knee  = compressorKneeDb;

    if (2.0f * over < -knee)
        return 0.0f;

    if (2.0f * std::abs (over) <= knee)
    {
        const auto x = over + knee * 0.5f;
        return slope * x * x / (2.0f * knee);
    }

    return slope * over;
}

//==============================================================================
/**
    Level as a distance cue.

    Intensity is the DOMINANT distance cue, and until now the plugin deliberately
    cancelled it so an A/B would be honest about tone. That made the fader a pure
    tone control. Restoring the level law makes it a distance control.

    THE NUMBER. In a free field the inverse-square law gives 6 dB per doubling of
    distance. Real rooms give less -- 4-5 dB is typical, because only the direct
    sound falls with distance while the reverberant field stays roughly constant
    throughout the space. Perceptually the story differs again: loudness in sones
    goes as intensity^0.3, so 10 dB is a halving of perceived loudness, and
    listeners asked to make a source sound twice as far typically pull ~10 dB --
    MORE than physics demands.

    6 dB/doubling is chosen as the free-field physical value: it is the honest
    default, it sits between the room figure and the perceptual one, and it is
    roughly a 1.5x change in sones -- clearly audible without swamping the mix.
    Raise dbPerDoubling toward 10 for a more theatrical read.

    HOW IT COMBINES. This is applied ON TOP of the loudness compensation, not
    instead of it. The compensation removes the loudness change the EQ curve
    causes incidentally (air absorption removing energy is a tone side-effect,
    not a distance cue); this then applies the intended change. Keeping them
    separate is what makes the level law exact and material-independent rather
    than "whatever the EQ happened to do to this source".
*/
inline constexpr float dbPerDoubling = 6.0f;

// Fader extreme == this many doublings of distance. 1.0 means fully-far is
// twice the reference distance and fully-close is half it; 2x mode makes that
// two doublings each way.
inline constexpr float doublingsAtExtreme = 1.0f;

/** Signed level offset in dB for a normalised distance. Positive (closer) is
    louder, negative (further) is quieter. Exactly 0 at centre. */
inline float distanceLevelDb (float d, float scale) noexcept
{
    if (juce::exactlyEqual (d, 0.0f))
        return 0.0f;

    // Same shaping exponent as the EQ and compressor, so level, tone and
    // dynamics all travel together rather than decoupling across the fader.
    const auto magnitude = std::pow (std::abs (d), curveExponent);
    const auto signedAmount = d > 0.0f ? magnitude : -magnitude;

    return signedAmount * dbPerDoubling * doublingsAtExtreme * scale;
}

//==============================================================================
/**
    Transient shaping as a distance cue -- the closest this chain gets to the
    direct-to-reverberant ratio, which is the cue EQ genuinely cannot fake.

    Reverberation does two things to an envelope: it smears the onset (early
    reflections arrive just after the direct sound, blurring the attack) and it
    extends the tail. So:

      CLOSE  attack UP, sustain DOWN   -- immediate, dry, all direct sound
      FAR    attack DOWN, sustain UP   -- blurred onset, longer tail

    Unlike the compressor this is LEVEL-INDEPENDENT: it works from the difference
    between two envelope followers, so a quiet hit is shaped as much as a loud
    one. That is why it reinforces the compressor's ballistics rather than
    duplicating them -- the compressor only acts above its threshold.

    Amounts are the maximum deviation; the differential approaches them through a
    tanh, so a sharper onset shapes harder but can never run away.
*/
struct TransientSpec
{
    float attackDb;
    float sustainDb;
};

inline constexpr TransientSpec closeTransient {  8.0f, -5.0f };
inline constexpr TransientSpec farTransient   { -8.0f,  6.0f };

// dB differential that reaches ~76% of the target deviation. Measured at 8.0 the
// shaping came out ~4x weaker than the amounts imply: real onsets only hold a
// large fast-vs-slow differential for a millisecond or two, so a high knee means
// the target is never approached before the differential collapses.
inline constexpr float transientKneeDb = 4.0f;

inline TransientSpec transientFor (float d, float scale) noexcept
{
    if (juce::exactlyEqual (d, 0.0f))
        return { 0.0f, 0.0f };

    const auto amount = std::pow (std::abs (d), curveExponent) * scale;
    const auto& target = d < 0.0f ? farTransient : closeTransient;

    return { target.attackDb * amount, target.sustainDb * amount };
}

//==============================================================================
/**
    Saturation as a proximity cue.

    Loud sources drive whatever is carrying them -- preamp, tape, console -- into
    distortion, and physical sources go nonlinear when driven hard: a struck
    snare, a strained voice, the "brassiness" of a horn pushed loud. Up close you
    hear that. At distance you lose it twice: the harmonics are higher in
    frequency so air absorbs them faster, and reverberation dilutes what is left.

    Hence the deliberate ASYMMETRY -- this is nonzero only on the close side.
    A distant source with MORE harmonic distortion than a near one would be
    backwards, so the far side gets none rather than a little.

    The returned value is the soft-clip amount: 0 = no shaping at all, 1 = knee
    starts a full softClipRangeDb below the ceiling.
*/
//  Kept deliberately modest. This is a colour cue, not a crush: the clipper
//  shaves the same transient peaks the CLOSE compressor is trying to preserve,
//  so pushing it hard cancels the punch that defines the close end. Measured at
//  0.55 x 2x (which clamped to full), onset/body at close fell BELOW far --
//  i.e. the saturation had undone the transient design entirely.
inline constexpr float closeSoftClipMax = 0.22f;
inline constexpr float softClipCeilingAmount = 0.35f;   // cap, even at 2x

enum class ClipMode { soft, hard };

inline float distanceSoftClipAmount (float d, float scale) noexcept
{
    if (d <= 0.0f)
        return 0.0f;

    return juce::jlimit (0.0f, softClipCeilingAmount,
                         closeSoftClipMax * std::pow (d, curveExponent) * scale);
}

//==============================================================================
// Parameter range. Exposed here so the processor and the editor agree.
inline constexpr float distanceMin = -100.0f;   // furthest
inline constexpr float distanceMax =  100.0f;   // closest

/** Raw parameter value -> normalised [-1, +1], with a hair-thin dead zone at centre.

    The dead zone is not cosmetic. NormalisableRange's 0.1 step snaps via
    `round((v - min) / 0.1) * 0.1 + min`, and 0.1f is not exactly representable
    in binary -- so "zero" arrives as ~7.6e-6, not 0.0f. Without this snap the
    flat position never compares equal to zero, the flat-skip never engages, and
    a plugin sitting at "flat" quietly runs a not-quite-unity filter over the
    audio. The zone is 0.01 on the -100..+100 scale, an order of magnitude below
    the parameter's own step, so it can only ever catch float noise.
*/
inline float normaliseDistance (float raw) noexcept
{
    const auto d = juce::jlimit (-1.0f, 1.0f, raw / distanceMax);

    return std::abs (d) < 1.0e-4f ? 0.0f : d;
}

} // namespace ShipStudios
