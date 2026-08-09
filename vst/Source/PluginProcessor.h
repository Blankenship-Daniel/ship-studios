#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>

#include <vector>

#include "DistanceCurve.h"
#include "GeminiClient.h"
#include "SourceAnalysis.h"

//==============================================================================
/**
    A distance / proximity effect: one control morphs a four-band EQ curve so the
    source sits closer (fader up) or further away (fader down). Centre is flat.

    The curve itself lives in DistanceCurve.h, shared with the editor's display.

    SIGNAL PATH, in order -- kept as discrete stages so an ambience/wet block can
    later drop in between the EQ and the compressor without restructuring:

        in -> [ input gain ]
           -> [ distance EQ ]
           -> [ compressor ]
           -> [ transient shaper ]
           -> [ loudness compensation + distance level law + output trim ]
           -> [ clip: soft or hard (close only) ]
           -> [ brick-wall limiter ]
           -> out

    Input gain leads because it has to: the compressor's thresholds are fixed in
    dBFS, so driving the input is how you decide how hard the dynamics work.
    Putting it after them would just be a second output trim.

    The compensation cancels the loudness change the EQ causes INCIDENTALLY; the
    distance level law then applies the intended one (6 dB per doubling). Keeping
    those separate is what makes the level law exact rather than
    material-dependent.
*/
class ShipStudiosGainProcessor final : public juce::AudioProcessor,
                                       private juce::AsyncUpdater,
                                       private juce::AudioProcessorValueTreeState::Listener
{
public:
    ShipStudiosGainProcessor();
    ~ShipStudiosGainProcessor() override;

    //==========================================================================
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    //==========================================================================
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override                            { return true; }

    const juce::String getName() const override                { return JucePlugin_Name; }
    bool acceptsMidi() const override                          { return false; }
    bool producesMidi() const override                         { return false; }
    bool isMidiEffect() const override                         { return false; }

    // A biquad EQ rings; give the host a small but non-zero tail.
    double getTailLengthSeconds() const override               { return 0.05; }

    juce::AudioProcessorParameter* getBypassParameter() const override { return bypassParam; }

    //==========================================================================
    // Factory presets exposed through the host's own preset menu as well as the
    // in-plugin list, so they show up wherever the user already looks.
    int getNumPrograms() override;
    int getCurrentProgram() override                           { return currentProgram; }
    void setCurrentProgram (int index) override;
    const juce::String getProgramName (int index) override;
    void changeProgramName (int, const juce::String&) override {}

    struct FactoryPreset
    {
        const char* name;
        float distance;
        bool  extreme;
        bool  hardClip;
        float inputDb;
        float outputDb;
        float ceilingDb;
    };

    static const std::array<FactoryPreset, 8> factoryPresets;

    /** True while every parameter still matches the named preset. Once it does
        not, the UI must stop claiming that preset is loaded. */
    bool matchesProgram (int index) const;

    //==========================================================================
    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    //==========================================================================
    juce::AudioProcessorValueTreeState apvts;

    static constexpr const char* analyseParamID  = "analyse";
    static constexpr const char* geminiParamID   = "gemini";
    static constexpr const char* assistParamID   = "assist";
    static constexpr const char* inputParamID    = "input_db";
    static constexpr const char* distanceParamID = "distance";
    static constexpr const char* outputParamID   = "output_db";
    static constexpr const char* ceilingParamID  = "ceiling_db";
    static constexpr const char* hardClipParamID = "hard_clip";
    static constexpr const char* extremeParamID  = "extreme";
    static constexpr const char* bypassParamID   = "bypass";

    /** Sample rate the UI should draw its curve at. Atomic because the editor
        reads it while the audio thread may be writing it. */
    std::atomic<double> displaySampleRate { 48000.0 };

    /** Peak gain reduction (positive dB) over the last processed block, for the
        compressor meter. Atomic for the same reason. */
    std::atomic<float> displayGainReductionDb { 0.0f };

    /** Same, for the brick-wall limiter. */
    std::atomic<float> displayLimiterGrDb { 0.0f };

    //==========================================================================
    /** Bands + their loudness compensation, published as ONE unit.

        They must swap together: the tables are derived from the bands, so a new
        curve with the old compensation would break the calibrated level law. */
    struct CurveProfile
    {
        std::array<ShipStudios::BandSpec, 4> bands = ShipStudios::factoryBands;
        std::array<float, 201> comp {};
        std::array<float, 201> compExtreme {};
        double sampleRate = 0.0;
        juce::uint32 generation = 0;        // 0 == factory
    };

    /** Snapshot for the editor -- by value, so a swap mid-paint cannot tear. */
    CurveProfile getDisplayProfile() const noexcept
    {
        return profileSlots[(size_t) activeProfile.load (std::memory_order_acquire)];
    }

    void requestAnalysis() noexcept;

    /** Editor entry point: ANALYSE here AND on every linked instance, each
        capturing and adapting to its own source. requestAnalysis() stays the
        single-instance trigger -- it is also the audio-thread parameter path,
        which must never touch the link registry lock. */
    void requestAnalysisGroup();

    void revertToFactory();

    std::atomic<juce::uint32> publishedGeneration { 0 };
    std::atomic<int> captureProgress { 0 };      // samples captured, for the UI
    std::atomic<int> captureCapacity { 0 };

    enum class AnalysisState { idle, capturing, analysing, classifying, assisting, adapted, failed };

    /** Arm a capture whose result goes to the SETTINGS assistant rather than
        the band placement. Same capture, different question. */
    void requestAssist() noexcept;

    /** Set by the worker when the assistant returns; the editor picks it up and
        reports it. Empty until then. */
    juce::String getAssistReasoning() const
    {
        const juce::ScopedLock sl (analysisLabelLock);
        return assistReasoning;
    }
    std::atomic<AnalysisState> analysisState { AnalysisState::idle };
    // Two strings, both worker-written and message-thread read: the SHORT one
    // is what the ANALYSE control can fit on itself, the long one is its
    // tooltip. Deriving the short form in the editor by parsing the long one
    // would break the first time either is reworded.
    juce::String analysisLabel;
    juce::String analysisShortLabel;
    juce::String assistReasoning;
    mutable juce::CriticalSection analysisLabelLock;

    juce::String getAnalysisLabel() const
    {
        const juce::ScopedLock sl (analysisLabelLock);
        return analysisLabel;
    }

    juce::String getAnalysisShortLabel() const
    {
        const juce::ScopedLock sl (analysisLabelLock);
        return analysisShortLabel;
    }

    /** Peak level the compressor's detector saw this block, so the transfer
        curve can show WHERE ON IT you are rather than just its shape. */
    std::atomic<float> displayCompLevelDb { -100.0f };

    /** Same, for the clipper. Without this the clip stage is invisible -- and it
        only engages when driven, so a user can flip SOFT/HARD, hear nothing, and
        reasonably conclude it is broken. */
    std::atomic<float> displayClipGrDb { 0.0f };

    /** Peak level in dBFS at the input (pre-everything) and the output
        (post-limiter), for gain staging. */
    std::atomic<float> displayInputLevelDb  { -100.0f };
    std::atomic<float> displayOutputLevelDb { -100.0f };

    //==========================================================================
    // A/B compare. Two full parameter snapshots, held by the PROCESSOR so they
    // survive the editor being closed and reopened.
    void storeAbSlot (int slot);
    void recallAbSlot (int slot);
    bool hasAbSlot (int slot) const;
    int currentAbSlot = 0;

    //==========================================================================
    // Instance linking: while LINK is lit on two or more instances, a
    // parameter change on any of them is mirrored to all the others -- one
    // fader rides the whole group (all drum mics, say, at the same distance).
    //
    // The group is process-global: every live instance registers in a shared
    // registry, and linked ones mirror each other. No group IDs -- one group,
    // opt in per instance, which is the whole UI. Instances left unlinked are
    // untouched. (Host formats load separate binaries, so an AU instance and a
    // VST3 instance cannot see each other -- in practice a session uses one
    // format, so the limitation is theoretical.)
    //
    // What MIRRORS (same value everywhere): the SOUND parameters (distance,
    // input, output, ceiling, clip mode, 2x, bypass) -- and therefore presets
    // too, since loading one just sets those.
    //
    // What GROUP-FIRES but stays per-instance in its RESULT: the ANALYSE and
    // AUTO-gain triggers. One click arms/fires all linked instances, but each
    // captures and measures ITS OWN audio and applies its own outcome --
    // adapted bands for analysis, gain staging for auto-gain (whose applies
    // are exempted from mirroring so peers cannot stamp over each other).
    // The GEMINI privacy opt-in never propagates: uploading audio to Google
    // is a per-instance decision, made explicitly on each instance.
    //
    // Loop-safety: changes propagate only from the instance the change
    // ORIGINATED on (a mirrored write is flagged and never re-broadcast), and
    // a peer already at the target value is skipped, so propagation always
    // terminates. Parameter callbacks can arrive on the audio thread, so the
    // broadcast itself is coalesced onto the message thread via the async
    // updater -- never done in the callback.
    void setLinkEnabled (bool shouldLink);
    bool isLinkEnabled() const noexcept    { return linkEnabled.load(); }

    //==========================================================================
    // Auto gain staging: scan the WHOLE region being played, then set INPUT
    // and OUTPUT together in one move.
    //
    // Every stage downstream of the input gain is fixed in absolute dBFS -- the
    // compressor thresholds (-18 close / -24 far), the clip knee, the limiter
    // ceiling. A source arriving 12 dB hot gets crushed; one 12 dB shy coasts
    // through a chain that barely engages. INPUT is the calibration control,
    // and this automates finding its value. OUTPUT is then set to MIRROR the
    // input move (clamped to its own +/-12 range): drive the chain correctly
    // without changing the track's level in the mix -- the classic
    // gain-staging move, done as one gesture so the two can never disagree.
    //
    // Measurement is K-weighted (BS.1770), same as the loudness compensation
    // table and for the same reason: the thing being levelled is LOUDNESS, not
    // broadband energy. The target is -18 LUFS -- the classic reference
    // operating level -- capped so the learned peak lands no higher than
    // -3 dBFS, whichever asks for LESS gain. The cap matters because the close
    // end ADDS up to +6 dB of shelf before the dynamics: peaks already at -1
    // would hand the limiter a job the compressor was supposed to have.
    //
    // Lifecycle: autoGainStart() arms an OPEN-ENDED scan -- there is no fixed
    // window, so it covers however much of the region you play (silence never
    // counts, so arming before pressing play is fine). It ends and applies in
    // either of two ways: a second click, or the host transport STOPPING after
    // enough signal has been heard -- so "arm, play the region to the end,
    // stop" needs no second click. The apply runs via an async update on the
    // processor, so it completes even with the editor closed. Where no
    // transport exists (standalone), the second click is the only ending.
    //
    // LINKED instances arm and finish TOGETHER, but each scans its own audio
    // and applies its own result -- the trigger is group-wide, the measurement
    // never is. The applies are exempted from link mirroring for the same
    // reason: five mics need five gain stagings, not the last one five times.
    void autoGainStart();

    /** Second click while scanning: apply with what has been heard so far --
        or, if there has been next to no signal yet, just cancel. Propagates
        across the link group like the start does. */
    void autoGainFinishEarly();

    bool  isAutoGainLearning() const   { return autoGainLearning.load(); }

    /** Seconds of non-silent audio heard so far, for the UI. Open-ended. */
    float autoGainSecondsHeard() const { return autoGainProgressPub.load(); }

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    void setParameterValue (const juce::String& id, float value);

    int currentProgram = 0;
    juce::ValueTree abSlots[2];

    void updateCoefficients (const CurveProfile&, float normalisedDistance, float scale) noexcept;

    /** Compresses in place and returns the makeup gain its settings call for. */
    float processCompressor (juce::dsp::AudioBlock<float>& block,
                             float normalisedDistance,
                             float scale) noexcept;

    /** Level-independent attack/sustain shaping, driven by the same fader. */
    void processTransient (juce::dsp::AudioBlock<float>& block,
                           float normalisedDistance,
                           float scale) noexcept;

    /** Waveshaper, bounded by the ceiling in steady state. Amount comes from
        the distance fader, not a control of its own -- saturation is a
        proximity cue, so it belongs on the same axis as everything else. Shape
        is chosen by the clip-mode switch.

        Anti-aliased with first-order ADAA applied to the clip CORRECTION
        (f(x) - x), not the whole transfer: below the knee the correction is
        identically zero, so the sub-threshold path stays bit-exact while the
        alias-generating part is band-limited. See the .cpp for the math. */
    void processClip (juce::dsp::AudioBlock<float>& block,
                      float normalisedDistance,
                      float scale,
                      float ceilingDb) noexcept;

    /** Lookahead brick-wall limiter. Final stage; operates on the whole block. */
    void processLimiter (juce::AudioBuffer<float>& buffer,
                         bool bypassed,
                         float ceilingDb) noexcept;

    void buildCompensationTables (const std::array<ShipStudios::BandSpec, 4>& bands, double sampleRate,
                                  std::array<float, 201>& out1x,
                                  std::array<float, 201>& out2x) const;
    void publishProfile (const std::array<ShipStudios::BandSpec, 4>& bands, double sampleRate);

    /** publishProfile has two callers on two threads -- the analysis worker and
        the editor's FACTORY button -- and it advances `nextWriteSlot`. Without
        this they could pick the same slot. The audio thread never takes it; it
        only reads `activeProfile`. */
    juce::CriticalSection publishLock;
    float compensationDbFor (const CurveProfile&, float normalisedDistance,
                             float scale) const noexcept;

    //==========================================================================
    // One duplicator per band: IIR::Filter is mono-only and asserts on a stereo
    // block, so the duplicator fans one shared coefficient set across channels.
    using Band = juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>,
                                                juce::dsp::IIR::Coefficients<float>>;
    juce::dsp::ProcessorChain<Band, Band, Band, Band> eqChain;

    std::atomic<float>* inputDbParam = nullptr;
    std::atomic<float>* distanceParam = nullptr;
    std::atomic<float>* outputDbParam = nullptr;
    std::atomic<float>* ceilingParam = nullptr;
    std::atomic<float>* analyseParam = nullptr;   // cached like the rest: no map lookup per block
    juce::AudioParameterBool* bypassParam = nullptr;
    juce::AudioParameterBool* extremeParam = nullptr;
    juce::AudioParameterBool* hardClipParam = nullptr;

    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> inputGainSmoothed;
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> distanceSmoothed;
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> gainSmoothed;

    // 2x is smoothed, not switched: flipping it mid-playback would step every
    // band gain and the compressor threshold at once, which clicks audibly.
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> scaleSmoothed;

    // Ceiling is smoothed too (in dB): it feeds the clip threshold and the
    // limiter target, and an unsmoothed automation step would zipper both.
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> ceilingSmoothed;

    double currentSampleRate = 48000.0;

    static constexpr int compTableSize = 201;

    // THREE slots, not two: during the swap fade the audio thread holds the old
    // and the new generation at once, so a two-slot rotation could scribble on a
    // slot still being read.
    //
    // Three is enough ONLY because publishes are human- or network-paced: a
    // THIRD publish landing inside one 40 ms swap fade would rotate
    // nextWriteSlot back onto the slot the audio thread is still fading out
    // of. Every current publisher (analysis worker, FACTORY, state restore)
    // is orders of magnitude slower than the fade -- if a publish path ever
    // becomes programmatic/rapid, widen the rotation or gate on the fade.
    std::array<CurveProfile, 3> profileSlots;
    std::atomic<int> activeProfile { 0 };

    // Swapping band FREQUENCIES under a live signal steps the transfer function
    // -- a click. So the EQ's own `d` is faded to 0 (where the curve is unity
    // for ANY frequency or Q), the profile is adopted there, and `d` is ramped
    // back. Only the EQ and its compensation ride the fade; the level law,
    // compressor, shaper and clipper stay on the real `d` throughout, so the
    // swap is inaudible rather than a dip.
    //
    // NOT filter reset(): a biquad given new stable coefficients stays stable,
    // and discarding its ring-out CREATES the discontinuity it looks like it
    // prevents.
    enum class SwapPhase { none, fadingOut, fadingIn };
    SwapPhase swapPhase = SwapPhase::none;
    int appliedSlot = 0;                         // audio thread only
    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> swapFade { 1.0f };
    static constexpr double swapFadeSeconds = 0.04;
    int nextWriteSlot = 1;                       // worker-thread only
    juce::uint32 generationCounter = 0;

    //==========================================================================
    // Capture. Filled from processBlock BEFORE the input gain, so the analysis
    // measures the raw source rather than the curve this plugin just imposed --
    // otherwise analysing at FAR would walk the bands further out every press.
    juce::AudioBuffer<float> captureBuffer;

    /** Held by prepareToPlay while it RESIZES the buffer, and by the worker
        while it READS it. Neither is realtime; the audio thread never takes it
        (it only writes into an already-sized buffer under captureState). Without
        this a host reconfigure during an analysis would realloc under the
        worker's read pointer. */
    juce::CriticalSection captureBufferLock;
    std::atomic<int> captureWritePos { 0 };
    std::atomic<float> capturePeak { 0.0f };
    enum class CaptureState { idle, capturing, full };
    std::atomic<CaptureState> captureState { CaptureState::idle };
    double captureSampleRate = 48000.0;
    // Capture 30 s, MEASURE 10 s of it. The extra 20 s exists so something can
    // choose WHICH ten -- fitting the bands to whatever happened to be under the
    // playhead is how you end up describing a count-in or, measured on this
    // repo's own overhead stems, eleven seconds of spoken-word bleed.
    static constexpr double captureSeconds = 30.0;
    static constexpr double analysisWindowSeconds = 10.0;

    bool lastAnalyseTrigger = false;
    bool lastAssistTrigger = false;

    /** Which question the armed capture is for. One buffer, two consumers. */
    enum class CaptureIntent { adaptBands, suggestSettings };
    std::atomic<CaptureIntent> captureIntent { CaptureIntent::adaptBands };
    bool assistArming = false;

    void runAssist (const juce::AudioBuffer<float>& capture, double rate);
    void applySuggestedSettings (const ShipStudios::GeminiClient::Settings&);

    /** Polls its own atomic rather than using a message-thread Timer: the
        pedalboard verification harness runs with NO message loop, so a Timer
        would never fire and the feature would be untestable. */
    class AnalysisWorker final : public juce::Thread
    {
    public:
        explicit AnalysisWorker (ShipStudiosGainProcessor& p)
            : juce::Thread ("ShipStudios Analysis"), owner (p) {}
        void run() override;
    private:
        ShipStudiosGainProcessor& owner;
    };

    std::unique_ptr<AnalysisWorker> worker;
    void runAnalysis();

    /** Teardown's handle on an in-flight Gemini request. stopThread's timeout
        FORCE-KILLS a thread that will not exit, and the classification leg can
        block inside a network read for longer than any tolerable timeout --
        cancelling the stream first is what lets the worker actually exit.
        Re-armed whenever the worker (re)starts. */
    ShipStudios::NetworkCancel geminiCancel;

    /** True once the worker has been asked to exit. The classification leg can
        sit on a socket for 20 s, so it must not publish into a processor that
        is being torn down. */
    bool threadShouldStopAnalysis() const noexcept
    {
        return worker == nullptr || worker->threadShouldExit();
    }

    // Coefficients are stepped once per sub-block rather than per sample; JUCE
    // ships no coefficient smoother, so this is the standard trade.
    //
    // Measured, not guessed: halving this to 16 moved the automation-sweep
    // result by 0.0001 (0.05985 -> 0.05991), i.e. not at all. Coefficient
    // stepping is nowhere near the limiting factor at this smoothing rate, so
    // 32 stands and the extra updates would have bought nothing.
    static constexpr int updateChunkSamples = 32;

    // At the centre position every band is unity, but a unity biquad is only
    // unity in exact arithmetic -- in float, the normalised coefficients leave
    // roughly 1e-6 of rounding per sample. Skipping the filters outright is what
    // makes "flat" genuinely bit-exact (and free). We wait a couple of blocks
    // first so the filters' state has decayed, otherwise dropping out of the
    // chain would strand live state and click on the way back in.
    int flatBlocks = 0;
    float lastAppliedDistance = 2.0f;   // impossible value -> forces a first update
    float lastAppliedScale = 0.0f;      // ditto

    // WITHOUT this the coefficient update is skipped whenever d and scale are
    // unchanged -- so with a static fader a freshly analysed profile would never
    // reach the filters, while every indicator still said ADAPTED.
    juce::uint32 lastAppliedGeneration = 0xffffffffu;
    static constexpr int flatBlocksBeforeSkip = 3;

    // Pre-detector peak hold for the COMPRESSOR's sidechain.
    //
    // Instant attack, ~2 ms exponential decay on the LINEAR peak, applied
    // BEFORE the dB-domain gain-reduction follower. Without it, a detector as
    // fast as the far side's 0.3 ms attack tracks individual cycles below
    // ~1 kHz and modulates gain at twice the fundamental -- harmonic
    // distortion on sustained tonal material, on the FAR side, where the
    // saturation model says there should be none. The hold bridges half-cycles
    // without touching onsets: attack is still instantaneous, and 2 ms is
    // negligible against the 120-300 ms releases that govern decay.
    //
    // The transient shaper deliberately does NOT get this hold -- it feeds on
    // follower contrast, which the hold flattens (see processTransient).
    static constexpr double detectorHoldSeconds = 0.002;
    float detectorHoldCoeff = 0.0f;
    float compDetectorPeak = 0.0f;

    // Transient shaper: three envelope followers on a stereo-linked detector.
    // fast-vs-slow ATTACK gives the onset differential; long-vs-fast RELEASE
    // gives the sustain differential. Fixed times -- the fader moves the
    // AMOUNTS, not the ballistics, so the shaper's character stays constant
    // while its direction reverses across the fader.
    float envFastDb = -100.0f;
    float envSlowDb = -100.0f;
    float envLongDb = -100.0f;
    float transAttackFastCoeff = 0.0f;
    float transAttackSlowCoeff = 0.0f;
    float transReleaseCoeff = 0.0f;
    float transReleaseLongCoeff = 0.0f;

    // Running mean of the shaper's own gain, subtracted so it alters envelope
    // CONTRAST without altering level. Without this the shaper moved integrated
    // loudness by up to 2.5 LU and broke the calibrated distance level law
    // (measured far -8.59 LU against a -6.0 target). 400 ms is long enough to
    // span a hit and its tail, so the within-hit contrast survives intact.
    float transAverageGainDb = 0.0f;
    float transAverageCoeff = 0.0f;
    static constexpr double transAverageSeconds = 0.400;

    static constexpr double transAttackFastMs = 0.5;
    static constexpr double transAttackSlowMs = 20.0;
    static constexpr double transReleaseMs = 60.0;
    static constexpr double transReleaseLongMs = 350.0;

    // Compressor state. One shared gain-reduction envelope drives every channel,
    // so the stereo image cannot wander as the two sides duck independently.
    float gainReductionDb = 0.0f;

    // Makeup = the gain reduction actually being applied, averaged slowly.
    // Long enough (200 ms) that it does not pump against the compressor's own
    // release, short enough to settle within a phrase.
    float averageGainReductionDb = 0.0f;

    // Settings + ballistics coefficients cached against (d, scale): they only
    // change when the fader moves, so recomputing three std::exp per chunk was
    // pure waste. Impossible initial values force the first computation.
    ShipStudios::CompressorSettings compSettings { 1.0f, 0.0f, 20.0f, 200.0f };
    float compCachedD = 2.0f;
    float compCachedScale = 0.0f;
    float compAttackCoeff = 0.0f;
    float compReleaseCoeff = 0.0f;
    float compAverageCoeff = 0.0f;   // 200 ms, depends only on sample rate

    // Per-block meter accumulators. The stage functions run once per 32-sample
    // chunk; storing to the atomics per chunk meant the UI only ever saw the
    // LAST chunk's peak. These accumulate across the block and are stored once
    // at the end -- which also resets the clip meter when bypass stops the
    // clip stage from running at all.
    float blockCompGrMax = 0.0f;
    float blockCompLevelMax = -100.0f;
    float blockClipGrMax = 0.0f;

    // ADAA state for the clipper: previous input sample per channel. Reseeded
    // whenever the stage re-engages so a stale sample from minutes ago cannot
    // corrupt the first frame.
    float clipPrevX[2] {};
    bool clipStateValid = false;

    //==========================================================================
    // Brick-wall limiter.
    //
    // Lookahead is what makes it a BRICK WALL rather than a fast compressor: the
    // control signal is computed from samples that have not been output yet, so
    // the gain is already down by the time the peak arrives. The cost is
    // latency, which is reported to the host via setLatencySamples so it can
    // compensate -- this plugin is no longer zero-latency.
    //
    // Control chain, per sample:
    //   1. required reduction, from the sample ENTERING the delay line
    //   2. two-block sliding max holds it across the lookahead window
    //   3. instant-attack / exponential-release follower
    //   4. boxcar moving average over exactly the lookahead window
    // The boxcar is what shapes the ATTACK: it turns any step in the control
    // into a linear ramp that completes precisely when the offending peak
    // leaves the delay. The previous design slewed the gain at a fixed
    // 0.5 dB/sample instead -- corners that sharp amplitude-modulate the
    // programme and put audible sidebands on bass-heavy material, and its
    // fixed slope silently capped the catchable demand at 48 dB per window.
    // A ramp spread over the whole window has neither problem: it is the
    // smoothest trajectory that still meets the deadline, for ANY demand.
    //
    // The ceiling guarantee is by construction: every term the boxcar averages
    // at the moment a sample exits is >= that sample's own requirement (held
    // there by the sliding max), so the average is too.
    //
    // KNOWN LIMITATION: this is a SAMPLE-peak limiter. Inter-sample peaks can
    // still exceed the ceiling by ~0.3-1 dB after DAC reconstruction or lossy
    // encoding. True-peak would need an oversampled detector (~4x on the
    // sidechain only); do that before advertising a dBTP ceiling.
    juce::AudioBuffer<float> limiterDelay;
    int lookaheadSamples = 96;      // ~2 ms, recomputed per sample rate
    int limiterWritePos = 0;        // shared by the delay AND the boxcar ring
    float limiterGrDb = 0.0f;       // the follower (stage 3)
    float limiterReleaseCoeff = 0.0f;

    // Boxcar state (stage 4): ring buffer of follower output + running sum.
    // The sum is double so hours of accumulation cannot drift the gain.
    std::vector<float> limiterSmoothBuf;
    double limiterSmoothSum = 0.0;

    // Sliding maximum of the required reduction over the lookahead window,
    // via the classic two-block trick (O(1) per sample).
    //
    // Without this the control signal is the INSTANTANEOUS requirement, which
    // releases between the moment a peak is seen and the moment that same peak
    // reaches the output -- so the gain has crept back up by the time it is
    // needed. Measured overshoot was +0.58 dB at 1x and +1.16 dB at 2x. Holding
    // the maximum across the whole window removes that by construction.
    float limiterBlockMax = 0.0f;
    float limiterPrevBlockMax = 0.0f;
    int limiterBlockCounter = 0;

    // At 100% the knee starts this far below the ceiling.
    static constexpr float softClipRangeDb = 12.0f;

    static constexpr double lookaheadSeconds = 0.002;
    static constexpr double limiterReleaseSeconds = 0.150;

    //==========================================================================
    // Auto input gain -- see the public API block above for the doctrine.
    //
    // Ownership: the plain accumulators belong to the AUDIO thread and are only
    // touched while `autoGainLearning` is true (started via the reset-pending
    // handshake, so the audio thread cannot observe learning without the
    // reset). The *Pub atomics are published snapshots; the MESSAGE thread
    // computes and applies the result from those alone.
    void handleAsyncUpdate() override;
    void processAutoGainLearn (const juce::AudioBuffer<float>& buffer,
                               int numChannels, int numSamples,
                               float blockPeak) noexcept;
    void computeAndApplyAutoGain();

    // Live BS.1770 K-weighting for the learn measurement, one pair per channel
    // (same curve the compensation table is built from).
    juce::dsp::IIR::Filter<float> kWeightShelf[2];
    juce::dsp::IIR::Filter<float> kWeightHighPass[2];

    // Audio-thread-owned accumulators.
    double autoGainSumSquares = 0.0;
    juce::int64 autoGainSamples = 0;
    float autoGainPeak = 0.0f;

    std::atomic<bool>        autoGainLearning { false };
    std::atomic<bool>        autoGainResetPending { false };
    std::atomic<double>      autoGainSumSquaresPub { 0.0 };
    std::atomic<juce::int64> autoGainSamplesPub { 0 };
    std::atomic<float>       autoGainPeakPub { 0.0f };
    std::atomic<float>       autoGainProgressPub { 0.0f };

    // Transport edge detector for the auto-apply-on-stop ending. Audio-thread
    // only; meaningful only while a host actually reports a transport.
    bool autoGainWasPlaying = false;

    static constexpr double autoGainMinSeconds   = 0.5;   // below this: cancel

    //==========================================================================
    // Instance-link internals -- see the public block for the doctrine.
    //
    // parameterChanged may fire on any thread; it only sets a dirty bit and
    // pokes the (shared) AsyncUpdater. handleAsyncUpdate multiplexes its two
    // producers by pending-flag: auto-gain sets autoGainApplyPending, the link
    // just leaves a non-zero dirty mask.
    void parameterChanged (const juce::String& parameterID, float newValue) override;
    void broadcastLinkChanges();
    void applyRemoteLink (const char* paramID, float normalisedValue);

    /** Message-thread only: every OTHER linked instance (empty if this one is
        not itself linked). Group trigger fan-out uses this. */
    juce::Array<ShipStudiosGainProcessor*> linkedPeers() const;

    // The per-instance halves of the group triggers: what the public entry
    // points run locally and on each peer. Never propagate themselves.
    void autoGainStartLocal();
    void autoGainFinishEarlyLocal();

    static constexpr std::array<const char*, 7> linkSyncedParams {
        inputParamID, distanceParamID, outputParamID, ceilingParamID,
        hardClipParamID, extremeParamID, bypassParamID };

    std::atomic<bool>          linkEnabled { false };
    std::atomic<bool>          applyingRemoteLink { false };
    std::atomic<juce::uint32>  linkDirtyMask { 0 };
    std::atomic<bool>          autoGainApplyPending { false };
    static constexpr float  autoGainGateDb       = -60.0f;
    static constexpr float  autoGainTargetLufs   = -18.0f;
    static constexpr float  autoGainMaxPeakDb    = -3.0f;

    JUCE_DECLARE_WEAK_REFERENCEABLE (ShipStudiosGainProcessor)
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ShipStudiosGainProcessor)
};
