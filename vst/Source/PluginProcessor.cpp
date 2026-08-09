#include "PluginProcessor.h"
#include "GeminiClient.h"
#include "PluginEditor.h"

using namespace ShipStudios;

//==============================================================================
// The instance-link registry. Process-global by design: every live instance
// registers here, and LINKed ones mirror each other's parameters. Guarded by
// its own lock; registration, unregistration and broadcast all happen on the
// message thread, so a pointer snapshotted under the lock cannot be deleted
// out from under a broadcast in progress.
namespace
{
juce::Array<ShipStudiosGainProcessor*> linkRegistry;
juce::CriticalSection linkRegistryLock;
} // namespace

//==============================================================================
ShipStudiosGainProcessor::ShipStudiosGainProcessor()
    : AudioProcessor (BusesProperties()
                          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "PARAMETERS", createParameterLayout())
{
    inputDbParam  = apvts.getRawParameterValue (inputParamID);
    distanceParam = apvts.getRawParameterValue (distanceParamID);
    outputDbParam = apvts.getRawParameterValue (outputParamID);
    ceilingParam  = apvts.getRawParameterValue (ceilingParamID);
    analyseParam  = apvts.getRawParameterValue (analyseParamID);
    bypassParam   = dynamic_cast<juce::AudioParameterBool*> (apvts.getParameter (bypassParamID));
    extremeParam  = dynamic_cast<juce::AudioParameterBool*> (apvts.getParameter (extremeParamID));
    hardClipParam = dynamic_cast<juce::AudioParameterBool*> (apvts.getParameter (hardClipParamID));

    jassert (inputDbParam != nullptr);
    jassert (distanceParam != nullptr);
    jassert (outputDbParam != nullptr);
    jassert (ceilingParam != nullptr);
    jassert (analyseParam != nullptr);
    jassert (bypassParam != nullptr);
    jassert (extremeParam != nullptr);
    jassert (hardClipParam != nullptr);

    // Instance link: listen to every syncable parameter, and join the
    // process-global registry. Listening is unconditional -- the callback
    // itself checks whether LINK is lit, so toggling the group on and off
    // never has to re-wire listeners.
    for (const auto* id : linkSyncedParams)
        apvts.addParameterListener (id, this);

    {
        const juce::ScopedLock sl (linkRegistryLock);
        linkRegistry.add (this);
    }
}

ShipStudiosGainProcessor::~ShipStudiosGainProcessor()
{
    // Not every host calls releaseResources before deleting the plugin, and
    // juce::Thread's own destructor responds to a still-running thread by
    // KILLING it after a grace period -- mid-network-read that is a leak at
    // best. Cancel any in-flight request so the worker can actually exit,
    // then stop it here, before member destruction begins.
    geminiCancel.cancel();

    if (worker != nullptr)
    {
        worker->stopThread (5000);
        worker.reset();
    }

    {
        const juce::ScopedLock sl (linkRegistryLock);
        linkRegistry.removeFirstMatchingValue (this);
    }

    for (const auto* id : linkSyncedParams)
        apvts.removeParameterListener (id, this);

    cancelPendingUpdate();
}

juce::AudioProcessorValueTreeState::ParameterLayout
ShipStudiosGainProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    // Non-automatable: it is a momentary action, not something to draw a curve
    // for. But it IS a parameter, which is what lets the pedalboard harness
    // trigger analysis -- it cannot press a button.
    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { analyseParamID, 1 }, "Analyse", false,
        juce::AudioParameterBoolAttributes().withAutomatable (false)));

    // OFF by default, and it must stay that way: switching it on means pressing
    // ANALYSE uploads ~10 s of the user's audio to Google. That is a decision
    // for them to make explicitly, not a consequence of a key being present.
    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { geminiParamID, 1 }, "Gemini", false,
        juce::AudioParameterBoolAttributes().withAutomatable (false)));

    // Momentary, like `analyse`: a rising edge arms a capture whose answer goes
    // to the settings assistant instead of the band placement. A parameter
    // rather than a button so the harness can trigger it.
    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { assistParamID, 1 }, "Assist", false,
        juce::AudioParameterBoolAttributes().withAutomatable (false)));

    layout.add (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID { inputParamID, 1 },
        "Input",
        juce::NormalisableRange<float> (-24.0f, 24.0f, 0.1f),
        0.0f,
        juce::AudioParameterFloatAttributes().withLabel ("dB")));

    layout.add (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID { distanceParamID, 1 },
        "Distance",
        juce::NormalisableRange<float> (distanceMin, distanceMax, 0.1f),
        0.0f));

    layout.add (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID { outputParamID, 1 },
        "Output",
        juce::NormalisableRange<float> (-12.0f, 12.0f, 0.1f),
        0.0f,
        juce::AudioParameterFloatAttributes().withLabel ("dB")));

    layout.add (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID { ceilingParamID, 1 },
        "Ceiling",
        juce::NormalisableRange<float> (-12.0f, 0.0f, 0.1f),
        -0.3f,
        juce::AudioParameterFloatAttributes().withLabel ("dB")));

    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { hardClipParamID, 1 },
        "Hard Clip",
        false));

    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { extremeParamID, 1 },
        "Extreme",
        false));

    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { bypassParamID, 1 },
        "Bypass",
        false));

    return layout;
}

//==============================================================================
void ShipStudiosGainProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    displaySampleRate.store (sampleRate);

    const juce::dsp::ProcessSpec spec {
        sampleRate,
        (juce::uint32) juce::jmax (1, samplesPerBlock),
        (juce::uint32) juce::jmax (1, getTotalNumOutputChannels())
    };

    // NEVER replace `.state` with a new Ptr -- only ever assign THROUGH it.
    //
    // ProcessorDuplicator::prepare() constructs one filter per channel, each
    // capturing the state Ptr, and on a second prepare() it REUSES the filters
    // it already built. So swapping the Ptr here would leave those filters
    // pointing at the previous Coefficients object, and every subsequent
    // `*state = ...` would write somewhere nothing is reading. The symptom is
    // brutal to diagnose: the EQ silently freezes at whatever curve was written
    // during the first prepare, while everything else keeps responding.
    eqChain.prepare (spec);
    eqChain.reset();

    // Mandatory, not just a warm-up: a default-constructed IIR::Coefficients is
    // all zeros, which is SILENCE rather than passthrough. This first assignment
    // also grows the backing array to capacity, so every later assignment on the
    // audio thread is allocation-free.
    updateCoefficients (profileSlots[(size_t) activeProfile.load()], 0.0f, 1.0f);
    lastAppliedDistance = 0.0f;
    gainReductionDb = 0.0f;
    averageGainReductionDb = 0.0f;
    displayGainReductionDb.store (0.0f);

    // Lookahead sized in TIME, not samples, so the limiter behaves the same at
    // any sample rate. Reported to the host: this plugin now has latency.
    lookaheadSamples = juce::jmax (1, (int) std::round (lookaheadSeconds * sampleRate));
    limiterDelay.setSize (juce::jmax (1, getTotalNumOutputChannels()), lookaheadSamples);
    limiterDelay.clear();
    limiterSmoothBuf.assign ((size_t) lookaheadSamples, 0.0f);
    limiterSmoothSum = 0.0;
    limiterWritePos = 0;
    limiterGrDb = 0.0f;
    limiterBlockMax = 0.0f;
    limiterPrevBlockMax = 0.0f;
    limiterBlockCounter = 0;
    displayLimiterGrDb.store (0.0f);

    const auto coeff = [sampleRate] (double ms)
    {
        return 1.0f - std::exp (-1.0f / (float) (0.001 * ms * sampleRate));
    };

    transAttackFastCoeff = coeff (transAttackFastMs);
    transAttackSlowCoeff = coeff (transAttackSlowMs);
    transReleaseCoeff = coeff (transReleaseMs);
    transReleaseLongCoeff = coeff (transReleaseLongMs);
    transAverageCoeff = 1.0f - std::exp (-1.0f / (float) (transAverageSeconds * sampleRate));
    envFastDb = envSlowDb = envLongDb = -100.0f;
    transAverageGainDb = 0.0f;

    // NB decay coefficient, not a one-pole mix: the detector is
    // max (peak, held * coeff), so this is exp(), not 1 - exp().
    detectorHoldCoeff = std::exp (-1.0f / (float) (detectorHoldSeconds * sampleRate));
    compDetectorPeak = 0.0f;

    compAverageCoeff = 1.0f - std::exp (-1.0f / (float) (0.200 * sampleRate));
    compCachedD = 2.0f;       // impossible -> forces a recompute on first use
    compCachedScale = 0.0f;

    clipStateValid = false;

    limiterReleaseCoeff = 1.0f - std::exp (-1.0f / (float) (limiterReleaseSeconds * sampleRate));

    setLatencySamples (lookaheadSamples);

    {
        const juce::ScopedLock sl (captureBufferLock);
        captureSampleRate = sampleRate;
        const auto cap = (int) std::ceil (captureSeconds * sampleRate);
        captureBuffer.setSize (1, cap, false, true, false);
        captureBuffer.clear();
        captureCapacity.store (cap);
        captureWritePos.store (0);
        captureProgress.store (0);
        captureState.store (CaptureState::idle);
    }

    // Slot 0 is always the factory profile, rebuilt for this sample rate. The
    // FREQUENCIES are rate-independent but the compensation tables are not.
    //
    // Under publishLock: this loop is a THIRD writer of profileSlots, next to
    // the analysis worker and revertToFactory. A host reconfigure landing
    // while the worker is mid-publishProfile would otherwise be two
    // unsynchronised writers on the same slot.
    {
        const juce::ScopedLock sl (publishLock);

        for (auto& slot : profileSlots)
        {
            if (slot.generation == 0)
                slot.bands = factoryBands;

            buildCompensationTables (slot.bands, sampleRate, slot.comp, slot.compExtreme);
            slot.sampleRate = sampleRate;
        }
    }

    lastAppliedGeneration = 0xffffffffu;

    swapFade.reset (sampleRate, swapFadeSeconds);
    swapFade.setCurrentAndTargetValue (1.0f);
    swapPhase = SwapPhase::none;
    appliedSlot = activeProfile.load();

    if (worker == nullptr)
    {
        // Re-arm BEFORE the thread exists: a cancel latched by a previous
        // teardown would otherwise abort this worker's first classify.
        geminiCancel.rearm();
        worker = std::make_unique<AnalysisWorker> (*this);
        worker->startThread (juce::Thread::Priority::low);
    }

    // A live auto-gain learn does not survive a reconfigure: its accumulators
    // count samples at the OLD rate, so carrying them across would mis-time
    // the window. Cancelling is cheaper than converting, and this is rare.
    autoGainLearning.store (false);
    autoGainProgressPub.store (0.0f);

    // Same K-weighting the compensation table uses, as live filters for the
    // learn measurement. Allocates -- which is why it happens here, not there.
    const auto kShelfLive = juce::dsp::IIR::Coefficients<float>::makeHighShelf (
        sampleRate, 1681.0f, 0.7071f, juce::Decibels::decibelsToGain (3.99f));
    const auto kHighPassLive = juce::dsp::IIR::Coefficients<float>::makeHighPass (
        sampleRate, 38.0f, 0.5f);

    for (auto& f : kWeightShelf)    { f.coefficients = kShelfLive;    f.reset(); }
    for (auto& f : kWeightHighPass) { f.coefficients = kHighPassLive; f.reset(); }

    const bool bypassed = bypassParam->get();
    const auto d = bypassed ? 0.0f : normaliseDistance (distanceParam->load());

    // Starting at centre with freshly reset filters: their state is already
    // zero, so the skip is safe from the very first sample rather than after a
    // settle window. That is what makes a flat instance bit-exact end to end.
    flatBlocks = juce::exactlyEqual (d, 0.0f) ? flatBlocksBeforeSkip : 0;

    inputGainSmoothed.reset (sampleRate, 0.02);
    inputGainSmoothed.setCurrentAndTargetValue (
        bypassed ? 1.0f : juce::Decibels::decibelsToGain (inputDbParam->load()));

    distanceSmoothed.reset (sampleRate, 0.05);
    distanceSmoothed.setCurrentAndTargetValue (d);

    const auto scale = (! bypassed && extremeParam->get()) ? extremeScale : 1.0f;
    scaleSmoothed.reset (sampleRate, 0.05);
    scaleSmoothed.setCurrentAndTargetValue (scale);

    ceilingSmoothed.reset (sampleRate, 0.02);
    ceilingSmoothed.setCurrentAndTargetValue (ceilingParam->load());

    gainSmoothed.reset (sampleRate, 0.02);
    gainSmoothed.setCurrentAndTargetValue (
        bypassed ? 1.0f
                 : juce::Decibels::decibelsToGain (compensationDbFor (
                                                       profileSlots[(size_t) activeProfile.load()],
                                                       d, scale)
                                                       + distanceLevelDb (d, scale)
                                                       + outputDbParam->load()));
}

void ShipStudiosGainProcessor::releaseResources()
{
    if (worker != nullptr)
    {
        // Cancel first: the classification leg can sit inside a network read
        // far longer than any stopThread timeout, and a timed-out stopThread
        // KILLS the thread rather than joining it. With the stream cancelled
        // the read returns immediately and the join is real.
        geminiCancel.cancel();
        worker->stopThread (5000);
        worker.reset();
    }

    eqChain.reset();
    limiterDelay.clear();
    std::fill (limiterSmoothBuf.begin(), limiterSmoothBuf.end(), 0.0f);
    limiterSmoothSum = 0.0;
    limiterWritePos = 0;
    limiterGrDb = 0.0f;
    limiterBlockMax = 0.0f;
    limiterPrevBlockMax = 0.0f;
    limiterBlockCounter = 0;
    compDetectorPeak = 0.0f;
    clipStateValid = false;
}

bool ShipStudiosGainProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto& out = layouts.getMainOutputChannelSet();

    if (out != juce::AudioChannelSet::mono() && out != juce::AudioChannelSet::stereo())
        return false;

    // Effect, not a converter: in and out must match.
    return out == layouts.getMainInputChannelSet();
}

//==============================================================================
void ShipStudiosGainProcessor::updateCoefficients (const CurveProfile& profile,
                                                   float d, float scale) noexcept
{
    // Assign THROUGH the shared state Ptr -- ArrayCoefficients allocates nothing,
    // and one write updates every channel's filter at once.
    // profile.bands, NOT factoryBands: reading the factory table here is exactly
    // the silent no-op this refactor exists to avoid -- it compiles, the profile
    // swaps, every indicator says ADAPTED, and the filters never move.
    *eqChain.get<0>().state = makeArrayCoefficients (profile.bands[0], d, currentSampleRate, scale);
    *eqChain.get<1>().state = makeArrayCoefficients (profile.bands[1], d, currentSampleRate, scale);
    *eqChain.get<2>().state = makeArrayCoefficients (profile.bands[2], d, currentSampleRate, scale);
    *eqChain.get<3>().state = makeArrayCoefficients (profile.bands[3], d, currentSampleRate, scale);
}

void ShipStudiosGainProcessor::buildCompensationTables (const std::array<BandSpec, 4>& bands,
                                                        double sampleRate,
                                                        std::array<float, 201>& out1x,
                                                        std::array<float, 201>& out2x) const
{
    // Log-spaced probes: pink noise carries equal energy per octave, so log
    // spacing already bakes in a pink weighting.
    constexpr int numProbes = 96;
    const double loHz = 20.0;
    const double hiHz = juce::jmin (20000.0, sampleRate * 0.45);

    std::array<double, numProbes> probeHz {};
    for (int k = 0; k < numProbes; ++k)
    {
        const auto t = (double) k / (double) (numProbes - 1);
        probeHz[(size_t) k] = loHz * std::pow (hiHz / loHz, t);
    }

    // ...then weight by BS.1770 K-weighting, because the thing being cancelled
    // is LOUDNESS, not broadband energy. Ears are far less sensitive to the sub
    // content the 110 Hz shelf moves than to the presence region, and a flat
    // energy weighting over-compensates for the low bands accordingly. K-weighting
    // is a +3.99 dB shelf at 1681 Hz over a 38 Hz / Q 0.5 high-pass.
    const auto kShelf = juce::dsp::IIR::Coefficients<float>::makeHighShelf (
        sampleRate, 1681.0f, 0.7071f, juce::Decibels::decibelsToGain (3.99f));
    const auto kHighPass = juce::dsp::IIR::Coefficients<float>::makeHighPass (
        sampleRate, 38.0f, 0.5f);

    std::array<double, numProbes> weight {};
    double weightSum = 0.0;

    for (int k = 0; k < numProbes; ++k)
    {
        const auto f = probeHz[(size_t) k];
        const auto k1 = kShelf->getMagnitudeForFrequency (f, sampleRate);
        const auto k2 = kHighPass->getMagnitudeForFrequency (f, sampleRate);

        weight[(size_t) k] = k1 * k1 * k2 * k2;
        weightSum += weight[(size_t) k];
    }

    std::array<double, numProbes> magnitude {};

    // Two passes: one table per scale. 2x changes the curve, so it needs its own
    // compensation -- reusing the 1x table would leave it several dB out.
    for (int pass = 0; pass < 2; ++pass)
    {
        const auto scale = pass == 0 ? 1.0f : extremeScale;
        auto& table = pass == 0 ? out1x : out2x;

        for (int i = 0; i < compTableSize; ++i)
        {
            const auto d = (float) i / 100.0f - 1.0f;

            magnitude.fill (1.0);

            // One coefficient object per band (these allocate -- fine, we are not
            // on the audio thread), then evaluate every probe against it.
            for (const auto& band : bands)     // the PROFILE's bands, not the factory's
            {
                const auto coeffs = makeCoefficientsPtr (band, d, sampleRate, scale);

                for (int k = 0; k < numProbes; ++k)
                    magnitude[(size_t) k] *= coeffs->getMagnitudeForFrequency (
                        probeHz[(size_t) k], sampleRate);
            }

            double power = 0.0;
            for (int k = 0; k < numProbes; ++k)
                power += weight[(size_t) k] * magnitude[(size_t) k] * magnitude[(size_t) k];

            power /= juce::jmax (1.0e-12, weightSum);

            table[(size_t) i] = (float) (-10.0 * std::log10 (juce::jmax (1.0e-12, power)));
        }
    }
}

float ShipStudiosGainProcessor::compensationDbFor (const CurveProfile& profile,
                                                   float d, float scale) const noexcept
{
    const auto x = juce::jlimit (0.0f, (float) (compTableSize - 1), (d + 1.0f) * 100.0f);
    const auto i = (size_t) x;
    const auto j = juce::jmin (i + 1, (size_t) (compTableSize - 1));
    const auto frac = x - (float) i;

    const auto normal  = profile.comp[i]        + frac * (profile.comp[j]        - profile.comp[i]);
    const auto extreme = profile.compExtreme[i] + frac * (profile.compExtreme[j] - profile.compExtreme[i]);

    // scale ramps through [1, 2] while the toggle smooths.
    const auto blend = juce::jlimit (0.0f, 1.0f, (scale - 1.0f) / (extremeScale - 1.0f));

    return normal + blend * (extreme - normal);
}

//==============================================================================
// Message-thread only: snapshot of every OTHER linked instance. Empty unless
// this instance is itself linked -- an unlinked instance never drives peers.
juce::Array<ShipStudiosGainProcessor*> ShipStudiosGainProcessor::linkedPeers() const
{
    juce::Array<ShipStudiosGainProcessor*> peers;

    if (! linkEnabled.load())
        return peers;

    const juce::ScopedLock sl (linkRegistryLock);

    for (auto* p : linkRegistry)
        if (p != this && p->linkEnabled.load())
            peers.add (p);

    return peers;
}

//==============================================================================
void ShipStudiosGainProcessor::autoGainStart()
{
    // The TRIGGER propagates across the group; the measurement does not. Each
    // linked instance scans ITS OWN audio and lands on its own gain staging --
    // arming five drum mics with one click is the point, forcing the snare's
    // gain onto the overheads would not be.
    autoGainStartLocal();

    for (auto* peer : linkedPeers())
        peer->autoGainStartLocal();
}

void ShipStudiosGainProcessor::autoGainStartLocal()
{
    // Order matters: raise the reset flag BEFORE the learning flag, so the
    // audio thread cannot observe learning without also observing the reset.
    autoGainResetPending.store (true);
    autoGainSumSquaresPub.store (0.0);
    autoGainSamplesPub.store (0);
    autoGainPeakPub.store (0.0f);
    autoGainProgressPub.store (0.0f);
    autoGainLearning.store (true);
}

void ShipStudiosGainProcessor::autoGainFinishEarly()
{
    // Same shape as the start: ending the scan on one linked instance ends it
    // on all of them, each applying its own measurement.
    autoGainFinishEarlyLocal();

    for (auto* peer : linkedPeers())
        peer->autoGainFinishEarlyLocal();
}

void ShipStudiosGainProcessor::autoGainFinishEarlyLocal()
{
    bool expected = true;
    if (autoGainLearning.compare_exchange_strong (expected, false))
        computeAndApplyAutoGain();

    autoGainProgressPub.store (0.0f);
}

void ShipStudiosGainProcessor::requestAnalysisGroup()
{
    // Editor entry point: ANALYSE on one linked instance fires it on all,
    // each capturing and adapting to ITS OWN source (with its own Gemini
    // opt-in). Kept separate from requestAnalysis() because that one is also
    // the audio-thread trigger path (the analyse parameter), and the registry
    // lock has no business on the audio thread.
    requestAnalysis();

    for (auto* peer : linkedPeers())
        peer->requestAnalysis();
}

void ShipStudiosGainProcessor::handleAsyncUpdate()
{
    // One AsyncUpdater, two producers -- each leaves its own pending marker,
    // because a trigger for one must not run the other. (A spurious
    // computeAndApplyAutoGain here would RE-apply a stale learn result on top
    // of faders the user has since moved by hand.)
    if (autoGainApplyPending.exchange (false))
    {
        computeAndApplyAutoGain();
        autoGainProgressPub.store (0.0f);
    }

    broadcastLinkChanges();
}

//==============================================================================
void ShipStudiosGainProcessor::setLinkEnabled (bool shouldLink)
{
    linkEnabled.store (shouldLink);

    // Stored as panel state, not a parameter: whether an instance belongs to
    // the group is session plumbing, not a sound control to automate.
    apvts.state.setProperty ("linkGroup", shouldLink, nullptr);
}

void ShipStudiosGainProcessor::parameterChanged (const juce::String& parameterID, float)
{
    // May fire on ANY thread -- host automation lands here from the audio
    // thread -- so no parameter writes and no locks: set a dirty bit,
    // coalesce onto the message thread, done.
    if (! linkEnabled.load (std::memory_order_relaxed)
        || applyingRemoteLink.load (std::memory_order_relaxed))
        return;

    for (size_t i = 0; i < linkSyncedParams.size(); ++i)
    {
        if (parameterID == linkSyncedParams[i])
        {
            linkDirtyMask.fetch_or (1u << i);
            triggerAsyncUpdate();
            break;
        }
    }
}

void ShipStudiosGainProcessor::broadcastLinkChanges()
{
    const auto mask = linkDirtyMask.exchange (0);

    if (mask == 0 || ! linkEnabled.load())
        return;

    // Snapshot the linked peers under the lock, apply outside it. Message
    // thread only, same thread instances unregister on -- a snapshotted
    // pointer cannot die mid-loop.
    juce::Array<ShipStudiosGainProcessor*> peers;
    {
        const juce::ScopedLock sl (linkRegistryLock);

        for (auto* p : linkRegistry)
            if (p != this && p->linkEnabled.load())
                peers.add (p);
    }

    if (peers.isEmpty())
        return;

    // Values are read NOW, not at flag time: dirty bits coalesce, and the
    // latest value is by definition the one every peer should end up on.
    for (size_t i = 0; i < linkSyncedParams.size(); ++i)
    {
        if ((mask & (1u << i)) == 0)
            continue;

        if (auto* param = apvts.getParameter (linkSyncedParams[i]))
        {
            const auto value = param->getValue();

            for (auto* peer : peers)
                peer->applyRemoteLink (linkSyncedParams[i], value);
        }
    }
}

void ShipStudiosGainProcessor::applyRemoteLink (const char* paramID, float normalisedValue)
{
    auto* param = apvts.getParameter (paramID);

    // The already-there check is the second half of loop-safety: a peer at
    // the target value never even sees a change, so nothing can ping-pong.
    if (param == nullptr || juce::approximatelyEqual (param->getValue(), normalisedValue))
        return;

    applyingRemoteLink.store (true);
    param->setValueNotifyingHost (normalisedValue);
    applyingRemoteLink.store (false);
}

void ShipStudiosGainProcessor::processAutoGainLearn (const juce::AudioBuffer<float>& buffer,
                                                     int numChannels, int numSamples,
                                                     float blockPeak) noexcept
{
    if (autoGainResetPending.exchange (false))
    {
        autoGainSumSquares = 0.0;
        autoGainSamples = 0;
        autoGainPeak = 0.0f;
        autoGainWasPlaying = false;

        for (auto& f : kWeightShelf)    f.reset();
        for (auto& f : kWeightHighPass) f.reset();
    }

    // Peak is tracked UNGATED: one transient in an otherwise quiet learn
    // window must still cap the recommendation.
    autoGainPeak = juce::jmax (autoGainPeak, blockPeak);

    // The loudness accumulator IS gated: arming AUTO before pressing play must
    // not average the pre-roll silence into the measurement. A -60 dBFS block
    // gate stands in for BS.1770's two-stage gating -- on real programme the
    // difference is a fraction of a dB, and the full gating machinery would be
    // the largest piece of code in the feature.
    if (blockPeak > juce::Decibels::decibelsToGain (autoGainGateDb))
    {
        const auto usedChannels = juce::jmin (numChannels, 2);

        for (int ch = 0; ch < usedChannels; ++ch)
        {
            const auto* data = buffer.getReadPointer (ch);
            auto& shelf = kWeightShelf[ch];
            auto& hp    = kWeightHighPass[ch];

            auto sum = 0.0;
            for (int n = 0; n < numSamples; ++n)
            {
                const auto w = hp.processSample (shelf.processSample (data[n]));
                sum += (double) w * (double) w;
            }

            autoGainSumSquares += sum;
        }

        // BS.1770 SUMS channel powers (each side weighted 1.0), so the count
        // advances once per FRAME, not once per channel-sample.
        autoGainSamples += numSamples;
    }

    autoGainSumSquaresPub.store (autoGainSumSquares, std::memory_order_relaxed);
    autoGainSamplesPub.store (autoGainSamples, std::memory_order_relaxed);
    autoGainPeakPub.store (autoGainPeak, std::memory_order_relaxed);
    autoGainProgressPub.store ((float) ((double) autoGainSamples / currentSampleRate));

    // The scan is OPEN-ENDED -- it covers however much of the region is
    // played. One ending lives here: the host transport STOPPING after enough
    // signal, so "arm, play the region, stop" applies without a second click.
    // Hosts that report no transport (standalone) never trip this; the second
    // click is their only ending. The play->stop edge is required -- merely
    // being stopped is not enough, or arming while parked would apply
    // instantly off whatever the peak meter last saw.
    bool haveTransport = false;
    bool playing = false;

    if (auto* playHead = getPlayHead())
        if (const auto position = playHead->getPosition())
        {
            haveTransport = true;
            playing = position->getIsPlaying();
        }

    if (haveTransport)
    {
        const bool stoppedEdge = autoGainWasPlaying && ! playing;
        autoGainWasPlaying = playing;

        if (stoppedEdge
            && (double) autoGainSamples >= autoGainMinSeconds * currentSampleRate)
        {
            // The exchange decides ownership: if the user's early click won
            // the race, the result is already applied and this stands down.
            bool expected = true;
            if (autoGainLearning.compare_exchange_strong (expected, false))
            {
                autoGainApplyPending.store (true);
                triggerAsyncUpdate();
            }
        }
    }
}

void ShipStudiosGainProcessor::computeAndApplyAutoGain()
{
    const auto samples = autoGainSamplesPub.load();

    // Too little signal to trust -- e.g. AUTO clicked twice in silence.
    // Leaving the parameter alone beats confidently applying a gain that was
    // measured on nothing.
    if ((double) samples < autoGainMinSeconds * currentSampleRate)
        return;

    const auto meanSquare = autoGainSumSquaresPub.load() / (double) samples;
    if (meanSquare <= 1.0e-12)
        return;

    // -0.691 is BS.1770's own calibration constant, kept so the target reads
    // in actual LUFS rather than a private unit 0.7 dB away from one.
    const auto lufs = -0.691 + 10.0 * std::log10 (meanSquare);
    const auto peakDb = juce::Decibels::gainToDecibels (autoGainPeakPub.load(), -100.0f);

    // Whichever constraint asks for LESS gain wins: loud enough to drive the
    // calibrated dynamics, never so hot that raw peaks eat the pre-EQ headroom.
    const auto gainDb = juce::jlimit (-24.0f, 24.0f,
                                      juce::jmin ((float) (autoGainTargetLufs - lufs),
                                                  autoGainMaxPeakDb - peakDb));

    // OUTPUT mirrors the input move so the track's level in the mix stays
    // where it was -- the chain gets driven correctly, the balance does not
    // jump. Clamped to output's own +/-12 range: a source needing more than
    // 12 dB of input correction keeps a residual level change, which is
    // honest -- output trim is a trim, not a second gain stage.
    const auto outputDb = juce::jlimit (-12.0f, 12.0f, -gainDb);

    const auto applyGestured = [this] (const char* id, float value)
    {
        if (auto* param = apvts.getParameter (id))
        {
            // Gestured like a real fader move, so host automation records it
            // the same way it would a manual adjustment.
            param->beginChangeGesture();
            param->setValueNotifyingHost (param->convertTo0to1 (value));
            param->endChangeGesture();
        }
    };

    // Exempt from link mirroring: when a grouped scan finishes, every linked
    // instance applies its OWN measurement. Without this, each apply would
    // broadcast to the group and whichever instance applied last would stamp
    // its numbers onto all of them -- exactly the wrong outcome.
    applyingRemoteLink.store (true);
    applyGestured (inputParamID,  gainDb);
    applyGestured (outputParamID, outputDb);
    applyingRemoteLink.store (false);
}

//==============================================================================
void ShipStudiosGainProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                             juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;

    const auto numIn  = getTotalNumInputChannels();
    const auto numOut = getTotalNumOutputChannels();
    const auto numSamples = buffer.getNumSamples();

    // A host may hand us more outputs than inputs; anything we don't write is
    // stale memory, so clear it.
    for (auto ch = numIn; ch < numOut; ++ch)
        buffer.clear (ch, 0, numSamples);

    if (numIn <= 0 || numSamples <= 0)
        return;

    // Capture BEFORE the input gain and before the EQ, so the analysis measures
    // the raw source. Capturing downstream would measure the curve this plugin
    // just imposed and walk the bands further out on every press.
    if (captureState.load (std::memory_order_acquire) == CaptureState::capturing)
    {
        const auto cap = captureCapacity.load (std::memory_order_relaxed);
        auto pos = captureWritePos.load (std::memory_order_relaxed);
        const auto n = juce::jmin (numSamples, cap - pos);

        if (n > 0)
        {
            auto* dst = captureBuffer.getWritePointer (0) + pos;

            if (numIn > 1)
            {
                juce::FloatVectorOperations::copyWithMultiply (dst, buffer.getReadPointer (0), 0.5f, n);
                juce::FloatVectorOperations::addWithMultiply  (dst, buffer.getReadPointer (1), 0.5f, n);
            }
            else
            {
                juce::FloatVectorOperations::copy (dst, buffer.getReadPointer (0), n);
            }

            auto pk = capturePeak.load (std::memory_order_relaxed);
            for (int i = 0; i < n; ++i) pk = juce::jmax (pk, std::abs (dst[i]));
            capturePeak.store (pk, std::memory_order_relaxed);

            pos += n;
            captureWritePos.store (pos, std::memory_order_release);
            captureProgress.store (pos, std::memory_order_relaxed);
        }

        if (pos >= cap)
            captureState.store (CaptureState::full, std::memory_order_release);
    }

    // Input meter reads the RAW signal, before the input gain -- a true input
    // meter. How hard the processing is being driven is the CLIP meter's job.
    auto inputPeak = 0.0f;
    for (int ch = 0; ch < numIn; ++ch)
        inputPeak = juce::jmax (inputPeak, buffer.getMagnitude (ch, 0, numSamples));

    displayInputLevelDb.store (juce::Decibels::gainToDecibels (inputPeak, -100.0f));

    // Auto-gain learn taps the signal HERE -- raw, before the input gain -- so
    // it measures the SOURCE. Post-gain it would chase its own correction.
    if (autoGainLearning.load (std::memory_order_relaxed))
        processAutoGainLearn (buffer, numIn, numSamples, inputPeak);

    // Bypass rides the smoothers back to flat/unity rather than hard-switching,
    // so engaging it does not click. There is deliberately NO early-out for the
    // flat case: an early return here would silently skip the EQ.
    // One acquire per block: coefficients AND compensation then come from the
    // same profile, so a torn "new bands with old compensation" is impossible.
    const int published = activeProfile.load (std::memory_order_acquire);

    // Rising edge on the analyse parameter arms a capture. Reading it here means
    // the harness can trigger analysis by setting a parameter.
    {
        const bool now = analyseParam->load() > 0.5f;
        if (now && ! lastAnalyseTrigger)
            requestAnalysis();
        lastAnalyseTrigger = now;
    }

    if (auto* trig = apvts.getRawParameterValue (assistParamID))
    {
        const bool now = trig->load() > 0.5f;
        if (now && ! lastAssistTrigger)
            requestAssist();
        lastAssistTrigger = now;
    }

    const bool bypassed = bypassParam->get();
    const auto targetDistance = bypassed ? 0.0f : normaliseDistance (distanceParam->load());
    const auto outputDb = bypassed ? 0.0f : outputDbParam->load();

    distanceSmoothed.setTargetValue (targetDistance);
    scaleSmoothed.setTargetValue (
        (! bypassed && extremeParam->get()) ? extremeScale : 1.0f);
    ceilingSmoothed.setTargetValue (ceilingParam->load());

    // Meter accumulators for this block; the stage functions jmax into them
    // per chunk and the atomics are stored ONCE at the end. A block where a
    // stage never ran (bypass, flat skip) therefore reads as inactive instead
    // of freezing at its last live value.
    blockCompGrMax = 0.0f;
    blockCompLevelMax = -100.0f;
    blockClipGrMax = 0.0f;

    // "Flat" means settled at exactly the centre. Only once that has held for a
    // few blocks -- long enough for the filters' state to decay -- is it safe to
    // drop them from the chain entirely.
    const bool atCentre = ! distanceSmoothed.isSmoothing()
                       && juce::exactlyEqual (distanceSmoothed.getCurrentValue(), 0.0f);

    flatBlocks = atCentre ? juce::jmin (flatBlocks + 1, flatBlocksBeforeSkip) : 0;
    const bool skipFilters = flatBlocks >= flatBlocksBeforeSkip;

    // Adopt a newly published profile. At centre the curve is already unity, so
    // there is nothing to fade and the swap is free.
    if (published != appliedSlot && swapPhase == SwapPhase::none)
    {
        if (skipFilters)
            appliedSlot = published;
        else
        {
            swapPhase = SwapPhase::fadingOut;
            swapFade.setTargetValue (0.0f);
        }
    }

    // Bound AFTER the adopt above, and RE-POINTED the moment the swap adopts
    // mid-block. A once-per-block reference ran the fade-in tail on the OLD
    // bands and compensation -- at large host buffers (a 4096-sample offline
    // bounce holds two whole 40 ms fades) the ENTIRE fade-in ran on the old
    // curve and the new bands then stepped in at full depth a block late,
    // which is exactly the click this machinery exists to prevent.
    const CurveProfile* profile = &profileSlots[(size_t) appliedSlot];

    juce::dsp::AudioBlock<float> block (buffer.getArrayOfWritePointers(),
                                        (size_t) numIn,
                                        (size_t) numSamples);

    // Input gain first, so everything downstream -- including the compressor's
    // fixed dBFS thresholds -- sees the driven signal. At 0 dB this multiplies
    // by exactly 1.0f, so it costs the centre position nothing.
    inputGainSmoothed.setTargetValue (
        bypassed ? 1.0f : juce::Decibels::decibelsToGain (inputDbParam->load()));
    block.multiplyBy (inputGainSmoothed);

    for (int pos = 0; pos < numSamples; pos += updateChunkSamples)
    {
        const auto chunk = juce::jmin (updateChunkSamples, numSamples - pos);

        // Step the curve once per chunk. Smoothing the PARAMETER and re-deriving
        // coefficients is the right lever -- juce_dsp has no coefficient smoother.
        const auto d = distanceSmoothed.skip (chunk);
        const auto scale = scaleSmoothed.skip (chunk);
        const auto ceilingDb = ceilingSmoothed.skip (chunk);

        // The EQ (and only the EQ) sees `d` scaled by the swap fade.
        const auto fade = swapFade.skip (chunk);
        const auto dEq = d * fade;

        if (swapPhase == SwapPhase::fadingOut && ! swapFade.isSmoothing())
        {
            appliedSlot = published;             // unity curve -> adopt here
            profile = &profileSlots[(size_t) appliedSlot];
            swapPhase = SwapPhase::fadingIn;
            swapFade.setTargetValue (1.0f);
        }
        else if (swapPhase == SwapPhase::fadingIn && ! swapFade.isSmoothing())
        {
            swapPhase = SwapPhase::none;
        }

        auto sub = block.getSubBlock ((size_t) pos, (size_t) chunk);

        auto makeupDb = 0.0f;

        if (! skipFilters)
        {
            // The generation term is load-bearing: without it a profile swap
            // never reaches the filters when the fader is not moving.
            if (! juce::exactlyEqual (dEq, lastAppliedDistance)
                || ! juce::exactlyEqual (scale, lastAppliedScale)
                || profile->generation != lastAppliedGeneration)
            {
                updateCoefficients (*profile, dEq, scale);
                lastAppliedDistance = dEq;
                lastAppliedScale = scale;
                lastAppliedGeneration = profile->generation;
            }

            juce::dsp::ProcessContextReplacing<float> context (sub);
            eqChain.process (context);

            // Compressor AFTER the EQ, so its detector hears the tone the
            // "room" already imposed rather than the raw source.
            makeupDb = processCompressor (sub, d, scale);

            // Transient shaper after the compressor, so it has the final say on
            // the envelope -- otherwise the compressor's own ballistics would
            // partly undo the shaping downstream of it.
            processTransient (sub, d, scale);
        }
        else
        {
            // Reset EVERY detector/envelope, not just the compressor's gain:
            // re-engaging after a long flat stretch must start from silence,
            // not from whatever the followers held when the fader last left
            // centre -- stale envelopes made the first shaped samples jump.
            gainReductionDb = 0.0f;
            averageGainReductionDb = 0.0f;
            envFastDb = envSlowDb = envLongDb = -100.0f;
            transAverageGainDb = 0.0f;
            compDetectorPeak = 0.0f;
        }

        // compensation cancels the EQ's incidental loudness change; the
        // distance law then applies the intended one on top of a level playing
        // field. Order matters conceptually even though they just add here.
        gainSmoothed.setTargetValue (
            juce::Decibels::decibelsToGain (compensationDbFor (*profile, dEq, scale)
                                                + distanceLevelDb (d, scale)
                                                + makeupDb
                                                + outputDb));
        sub.multiplyBy (gainSmoothed);

        // After the gain, so the shaper sees the level the distance law actually
        // produced -- and inside the loop, so it tracks the same smoothed d as
        // the EQ and compressor rather than stepping once per block.
        if (! bypassed)
            processClip (sub, d, scale, ceilingDb);
        else
            clipStateValid = false;   // ADAA must reseed after a bypass gap
    }

    // The limiter still guarantees the ceiling. With the clipper shaving close
    // settings, it has far less to do there, so what survives is punch rather
    // than gain reduction.
    processLimiter (buffer, bypassed, ceilingSmoothed.getCurrentValue());

    displayGainReductionDb.store (blockCompGrMax);
    displayCompLevelDb.store (blockCompLevelMax);
    displayClipGrDb.store (blockClipGrMax);

    auto outputPeak = 0.0f;
    for (int ch = 0; ch < numIn; ++ch)
        outputPeak = juce::jmax (outputPeak, buffer.getMagnitude (ch, 0, numSamples));

    displayOutputLevelDb.store (juce::Decibels::gainToDecibels (outputPeak, -100.0f));
}

//==============================================================================
void ShipStudiosGainProcessor::processTransient (juce::dsp::AudioBlock<float>& block,
                                                 float d,
                                                 float scale) noexcept
{
    const auto spec = transientFor (d, scale);

    if (std::abs (spec.attackDb) < 1.0e-4f && std::abs (spec.sustainDb) < 1.0e-4f)
        return;   // exactly transparent at centre

    const auto numChannels = juce::jmin (block.getNumChannels(), (size_t) 2);
    const auto numSamples = block.getNumSamples();

    float* channels[2] {};
    for (size_t ch = 0; ch < numChannels; ++ch)
        channels[ch] = block.getChannelPointer (ch);

    for (size_t n = 0; n < numSamples; ++n)
    {
        auto peak = 0.0f;
        for (size_t ch = 0; ch < numChannels; ++ch)
            peak = juce::jmax (peak, std::abs (channels[ch][n]));

        // Deliberately NO peak hold here, unlike the compressor. The shaper
        // lives off the CONTRAST between followers, and a pre-detector hold
        // flattens exactly that: measured, it cost ~half the onset/body
        // separation on percussive material (4.5 -> 2.3 dB) for a second-order
        // tonal win the compressor's hold had already banked. The shaper's own
        // cycle-tracking is tanh-bounded and mean-subtracted, so its residue
        // is far smaller than the compressor's was.
        const auto levelDb = juce::Decibels::gainToDecibels (peak, -100.0f);

        const auto follow = [levelDb] (float& env, float attackCoeff, float releaseCoeff)
        {
            env += (levelDb - env) * (levelDb > env ? attackCoeff : releaseCoeff);
        };

        follow (envFastDb, transAttackFastCoeff, transReleaseCoeff);
        follow (envSlowDb, transAttackSlowCoeff, transReleaseCoeff);
        follow (envLongDb, transAttackFastCoeff, transReleaseLongCoeff);

        // Onset: the fast follower outruns the slow one only while level is
        // rising. Sustain: the long follower lags the fast one only while it is
        // falling. Both collapse to zero in steady state, which is what makes
        // this level-independent rather than threshold-based.
        const auto onset = juce::jmax (0.0f, envFastDb - envSlowDb);
        const auto tail  = juce::jmax (0.0f, envLongDb - envFastDb);

        const auto rawGainDb = spec.attackDb  * std::tanh (onset / transientKneeDb)
                             + spec.sustainDb * std::tanh (tail  / transientKneeDb);

        // Subtract the slow mean so the shaper is loudness-neutral by
        // construction: the fast contrast between onset and tail survives, the
        // sustained bias that would fight the distance level law does not.
        transAverageGainDb += (rawGainDb - transAverageGainDb) * transAverageCoeff;
        const auto gain = juce::Decibels::decibelsToGain (rawGainDb - transAverageGainDb);

        for (size_t ch = 0; ch < numChannels; ++ch)
            channels[ch][n] *= gain;
    }
}

//==============================================================================
namespace
{
    // The clip transfer is f(x) = sign(x) * shaped(|x|), with
    //
    //   shaped(a) = a                                  for a <= t
    //   shaped(a) = t + s * tanh((a - t) / s)  (soft)  for a >  t
    //   shaped(a) = t                          (hard)
    //
    // SOFT: tanh over the region above the knee. Two properties make it the
    // right curve -- tanh'(0) == 1, so value AND slope are continuous at the
    // knee (no kink to buzz on), and tanh < 1 always, so the steady-state
    // output is strictly bounded by the ceiling and can never fold back the
    // way a naive polynomial shaper does.
    //
    // HARD: flat-top at the threshold. The slope discontinuity is the point --
    // a corner generates far more high-order harmonics than a curve, which is
    // exactly the difference between the two modes. Peaks land lower than
    // soft, which asymptotes up toward the ceiling; that is hard clipping
    // being the more aggressive peak control, not a level bug.
    //
    // ANTI-ALIASING. Run naively per sample, both shapes generate harmonics
    // past Nyquist that fold back as inharmonic junk (measured: the worst
    // aliased peak sat only ~24 dB under the fundamental on a driven 2 kHz
    // tone in hard mode). First-order ADAA fixes that: output the average of
    // f over the interval the signal traversed since the last sample --
    // (F(x[n]) - F(x[n-1])) / (x[n] - x[n-1]) with F the antiderivative --
    // which band-limits the nonlinearity analytically, no oversampling, no
    // added latency.
    //
    // The twist here: ADAA is applied to the CORRECTION c(x) = f(x) - x, not
    // to f itself. Plain ADAA has an inherent half-sample lowpass (below the
    // knee it returns (x[n] + x[n-1]) / 2 -- about -2 dB at 10 kHz), which
    // would darken everything the moment the stage engages. The correction is
    // identically ZERO below the knee, so y = x + ADAA(c) keeps the
    // sub-threshold path bit-exact and applies the smoothing only to the
    // alias-generating part.

    // c(x): the raw correction, for the ill-conditioned dx ~ 0 fallback.
    inline float clipCorrection (float x, float threshold, float span, bool hard) noexcept
    {
        const auto a = std::abs (x);

        if (a <= threshold)
            return 0.0f;

        const auto shaped = hard ? threshold
                                 : threshold + span * std::tanh ((a - threshold) / span);
        const auto corr = shaped - a;   // <= 0 by construction

        return x < 0.0f ? -corr : corr;
    }

    // Antiderivative of c. Even in x (c is odd). Computed in DOUBLE: the ADAA
    // divided difference cancels catastrophically in float when successive
    // samples are close together.
    //
    // For a = |x| > t, with e = a - t:
    //   soft: C = t*e + s^2 * ln cosh(e/s) + (t^2 - a^2) / 2
    //   hard: C = -e^2 / 2
    // and C = 0 below the knee.
    inline double clipCorrectionIntegral (double x, double threshold,
                                          double span, bool hard) noexcept
    {
        const auto a = std::abs (x);

        if (a <= threshold)
            return 0.0;

        const auto e = a - threshold;

        if (hard)
            return -0.5 * e * e;

        const auto u = e / span;

        // ln cosh(u), stable for large u: u + ln(1 + e^(-2u)) - ln 2.
        const auto logCosh = u + std::log1p (std::exp (-2.0 * u))
                           - 0.6931471805599453;

        return threshold * e + span * span * logCosh
             + 0.5 * (threshold * threshold - a * a);
    }
} // namespace

void ShipStudiosGainProcessor::processClip (juce::dsp::AudioBlock<float>& block,
                                            float d,
                                            float scale,
                                            float ceilingDb) noexcept
{
    const auto amount = distanceSoftClipAmount (d, scale);

    // Exactly zero means exactly transparent -- no waveshaping at all, not a
    // shaper configured to do nothing. True at centre and everywhere far.
    if (amount <= 1.0e-4f)
    {
        clipStateValid = false;
        return;
    }

    const auto ceilingLinear = juce::Decibels::decibelsToGain (ceilingDb);
    const auto threshold = ceilingLinear
                         * juce::Decibels::decibelsToGain (-amount * softClipRangeDb);
    const auto span = ceilingLinear - threshold;

    if (span <= 1.0e-9f)
    {
        clipStateValid = false;
        return;
    }

    const auto numChannels = juce::jmin (block.getNumChannels(), (size_t) 2);
    const auto numSamples = block.getNumSamples();

    if (! clipStateValid)
    {
        // Re-engaging: seed the ADAA memory from the first sample so the
        // divided difference never spans a disengaged gap. That first sample
        // then takes the dx ~ 0 fallback, i.e. plain f(x).
        for (size_t ch = 0; ch < numChannels; ++ch)
            clipPrevX[ch] = block.getChannelPointer (ch)[0];

        clipStateValid = true;
    }

    // Both modes share the SAME fader-derived threshold, so switching changes
    // the shape of the nonlinearity and nothing else. Sub-threshold audio is
    // untouched either way, which is what keeps the two comparable by ear --
    // only the peak treatment and the harmonic signature differ.
    const bool hard = hardClipParam->get();

    auto peakReduction = 0.0f;

    for (size_t ch = 0; ch < numChannels; ++ch)
    {
        auto* data = block.getChannelPointer (ch);
        auto prev = clipPrevX[ch];

        for (size_t n = 0; n < numSamples; ++n)
        {
            const auto x = data[n];
            float y;

            if (juce::jmax (std::abs (x), std::abs (prev)) <= threshold)
            {
                y = x;   // both samples in the linear region: bit-exact
            }
            else
            {
                const auto dx = (double) x - (double) prev;

                if (std::abs (dx) > 1.0e-6)
                    y = x + (float) ((clipCorrectionIntegral (x,    threshold, span, hard)
                                    - clipCorrectionIntegral (prev, threshold, span, hard))
                                     / dx);
                else
                    y = x + clipCorrection (0.5f * (x + prev), threshold, span, hard);
            }

            prev = x;

            const auto magnitude = std::abs (x);

            if (magnitude > threshold)
                peakReduction = juce::jmax (
                    peakReduction,
                    juce::Decibels::gainToDecibels (magnitude)
                        - juce::Decibels::gainToDecibels (
                              juce::jmax (std::abs (y), 1.0e-9f)));

            data[n] = y;
        }

        clipPrevX[ch] = prev;
    }

    blockClipGrMax = juce::jmax (blockClipGrMax, peakReduction);
}

//==============================================================================
void ShipStudiosGainProcessor::processLimiter (juce::AudioBuffer<float>& buffer,
                                               bool bypassed,
                                               float ceilingDb) noexcept
{
    const auto numChannels = juce::jmin (buffer.getNumChannels(), limiterDelay.getNumChannels());
    const auto numSamples = buffer.getNumSamples();
    const auto ceilingLinear = juce::Decibels::decibelsToGain (ceilingDb);
    const auto invWindow = 1.0 / (double) lookaheadSamples;

    auto peakReduction = 0.0f;

    for (int n = 0; n < numSamples; ++n)
    {
        // The control is read from the sample ENTERING the delay line -- i.e.
        // one lookahead ahead of the sample leaving it. That head start is the
        // whole trick.
        auto peak = 0.0f;
        for (int ch = 0; ch < numChannels; ++ch)
            peak = juce::jmax (peak, std::abs (buffer.getReadPointer (ch)[n]));

        const auto required = (! bypassed && peak > ceilingLinear)
                                  ? juce::Decibels::gainToDecibels (peak) - ceilingDb
                                  : 0.0f;

        // Hold the requirement across the whole lookahead window: the sample
        // leaving the delay line entered one window ago, so its own requirement
        // must still be represented in the target.
        limiterBlockMax = juce::jmax (limiterBlockMax, required);

        if (++limiterBlockCounter >= lookaheadSamples)
        {
            limiterPrevBlockMax = limiterBlockMax;
            limiterBlockMax = 0.0f;
            limiterBlockCounter = 0;
        }

        const auto target = juce::jmax (limiterBlockMax, limiterPrevBlockMax);

        // Instant attack, exponential release. The follower itself may step --
        // the boxcar below is what turns that step into a ramp.
        if (target > limiterGrDb)
            limiterGrDb = target;
        else
            limiterGrDb += (target - limiterGrDb) * limiterReleaseCoeff;

        // Boxcar moving average over exactly the lookahead window (the ring
        // shares limiterWritePos with the delay -- same length, same phase).
        // Every term averaged when a sample exits is >= that sample's own
        // requirement, so the ceiling holds; and a step becomes a linear ramp
        // finishing exactly when the peak arrives, so the attack has no
        // corners to intermodulate low frequencies.
        limiterSmoothSum += (double) limiterGrDb
                          - (double) limiterSmoothBuf[(size_t) limiterWritePos];
        limiterSmoothBuf[(size_t) limiterWritePos] = limiterGrDb;

        const auto smoothedGrDb = juce::jmax (0.0f, (float) (limiterSmoothSum * invWindow));
        const auto gain = juce::Decibels::decibelsToGain (-smoothedGrDb);

        for (int ch = 0; ch < numChannels; ++ch)
        {
            auto* delayed = limiterDelay.getWritePointer (ch);
            auto* audio = buffer.getWritePointer (ch);

            const auto out = delayed[limiterWritePos];
            delayed[limiterWritePos] = audio[n];
            audio[n] = out * gain;
        }

        if (++limiterWritePos >= lookaheadSamples)
            limiterWritePos = 0;

        peakReduction = juce::jmax (peakReduction, smoothedGrDb);
    }

    displayLimiterGrDb.store (peakReduction);
}

//==============================================================================
float ShipStudiosGainProcessor::processCompressor (juce::dsp::AudioBlock<float>& block,
                                                   float d,
                                                   float scale) noexcept
{
    // Settings and ballistics coefficients only change when the fader (or 2x)
    // moves; cache them against (d, scale) instead of paying three std::exp
    // per chunk forever.
    if (! juce::exactlyEqual (d, compCachedD)
        || ! juce::exactlyEqual (scale, compCachedScale))
    {
        compSettings = compressorFor (d, scale);

        const auto sr = (float) currentSampleRate;
        compAttackCoeff  = 1.0f - std::exp (-1.0f / (0.001f * compSettings.attackMs  * sr));
        compReleaseCoeff = 1.0f - std::exp (-1.0f / (0.001f * compSettings.releaseMs * sr));

        compCachedD = d;
        compCachedScale = scale;
    }

    // Ratio 1.0 is mathematically inert; skip rather than burn cycles proving it.
    if (compSettings.ratio <= 1.0f + 1.0e-6f)
    {
        gainReductionDb = 0.0f;
        averageGainReductionDb = 0.0f;
        return 0.0f;
    }

    const auto numChannels = block.getNumChannels();
    const auto numSamples  = block.getNumSamples();

    float* channels[2] {};
    const auto usedChannels = juce::jmin (numChannels, (size_t) 2);

    for (size_t ch = 0; ch < usedChannels; ++ch)
        channels[ch] = block.getChannelPointer (ch);

    auto peakReduction = 0.0f;
    auto peakLevelDb = -100.0f;

    for (size_t n = 0; n < numSamples; ++n)
    {
        // Stereo-linked detector: one envelope for both sides.
        auto peak = 0.0f;
        for (size_t ch = 0; ch < usedChannels; ++ch)
            peak = juce::jmax (peak, std::abs (channels[ch][n]));

        // Peak hold before the dB conversion -- see the header. Without it the
        // far side's 0.3 ms attack rides individual cycles of low/mid tones
        // and distorts them; with it the detector reads the envelope.
        compDetectorPeak = juce::jmax (peak, compDetectorPeak * detectorHoldCoeff);

        const auto levelDb = juce::Decibels::gainToDecibels (compDetectorPeak, -120.0f);
        peakLevelDb = juce::jmax (peakLevelDb, levelDb);
        const auto target = compressorGainReductionDb (compSettings, levelDb);

        // Attack when clamping down, release when letting go -- this is where
        // the near/far character actually lives.
        const auto coeff = target > gainReductionDb ? compAttackCoeff : compReleaseCoeff;
        gainReductionDb += (target - gainReductionDb) * coeff;

        const auto gain = juce::Decibels::decibelsToGain (-gainReductionDb);

        for (size_t ch = 0; ch < usedChannels; ++ch)
            channels[ch][n] *= gain;

        averageGainReductionDb += (gainReductionDb - averageGainReductionDb) * compAverageCoeff;
        peakReduction = juce::jmax (peakReduction, gainReductionDb);
    }

    blockCompGrMax = juce::jmax (blockCompGrMax, peakReduction);
    blockCompLevelMax = juce::jmax (blockCompLevelMax, peakLevelDb);

    return averageGainReductionDb;
}

//==============================================================================
// Names describe the RESULT, not the settings -- the fader position is already
// on screen; what a preset adds is a starting point with an intent.
const std::array<ShipStudiosGainProcessor::FactoryPreset, 8>
    ShipStudiosGainProcessor::factoryPresets { {
        //  name                distance  2x     hard   in    out   ceiling
        { "Flat",                   0.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "A Step Back",          -35.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "Across the Room",      -70.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "Far Room",            -100.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "Another Building",    -100.0f, true,  false, 0.0f, 0.0f, -0.3f },
        { "Lean In",               40.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "Up Close",              80.0f, false, false, 0.0f, 0.0f, -0.3f },
        { "In Your Face",         100.0f, true,  true,  4.0f, 0.0f, -0.3f },
    } };

int ShipStudiosGainProcessor::getNumPrograms()
{
    return (int) factoryPresets.size();
}

const juce::String ShipStudiosGainProcessor::getProgramName (int index)
{
    if (juce::isPositiveAndBelow (index, (int) factoryPresets.size()))
        return factoryPresets[(size_t) index].name;

    return {};
}

void ShipStudiosGainProcessor::setParameterValue (const juce::String& id, float value)
{
    if (auto* param = apvts.getParameter (id))
        param->setValueNotifyingHost (param->convertTo0to1 (value));
}

bool ShipStudiosGainProcessor::matchesProgram (int index) const
{
    if (! juce::isPositiveAndBelow (index, (int) factoryPresets.size()))
        return false;

    const auto& preset = factoryPresets[(size_t) index];

    const auto same = [this] (const juce::String& id, float expected)
    {
        if (auto* raw = apvts.getRawParameterValue (id))
            return std::abs (raw->load() - expected) < 0.05f;

        return false;
    };

    return same (distanceParamID, preset.distance)
        && same (inputParamID,    preset.inputDb)
        && same (outputParamID,   preset.outputDb)
        && same (ceilingParamID,  preset.ceilingDb)
        && same (extremeParamID,  preset.extreme ? 1.0f : 0.0f)
        && same (hardClipParamID, preset.hardClip ? 1.0f : 0.0f);
}

void ShipStudiosGainProcessor::setCurrentProgram (int index)
{
    if (! juce::isPositiveAndBelow (index, (int) factoryPresets.size()))
        return;

    currentProgram = index;
    const auto& preset = factoryPresets[(size_t) index];

    setParameterValue (distanceParamID, preset.distance);
    setParameterValue (inputParamID,    preset.inputDb);
    setParameterValue (outputParamID,   preset.outputDb);
    setParameterValue (ceilingParamID,  preset.ceilingDb);
    setParameterValue (extremeParamID,  preset.extreme ? 1.0f : 0.0f);
    setParameterValue (hardClipParamID, preset.hardClip ? 1.0f : 0.0f);
}

//==============================================================================
void ShipStudiosGainProcessor::storeAbSlot (int slot)
{
    if (juce::isPositiveAndBelow (slot, 2))
        abSlots[slot] = apvts.copyState().createCopy();
}

void ShipStudiosGainProcessor::recallAbSlot (int slot)
{
    if (! (juce::isPositiveAndBelow (slot, 2) && abSlots[slot].isValid()))
        return;

    // A/B compares SOUND settings. The panel/session plumbing that rides in
    // the same tree (link membership, view mode) must NOT flip with a recall
    // -- and linkEnabled is cached in an atomic that replaceState knows
    // nothing about, so letting the property change would desync the two and
    // save the wrong membership with the session.
    const bool link = linkEnabled.load();
    const auto advanced = apvts.state.getProperty ("advancedView", false);

    apvts.replaceState (abSlots[slot].createCopy());

    apvts.state.setProperty ("linkGroup", link, nullptr);
    apvts.state.setProperty ("advancedView", advanced, nullptr);
}

bool ShipStudiosGainProcessor::hasAbSlot (int slot) const
{
    return juce::isPositiveAndBelow (slot, 2) && abSlots[slot].isValid();
}

namespace
{
    const char* materialName (ShipStudios::Material m) noexcept
    {
        switch (m)
        {
            case ShipStudios::Material::kick:      return "kick";
            case ShipStudios::Material::snare:     return "snare";
            case ShipStudios::Material::overheads: return "overheads";
            case ShipStudios::Material::drumKit:   return "drum kit";
            case ShipStudios::Material::vocal:   return "vocal";
            case ShipStudios::Material::fullMix: return "full mix";
            case ShipStudios::Material::bass:    return "bass";
            case ShipStudios::Material::other:   return "other";
            case ShipStudios::Material::unknown:
            default:                             return "unknown";
        }
    }
}

//==============================================================================
void ShipStudiosGainProcessor::publishProfile (const std::array<BandSpec, 4>& bands,
                                               double sampleRate)
{
    const juce::ScopedLock sl (publishLock);

    auto& dst = profileSlots[(size_t) nextWriteSlot];

    dst.bands = bands;
    dst.sampleRate = sampleRate;
    buildCompensationTables (dst.bands, sampleRate, dst.comp, dst.compExtreme);
    dst.generation = ++generationCounter;

    publishedGeneration.store (dst.generation, std::memory_order_relaxed);
    activeProfile.store (nextWriteSlot, std::memory_order_release);   // the flip

    nextWriteSlot = (nextWriteSlot + 1) % (int) profileSlots.size();
}

void ShipStudiosGainProcessor::requestAnalysis() noexcept
{
    // requestAssist() sets the intent and then calls through here, so only the
    // DIRECT caller resets it. Checked by the caller, not guessed at.
    if (! assistArming)
        captureIntent.store (CaptureIntent::adaptBands, std::memory_order_relaxed);

    // Refuse to re-arm while a run is in flight. The audio thread's lock-free
    // writes into captureBuffer are safe ONLY because of the state machine
    // (audio writes while `capturing`, the worker reads while `full`) -- and
    // re-arming mid-run flips full -> capturing while the worker may still be
    // copying, putting a writer under its read. The UI already greys the
    // control while busy; this closes the parameter-trigger path too.
    switch (analysisState.load())
    {
        case AnalysisState::capturing:
        case AnalysisState::analysing:
        case AnalysisState::classifying:
            return;

        case AnalysisState::idle:
        case AnalysisState::adapted:
        case AnalysisState::failed:
        default:
            break;
    }

    captureWritePos.store (0, std::memory_order_relaxed);
    captureProgress.store (0, std::memory_order_relaxed);
    capturePeak.store (0.0f, std::memory_order_relaxed);
    analysisState.store (AnalysisState::capturing);
    captureState.store (CaptureState::capturing, std::memory_order_release);  // release LAST

    if (worker != nullptr)
        worker->notify();
}

void ShipStudiosGainProcessor::runAssist (const juce::AudioBuffer<float>& capture, double rate)
{
    const auto* audio = capture.getReadPointer (0);
    const auto numSamples = capture.getNumSamples();

    // The SAME window pick and the SAME measurement the band adaptation uses.
    // The assistant is grounded on the numbers this produces, so they have to be
    // the numbers that describe the audio it is about to hear.
    const auto window = chooseWindow (audio, numSamples, rate, analysisWindowSeconds);
    const auto measured = analyseSource (audio + window.startSample, window.numSamples,
                                         rate, rangesFor (Material::unknown));

    if (! measured.valid)
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = measured.failure;
        analysisShortLabel = measured.failure.toUpperCase();
        analysisState.store (AnalysisState::failed);
        return;
    }

    if (! GeminiClient::hasApiKey())
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = "settings assistant needs an API key";
        analysisShortLabel = "NO KEY";
        analysisState.store (AnalysisState::failed);
        return;
    }

    analysisState.store (AnalysisState::assisting);

    const auto suggestion = GeminiClient::suggestSettings (
        audio + window.startSample, window.numSamples, rate, measured.meters);

    if (threadShouldStopAnalysis())
        return;

    if (! suggestion.ok)
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = "assistant: " + suggestion.reasoning;
        analysisShortLabel = "NO SUGGESTION";
        analysisState.store (AnalysisState::failed);
        return;
    }

    // Applied HERE, on the worker, not bounced through MessageManager::callAsync.
    //
    // Measured, not assumed: with callAsync the suggestion never arrived at all
    // under the pedalboard harness -- every parameter read back at its default.
    // pedalboard runs no message loop, and neither does a host doing an offline
    // bounce, so a message-thread hop is a silent no-op in exactly the two
    // situations where you would most want to verify the feature. This is the
    // same trap the analysis worker already avoids by polling instead of using
    // a juce::Timer.
    //
    // setValueNotifyingHost off the audio thread is what a control surface does
    // and is safe here; the audio thread only ever READS these parameters.
    applySuggestedSettings (suggestion);

    {
        const juce::ScopedLock sl (analysisLabelLock);
        assistReasoning = suggestion.reasoning;
        analysisLabel = "in B: " + suggestion.reasoning;
        analysisShortLabel = "SUGGESTED";
    }

    analysisState.store (AnalysisState::adapted);
}

void ShipStudiosGainProcessor::applySuggestedSettings (const ShipStudios::GeminiClient::Settings& s)
{
    // Your settings are preserved in the slot you were on; the suggestion
    // becomes live and is snapshotted into the OTHER slot, so the A/B button
    // flips between "mine" and "the AI's" with no new undo machinery.
    //
    // Deliberately does NOT call recallAbSlot() first, which was the obvious
    // way to write this and is broken: recallAbSlot goes through
    // apvts.replaceState(), whose parameter sync is DEFERRED -- it landed after
    // these writes and clobbered every one of them back to the recalled slot's
    // values. Measured: the model returned distance -35, the parameter read
    // back 0.0.
    storeAbSlot (currentAbSlot);

    const auto set = [this] (const char* id, float value)
    {
        if (auto* p = apvts.getParameter (id))
            p->setValueNotifyingHost (p->convertTo0to1 (value));
    };

    set (distanceParamID, s.distance);
    set (ceilingParamID, s.ceilingDb);
    set (outputParamID, s.outputDb);

    // INPUT is deliberately NOT set. autoGainStart() derives it from MEASURED
    // integrated loudness; replacing a measured answer with a heard one would
    // be a straight regression.

    const auto setBool = [this] (const char* id, bool on)
    {
        if (auto* p = apvts.getParameter (id))
            p->setValueNotifyingHost (on ? 1.0f : 0.0f);
    };

    setBool (extremeParamID, s.extreme);
    setBool (hardClipParamID, s.hardClip);

    currentAbSlot = 1 - currentAbSlot;
    storeAbSlot (currentAbSlot);
}

void ShipStudiosGainProcessor::requestAssist() noexcept
{
    assistArming = true;
    captureIntent.store (CaptureIntent::suggestSettings, std::memory_order_relaxed);
    requestAnalysis();
    assistArming = false;
}

void ShipStudiosGainProcessor::revertToFactory()
{
    publishProfile (factoryBands, currentSampleRate);

    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = {};
        analysisShortLabel = {};
    }

    analysisState.store (AnalysisState::idle);
}

void ShipStudiosGainProcessor::AnalysisWorker::run()
{
    while (! threadShouldExit())
    {
        if (owner.captureState.load (std::memory_order_acquire) == CaptureState::full)
            owner.runAnalysis();

        wait (50);
    }
}

void ShipStudiosGainProcessor::runAnalysis()
{
    analysisState.store (AnalysisState::analysing);

    // Take a COPY of the capture and let the lock go. The classification leg
    // can block for tens of seconds on the network, and prepareToPlay waits on
    // this lock -- holding it across the request would stall the host's next
    // reconfigure for the whole timeout.
    juce::AudioBuffer<float> work;
    double workRate = 48000.0;
    {
        const juce::ScopedLock sl (captureBufferLock);

        // Re-check under the lock: a host reconfigure between the poll and here
        // clears the buffer, and analysing the cleared one would report NO
        // SIGNAL for a capture that was actually fine.
        if (captureState.load (std::memory_order_acquire) != CaptureState::full)
        {
            analysisState.store (AnalysisState::idle);
            return;
        }

        const auto n = captureWritePos.load (std::memory_order_acquire);
        work.setSize (1, juce::jmax (1, n));
        work.copyFrom (0, 0, captureBuffer, 0, 0, n);
        workRate = captureSampleRate;

        captureState.store (CaptureState::idle, std::memory_order_release);
    }

    // Same capture, two possible questions.
    if (captureIntent.load (std::memory_order_relaxed) == CaptureIntent::suggestSettings)
    {
        runAssist (work, workRate);
        return;
    }

    const auto* audio = work.getReadPointer (0);
    const auto numSamples = work.getNumSamples();

    // Choose the window BEFORE measuring. Pure DSP, and the answer that stands
    // whenever the classification leg is off or its window fails validation.
    auto window = chooseWindow (audio, numSamples, workRate, analysisWindowSeconds);

    auto result = analyseSource (audio + window.startSample, window.numSamples,
                                 workRate, rangesFor (Material::unknown));

    if (! result.valid)
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = result.failure;
        analysisShortLabel = result.failure.toUpperCase();
        analysisState.store (AnalysisState::failed);
        return;
    }

    // Publish the MEASURED profile immediately, BEFORE any model is consulted.
    // That ordering is the whole safety argument: by the time the network can
    // fail, the adaptation has already landed, so there is no error path to
    // recover from -- a failure just means the window and the search ranges were
    // not refined.
    publishProfile (result.bands, currentSampleRate);

    const auto windowLabel = [] (const Window& w, double sr)
    {
        return juce::String (w.startSample / sr, 1) + "-"
             + juce::String ((w.startSample + w.numSamples) / sr, 1) + "s";
    };

    auto label = juce::String (result.bandsMoved) + " bands \xe2\x80\xa2 "
               + (result.roomy ? "roomy" : "dry")
               + " \xe2\x80\xa2 " + windowLabel (window, workRate);

    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = label + " \xe2\x80\xa2 measured";
        analysisShortLabel = "ADAPTED";
    }

    analysisState.store (AnalysisState::adapted);

    // --- optional classification leg ---------------------------------------
    // Opt-in, because pressing ANALYSE with this on UPLOADS the capture to
    // Google. It must be a deliberate choice, not a side effect of having a key
    // in the environment.
    auto* geminiOn = apvts.getRawParameterValue (geminiParamID);

    if (geminiOn == nullptr || geminiOn->load() <= 0.5f)
        return;

    if (! GeminiClient::hasApiKey())
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = label + " \xe2\x80\xa2 measured only (no API key)";
        return;
    }

    analysisState.store (AnalysisState::classifying);

    // The WHOLE capture goes up, not the chosen window: locating the performance
    // inside the clip is half of what it is being asked, and it cannot do that
    // from a clip we have already cropped for it.
    const auto verdict = GeminiClient::classify (audio, numSamples, workRate, &geminiCancel);

    if (threadShouldStopAnalysis())
        return;

    if (! verdict.ok)
    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = label + " \xe2\x80\xa2 measured only (" + verdict.note + ")";
        analysisState.store (AnalysisState::adapted);
        return;
    }

    // Gemini contributes exactly two things, neither of them a number the DSP
    // could have measured: WHERE to look, and WHAT the source is (which selects
    // a search window). Every frequency, gain and Q still comes out of
    // analyseSource.
    if (verdict.hasWindow)
    {
        const auto start = juce::jlimit (0, juce::jmax (0, numSamples - 1),
                                         (int) (verdict.windowStartS * workRate));
        const auto len = juce::jlimit (1, numSamples - start,
                                       (int) ((verdict.windowEndS - verdict.windowStartS) * workRate));

        // Long enough to measure? analyseSource needs several FFT frames, and a
        // three-second answer on a 30 s capture is still worth taking.
        if (len >= (int) (3.0 * workRate))
            window = { start, len };
    }

    const auto refined = analyseSource (audio + window.startSample, window.numSamples,
                                        workRate, rangesFor (verdict.material));

    if (refined.valid)
        publishProfile (refined.bands, currentSampleRate);

    {
        const juce::ScopedLock sl (analysisLabelLock);
        analysisLabel = juce::String (refined.valid ? refined.bandsMoved : result.bandsMoved)
                      + " bands \xe2\x80\xa2 " + materialName (verdict.material)
                      + " \xe2\x80\xa2 " + windowLabel (window, workRate)
                      + " \xe2\x80\xa2 " + (result.roomy ? "roomy" : "dry")
                      + (verdict.note.isNotEmpty() ? " \xe2\x80\xa2 " + verdict.note : juce::String());
        analysisShortLabel = juce::String (materialName (verdict.material)).toUpperCase();
    }

    analysisState.store (AnalysisState::adapted);
}

//==============================================================================
juce::AudioProcessorEditor* ShipStudiosGainProcessor::createEditor()
{
    return new ShipStudiosGainEditor (*this);
}

//==============================================================================
void ShipStudiosGainProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    if (auto xml = apvts.copyState().createXml())
    {
        // Ride the program index along on the parameter tree, so a session
        // reopens showing the same preset name it was saved with.
        xml->setAttribute ("currentProgram", currentProgram);

        // The adapted curve travels with the session. Frequencies only -- Q and
        // the endpoint gains encode the PHYSICS of distance and are never
        // material-dependent, so there is nothing else to store. Generation 0
        // means factory, and writing nothing is what makes an un-analysed
        // session load bit-identically to today.
        const auto profile = getDisplayProfile();

        if (profile.generation != 0)
        {
            juce::StringArray hz;

            for (const auto& band : profile.bands)
                hz.add (juce::String (band.freqHz, 3));

            xml->setAttribute ("adaptedHz", hz.joinIntoString (","));
            xml->setAttribute ("adaptedQ", juce::String (profile.bands[2].q, 4));

            const juce::ScopedLock sl (analysisLabelLock);
            xml->setAttribute ("adaptedLabel", analysisLabel);
            xml->setAttribute ("adaptedShort", analysisShortLabel);
        }

        copyXmlToBinary (*xml, destData);
    }
}

void ShipStudiosGainProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (auto xml = getXmlFromBinary (data, sizeInBytes))
    {
        if (xml->hasTagName (apvts.state.getType()))
        {
            currentProgram = juce::jlimit (0, (int) factoryPresets.size() - 1,
                                           xml->getIntAttribute ("currentProgram", 0));
            apvts.replaceState (juce::ValueTree::fromXml (*xml));

            // Group membership rides in the state tree; the atomic cache must
            // follow a restore or a saved LINKed instance would reload deaf.
            linkEnabled.store ((bool) apvts.state.getProperty ("linkGroup", false));

            const auto hz = juce::StringArray::fromTokens (
                xml->getStringAttribute ("adaptedHz"), ",", {});

            if (hz.size() == (int) factoryBands.size())
            {
                auto bands = factoryBands;
                bool sane = true;

                for (int i = 0; i < hz.size(); ++i)
                {
                    const auto f = (float) hz[i].getDoubleValue();

                    // Clamp on the way IN as well as on the way out. A hand-edited
                    // or truncated session must not be able to install a band
                    // outside its range -- the harshness guard depends on it.
                    sane = sane && f >= bandRanges[(size_t) i].minHz * 0.99f
                                && f <= bandRanges[(size_t) i].maxHz * 1.01f;
                    bands[(size_t) i].freqHz = f;
                }

                // PRESENCE's Q is derived, not fixed: it is solved to pin the
                // band's upper skirt under the 5-7 kHz harshness guard, so it
                // must be restored alongside the frequency or a session would
                // reload a band that breaches it.
                if (const auto q = (float) xml->getDoubleAttribute ("adaptedQ"); q > 0.05f && q < 20.0f)
                    bands[2].q = q;

                if (sane)
                {
                    publishProfile (bands, currentSampleRate);

                    const juce::ScopedLock sl (analysisLabelLock);
                    analysisLabel = xml->getStringAttribute ("adaptedLabel");
                    analysisShortLabel = xml->getStringAttribute ("adaptedShort", "ADAPTED");
                    analysisState.store (AnalysisState::adapted);
                }
            }
        }
    }
}

//==============================================================================
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new ShipStudiosGainProcessor();
}
