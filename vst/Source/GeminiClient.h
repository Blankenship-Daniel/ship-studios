#pragma once

#include <juce_audio_formats/juce_audio_formats.h>
#include <juce_data_structures/juce_data_structures.h>

#include "DistanceCurve.h"
#include "SourceAnalysis.h"

namespace ShipStudios
{

/**
    Asks Gemini ONE question: what is this material?

    It is never asked for a frequency, a gain or a Q. This repo documents in
    three places, with measured counter-examples, that the ~16 kbps mono codec
    the API downmixes to makes its tonal read unreliable -- it under-reads highs
    and over-reads lows by several dB/octave, and iterating on its feedback
    walks you into harshness it cannot hear. So the DSP owns every number and
    the model owns only intent; the answer selects a SEARCH WINDOW
    (`rangesFor`), never a value.

    Measured against the live API before this was written (2026-08-01):
      - material on three known drum sources: 3/3 correct
      - ambience on a room mic vs overheads: INVERTED -> not asked for, derived
        from crest factor instead
      - a 44-byte empty WAV: answered "drums / roomy / 0.9" with no audio at all
        -> the caller MUST gate on signal level before ever reaching here

    Every failure is non-fatal by construction: the DSP profile is already
    published before this runs, so there is no error path to recover from.
*/
/**
    Lets another thread abort an in-flight classify().

    The worker can sit inside a blocking network call for tens of seconds, and
    juce::Thread::stopThread's timeout FORCE-KILLS a thread that does not exit
    in time -- so teardown needs a way to unblock the read, not just ask nicely.
    cancel() cancels the registered stream (WebInputStream::cancel is
    thread-safe and unblocks a pending read) and latches, so a classify that
    has not yet connected aborts at its next check instead of connecting.

    rearm() clears the latch; call it when the worker (re)starts, or every
    later classify dies instantly on the stale flag.
*/
class NetworkCancel
{
public:
    void cancel()
    {
        const juce::ScopedLock sl (lock);
        cancelled = true;

        if (active != nullptr)
            active->cancel();
    }

    void rearm()
    {
        const juce::ScopedLock sl (lock);
        cancelled = false;
    }

    bool isCancelled() const
    {
        const juce::ScopedLock sl (lock);
        return cancelled;
    }

private:
    friend class GeminiClient;

    // Registration covers the gap between cancel() and the stream existing:
    // attaching after a cancel() cancels the stream immediately.
    void attach (juce::WebInputStream* s)
    {
        const juce::ScopedLock sl (lock);
        active = s;

        if (cancelled && s != nullptr)
            s->cancel();
    }

    void detach()
    {
        const juce::ScopedLock sl (lock);
        active = nullptr;
    }

    juce::CriticalSection lock;
    juce::WebInputStream* active = nullptr;
    bool cancelled = false;
};

class GeminiClient
{
public:
    struct Result
    {
        bool     ok = false;
        Material material = Material::unknown;
        float    confidence = 0.0f;
        juce::String note;      // model's one-liner, or the failure reason

        /** The stretch of the capture that is representative programme
            material. Locating an event in time is a genuine strength of the
            model and is untouched by the mono downmix -- unlike anything
            tonal. It selects WHICH audio the DSP measures; it never influences
            what the DSP concludes about it.

            hasWindow is false when the model declined or its answer failed
            validation, in which case the caller keeps its own DSP pick. */
        bool  hasWindow = false;
        float windowStartS = 0.0f;
        float windowEndS = 0.0f;
    };

    /** Where the key came from. Worth surfacing: "no key" and "key rejected"
        look identical from the UI otherwise. */
    enum class KeySource { none, environment, propertiesFile };

    static juce::String findApiKey (KeySource& sourceOut);
    static void storeApiKey (const juce::String& key);
    static bool hasApiKey();

    /** Blocking. Call from the analysis worker, never the audio or message
        thread. `samples` is the mono capture; it is encoded as 16-bit WAV.

        `cancel`, if given, lets teardown abort the call from another thread
        mid-connect or mid-read -- without it, stopping the worker during a
        stalled request degrades to juce::Thread's kill-after-timeout. */
    static Result classify (const float* samples,
                            int numSamples,
                            double sampleRate,
                            NetworkCancel* cancel = nullptr,
                            int timeoutMs = 30000);

    //==========================================================================
    /** A proposed position for the plugin's own controls.

        This is the one place a model is allowed to choose a NUMBER, and the
        split is deliberate: the DSP still owns where the EQ bands sit -- that is
        a measurement -- while these are the controls a listener would reach for,
        which is a taste judgement.

        The honest caveat, stated rather than buried: distance perception IS
        ambience perception, and ambience is the one axis this model measured
        WRONG here (it called a room mic "moderate" and the overheads "roomy",
        n=2). Three things carry the risk: the request is meter-grounded, every
        value is clamped on arrival, and the result lands in the A/B compare
        slot rather than over the top of your settings. */
    struct Settings
    {
        bool ok = false;

        float distance = 0.0f;      // -100 (far) .. +100 (close)
        bool  extreme = false;      // 2X
        bool  hardClip = false;     // soft vs hard clip character
        float ceilingDb = -0.3f;
        float outputDb = 0.0f;

        juce::String reasoning;     // shown to the user; nothing parses it
    };

    /** Blocking. Sends the audio AND the measured meters, so the model reasons
        from ground truth rather than re-estimating level and balance through a
        codec that destroys both. `cancel` as in classify(): the teardown hook
        that keeps stopThread from degrading to a kill. */
    static Settings suggestSettings (const float* samples,
                                     int numSamples,
                                     double sampleRate,
                                     const Meters& meters,
                                     NetworkCancel* cancel = nullptr,
                                     int timeoutMs = 30000);

    /** Exposed for the harness: the exact JSON body that would be POSTed, minus
        the audio. Keeps the schema testable without spending a request. */
    static juce::String buildRequestJson (const juce::String& base64Wav);
    static juce::String buildAssistJson (const juce::String& base64Wav, const Meters&);

    static Material materialFromString (const juce::String&) noexcept;

private:
    static juce::MemoryBlock encodeWav (const float* samples, int numSamples, double sampleRate);
};

} // namespace ShipStudios
