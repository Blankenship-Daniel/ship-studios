#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>

#include "DistanceCurve.h"

namespace ShipStudios
{

/**
    Measures a captured mono buffer and decides where the four distance bands
    should sit for THAT material.

    Nothing here is asked of a model. Every number comes from the spectrum; the
    only thing a classification can do is shift the search window it looks in
    (see `rangesFor` in DistanceCurve.h).

    The pipeline deliberately mirrors this repo's own proven Python one in
    `drum_prep/dsp.py` -- same ISO third-octave centres, same `fc/2^(1/6)` band
    edges, same "subtract the broadband mean over 80 Hz-12 kHz" trick for level
    independence -- so the C++ and the Python agree on what a source looks like.
*/

/** ISO third-octave centres, identical to drum_prep/dsp.py THIRD_OCT. */
inline constexpr std::array<float, 30> thirdOctaveCentres {
    25.0f, 31.5f, 40.0f, 50.0f, 63.0f, 80.0f, 100.0f, 125.0f, 160.0f, 200.0f,
    250.0f, 315.0f, 400.0f, 500.0f, 630.0f, 800.0f, 1000.0f, 1250.0f, 1600.0f,
    2000.0f, 2500.0f, 3150.0f, 4000.0f, 5000.0f, 6300.0f, 8000.0f, 10000.0f,
    12500.0f, 16000.0f, 20000.0f
};

/** Below this peak level a capture carries no usable signal. Gemini will still
    answer confidently about silence -- measured: an empty file returned
    "drums / roomy / 0.9" -- so this gate protects the whole feature, not just
    the DSP. */
inline constexpr float minAnalysisPeakDb = -60.0f;

/** The measured picture of the source, in the form a model can be GROUNDED on.

    Every one of these is something the ~16 kbps mono downmix destroys or
    distorts -- level, peak, crest, spectral balance. Handing them to Gemini as
    ground truth to reason FROM, rather than letting it re-estimate them by ear,
    is the pattern the six `[G]` critique tools in this repo already use, and it
    exists because the codec makes the model chronically under-read highs and
    over-read lows. */
struct Meters
{
    float peakDb = -120.0f;
    float crestDb = 0.0f;
    float tiltDbPerOctave = 0.0f;
    float centroidHz = 0.0f;

    /** Level-independent 5-band balance, in dB relative to the broadband mean:
        sub / low / mid / high-mid / air. */
    std::array<float, 5> bandDb {};
};

struct AnalysisResult
{
    bool valid = false;                    // false => nothing moved, report why
    juce::String failure;                  // "NO SIGNAL" etc.

    std::array<BandSpec, 4> bands = factoryBands;
    bool roomy = false;                    // MEASURED from crest, never asked
    float crestDb = 0.0f;
    int   bandsMoved = 0;

    Meters meters;
};

/** RBJ bell: bandwidth in octaves <-> Q. */
inline float qForBandwidthOctaves (float bandwidthOctaves) noexcept
{
    return 1.0f / (2.0f * std::sinh (0.34657359f * juce::jmax (0.05f, bandwidthOctaves)));
}

/** A half-open sample range inside the capture. */
struct Window { int startSample = 0; int numSamples = 0; };

/** Pick the most representative `windowSeconds` inside a longer capture.

    Fitting the bands to whatever happened to be under the playhead is how you
    end up describing a count-in, a held cymbal, or -- measured, on this repo's
    own overhead stems -- eleven seconds of spoken-word bleed before the drums
    start. This scores every candidate window on how much CONTINUOUS programme
    it holds and takes the best.

    Pure DSP, and the fallback whenever the classification leg is off or its
    answer fails validation. */
Window chooseWindow (const float* samples, int numSamples, double sampleRate,
                     double windowSeconds);

/** Analyse a mono buffer. `ranges` comes from `rangesFor(material)`. */
AnalysisResult analyseSource (const float* samples,
                              int numSamples,
                              double sampleRate,
                              const std::array<BandRange, 4>& ranges);

} // namespace ShipStudios
