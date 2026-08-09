#include "SourceAnalysis.h"

#include <algorithm>
#include <vector>

namespace ShipStudios
{
namespace
{

constexpr int   fftOrder = 13;              // 8192 -> 5.9 Hz/bin at 48 k, 171 ms window
constexpr int   fftSize  = 1 << fftOrder;
constexpr float unresolved = std::numeric_limits<float>::quiet_NaN();

bool resolved (float v) noexcept { return ! std::isnan (v); }

//==============================================================================
/** Averaged power spectrum, with quiet frames discarded.

    Frame gating matters more than it looks: a sparse source (a vocal take, a
    slow drum part) is mostly silence, and averaging every frame would measure
    the room tone rather than the instrument.
*/
std::vector<float> powerSpectrum (const float* samples, int numSamples, float& peakOut,
                                  float& crestOut)
{
    juce::dsp::FFT fft (fftOrder);
    juce::dsp::WindowingFunction<float> window ((size_t) fftSize,
                                                juce::dsp::WindowingFunction<float>::hann,
                                                false);

    const auto hop = fftSize / 2;
    std::vector<float> accum ((size_t) fftSize / 2, 0.0f);
    std::vector<float> frame ((size_t) fftSize * 2, 0.0f);

    // Two passes: find the loudest frame, then average only what is close to it.
    std::vector<float> frameRms;
    for (int start = 0; start + fftSize <= numSamples; start += hop)
    {
        double sum = 0.0;
        for (int i = 0; i < fftSize; ++i)
            sum += (double) samples[start + i] * samples[start + i];

        frameRms.push_back ((float) std::sqrt (sum / fftSize));
    }

    if (frameRms.empty())
        return {};

    const auto loudest = *std::max_element (frameRms.begin(), frameRms.end());
    const auto gate = loudest * 0.1f;       // -20 dB relative

    // Peak and crest over the whole capture -- crest is how ambience is judged,
    // since Gemini's ambience read measured backwards.
    double sumSq = 0.0;
    float peak = 0.0f;
    for (int i = 0; i < numSamples; ++i)
    {
        peak = juce::jmax (peak, std::abs (samples[i]));
        sumSq += (double) samples[i] * samples[i];
    }

    const auto rms = (float) std::sqrt (sumSq / juce::jmax (1, numSamples));
    peakOut = peak;
    crestOut = juce::Decibels::gainToDecibels (peak, -120.0f)
             - juce::Decibels::gainToDecibels (rms, -120.0f);

    int used = 0, index = 0;
    for (int start = 0; start + fftSize <= numSamples; start += hop, ++index)
    {
        if (frameRms[(size_t) index] < gate)
            continue;

        std::fill (frame.begin(), frame.end(), 0.0f);
        std::copy (samples + start, samples + start + fftSize, frame.begin());
        window.multiplyWithWindowingTable (frame.data(), (size_t) fftSize);
        fft.performFrequencyOnlyForwardTransform (frame.data());

        for (size_t k = 0; k < accum.size(); ++k)
            accum[k] += frame[k] * frame[k];

        ++used;
    }

    if (used == 0)
        return {};

    for (auto& v : accum)
        v /= (float) used;

    return accum;
}

//==============================================================================
/** Third-octave band energies. A band with no FFT bin returns NaN rather than a
    floor -- the repo learned this the hard way: a -200 dB floor made a measured
    tilt read 9.84 dB/oct against a true ~3.0. */
std::array<float, 30> bandDecibels (const std::vector<float>& spectrum, double sampleRate)
{
    std::array<float, 30> out {};
    const auto binHz = (float) (sampleRate / fftSize);
    const auto edgeRatio = std::pow (2.0f, 1.0f / 6.0f);

    for (size_t b = 0; b < thirdOctaveCentres.size(); ++b)
    {
        const auto lo = thirdOctaveCentres[b] / edgeRatio;
        const auto hi = thirdOctaveCentres[b] * edgeRatio;

        const auto firstBin = (int) std::ceil (lo / binHz);
        const auto lastBin  = (int) std::floor (hi / binHz);

        double sum = 0.0;
        int n = 0;
        for (int k = juce::jmax (1, firstBin); k <= lastBin && k < (int) spectrum.size(); ++k)
        {
            sum += spectrum[(size_t) k];
            ++n;
        }

        out[b] = n > 0 ? juce::Decibels::gainToDecibels ((float) std::sqrt (sum / n), -160.0f)
                       : unresolved;
    }

    return out;
}

/** Subtract the broadband mean over 80 Hz-12 kHz, exactly as drum_prep's
    `shape()` does. This is what makes a quiet take and a loud take of the same
    material produce identical numbers. */
void makeLevelIndependent (std::array<float, 30>& db)
{
    double sum = 0.0;
    int n = 0;

    for (size_t b = 0; b < db.size(); ++b)
        if (resolved (db[b]) && thirdOctaveCentres[b] >= 80.0f
                             && thirdOctaveCentres[b] <= 12000.0f)
        {
            sum += db[b];
            ++n;
        }

    if (n == 0)
        return;

    const auto mean = (float) (sum / n);
    for (auto& v : db)
        if (resolved (v))
            v -= mean;
}

/** Remove the material's own broadband slope.

    Programme is roughly pink (-3 to -4.5 dB/oct), so a raw argmax over
    120-500 Hz always lands on the low edge of the window regardless of what the
    source actually does. Peaks in the RESIDUAL are genuine departures from this
    material's own slope, which is what we want to aim a band at.
*/
std::array<float, 30> detrend (const std::array<float, 30>& db)
{
    double sx = 0, sy = 0, sxx = 0, sxy = 0;
    int n = 0;

    for (size_t b = 0; b < db.size(); ++b)
        if (resolved (db[b]))
        {
            const auto x = std::log2 (thirdOctaveCentres[b]);
            sx += x; sy += db[b]; sxx += x * x; sxy += x * db[b];
            ++n;
        }

    auto out = db;

    if (n < 3)
        return out;

    const auto denom = n * sxx - sx * sx;
    if (std::abs (denom) < 1.0e-9)
        return out;

    const auto slope = (n * sxy - sx * sy) / denom;
    const auto intercept = (sy - slope * sx) / n;

    for (size_t b = 0; b < out.size(); ++b)
        if (resolved (out[b]))
            out[b] -= (float) (slope * std::log2 (thirdOctaveCentres[b]) + intercept);

    return out;
}

/** Peak within a window, refined between third-octave centres by parabolic
    interpolation. Returns 0 if nothing clears `minProminenceDb`. */
float peakFrequency (const std::array<float, 30>& curve, float loHz, float hiHz,
                     float minProminenceDb)
{
    int best = -1;
    float bestDb = -1.0e9f;
    double sum = 0.0;
    int n = 0;

    for (size_t b = 0; b < curve.size(); ++b)
    {
        if (! resolved (curve[b]) || thirdOctaveCentres[b] < loHz
                                  || thirdOctaveCentres[b] > hiHz)
            continue;

        sum += curve[b];
        ++n;

        if (curve[b] > bestDb) { bestDb = curve[b]; best = (int) b; }
    }

    if (best < 0 || n < 3)
        return 0.0f;

    if (bestDb - (float) (sum / n) < minProminenceDb)
        return 0.0f;                        // featureless -- do not move the band

    // Parabolic refine in third-octave steps.
    auto refined = thirdOctaveCentres[(size_t) best];

    if (best > 0 && best + 1 < (int) curve.size()
        && resolved (curve[(size_t) best - 1]) && resolved (curve[(size_t) best + 1]))
    {
        const auto a = curve[(size_t) best - 1];
        const auto b2 = curve[(size_t) best];
        const auto c = curve[(size_t) best + 1];
        const auto denom = a - 2.0f * b2 + c;

        if (std::abs (denom) > 1.0e-6f)
        {
            const auto delta = juce::jlimit (-1.0f, 1.0f, 0.5f * (a - c) / denom);
            refined *= std::pow (2.0f, delta / 3.0f);
        }
    }

    return refined;
}

/** HF rolloff knee by two-segment hinge fit.

    No such helper exists anywhere in this repo -- this is new. Uses the
    UN-detrended curve on purpose: the knee IS a slope change, so detrending
    would erase the very thing being looked for.
*/
float rolloffKnee (const std::array<float, 30>& shapeDb, float searchLoHz, float searchHiHz,
                   float& slopeChangeOut)
{
    const auto fit = [&shapeDb] (int from, int to, double& slope, double& intercept)
    {
        double sx = 0, sy = 0, sxx = 0, sxy = 0;
        int n = 0;

        for (int b = from; b <= to; ++b)
            if (resolved (shapeDb[(size_t) b]))
            {
                const auto x = std::log2 (thirdOctaveCentres[(size_t) b]);
                sx += x; sy += shapeDb[(size_t) b]; sxx += x * x;
                sxy += x * shapeDb[(size_t) b];
                ++n;
            }

        if (n < 2) return false;

        const auto denom = n * sxx - sx * sx;
        if (std::abs (denom) < 1.0e-9) return false;

        slope = (n * sxy - sx * sy) / denom;
        intercept = (sy - slope * sx) / n;
        return true;
    };

    int lo = 0, hi = (int) thirdOctaveCentres.size() - 1;
    while (lo < hi && thirdOctaveCentres[(size_t) lo] < searchLoHz) ++lo;
    while (hi > lo && thirdOctaveCentres[(size_t) hi] > searchHiHz) --hi;

    slopeChangeOut = 0.0f;

    if (hi - lo < 5)
        return 0.0f;

    double bestScore = 1.0e18;
    float bestKnee = 0.0f;
    float bestChange = 0.0f;

    for (int k = lo + 2; k <= hi - 2; ++k)
    {
        double s1 = 0, i1 = 0, s2 = 0, i2 = 0;
        if (! fit (lo, k, s1, i1) || ! fit (k, hi, s2, i2))
            continue;

        double score = 0.0;
        for (int b = lo; b <= hi; ++b)
        {
            if (! resolved (shapeDb[(size_t) b])) continue;
            const auto x = std::log2 (thirdOctaveCentres[(size_t) b]);
            const auto pred = b <= k ? s1 * x + i1 : s2 * x + i2;
            const auto r = shapeDb[(size_t) b] - pred;
            score += r * r;
        }

        if (score < bestScore)
        {
            bestScore = score;
            bestKnee = thirdOctaveCentres[(size_t) k];
            bestChange = (float) (s2 - s1);
        }
    }

    slopeChangeOut = bestChange;

    // Only a genuine steepening counts. A bright synth has no knee, and forcing
    // one would put the AIR shelf somewhere arbitrary.
    return bestChange <= -3.0f ? bestKnee : 0.0f;
}

/** Frequency below which `fraction` of the 20-500 Hz energy sits. */
float lowEnergyMedian (const std::array<float, 30>& db, float fraction)
{
    std::array<double, 30> power {};
    double total = 0.0;

    for (size_t b = 0; b < db.size(); ++b)
    {
        const auto fc = thirdOctaveCentres[b];
        if (! resolved (db[b]) || fc < 20.0f || fc > 500.0f) { power[b] = 0.0; continue; }

        power[b] = std::pow (10.0, db[b] / 10.0);
        total += power[b];
    }

    if (total <= 0.0)
        return 0.0f;

    double run = 0.0;
    for (size_t b = 0; b < power.size(); ++b)
    {
        run += power[b];
        if (run >= total * fraction)
            return thirdOctaveCentres[b];
    }

    return 0.0f;
}

} // namespace

//==============================================================================
Window chooseWindow (const float* samples, int numSamples, double sampleRate,
                     double windowSeconds)
{
    const auto want = (int) std::round (windowSeconds * sampleRate);

    if (numSamples <= want)
        return { 0, numSamples };

    // 100 ms blocks: long enough that one drum hit does not dominate, short
    // enough to resolve a bar of silence.
    const auto blockLen = juce::jmax (1, (int) std::round (0.1 * sampleRate));
    const auto numBlocks = numSamples / blockLen;

    if (numBlocks < 2)
        return { 0, want };

    std::vector<float> blockDb ((size_t) numBlocks, -120.0f);

    for (int b = 0; b < numBlocks; ++b)
    {
        double sum = 0.0;
        const auto* p = samples + (size_t) b * (size_t) blockLen;

        for (int i = 0; i < blockLen; ++i)
            sum += (double) p[i] * (double) p[i];

        blockDb[(size_t) b] = 10.0f * std::log10 ((float) juce::jmax (1.0e-12, sum / blockLen));
    }

    // "Active" is relative to the capture's OWN peak block, not an absolute
    // threshold: a quiet passage of real playing must still count as content.
    const auto peakDb = *std::max_element (blockDb.begin(), blockDb.end());
    const auto activeDb = peakDb - 25.0f;

    const auto blocksPerWindow = juce::jmax (1, want / blockLen);

    auto bestStart = 0;
    auto bestScore = -1.0e9f;

    for (int b = 0; b + blocksPerWindow <= numBlocks; ++b)
    {
        auto active = 0;
        auto sum = 0.0f;

        for (int k = 0; k < blocksPerWindow; ++k)
        {
            const auto db = blockDb[(size_t) (b + k)];
            sum += db;
            if (db >= activeDb) ++active;
        }

        // Continuity first, loudness only as the tie-break. A window that is
        // half silence and half a very loud fill would otherwise beat a window
        // of steady playing, which is the opposite of what we want.
        const auto score = 100.0f * ((float) active / (float) blocksPerWindow)
                         + sum / (float) blocksPerWindow;

        if (score > bestScore)
        {
            bestScore = score;
            bestStart = b * blockLen;
        }
    }

    return { bestStart, juce::jmin (want, numSamples - bestStart) };
}

AnalysisResult analyseSource (const float* samples, int numSamples, double sampleRate,
                              const std::array<BandRange, 4>& ranges)
{
    AnalysisResult result;
    result.bands = factoryBands;

    if (samples == nullptr || numSamples < fftSize * 2 || sampleRate <= 0.0)
    {
        result.failure = "TOO SHORT";
        return result;
    }

    float peak = 0.0f, crest = 0.0f;
    const auto spectrum = powerSpectrum (samples, numSamples, peak, crest);

    // The gate that keeps the whole feature honest. Measured: Gemini answers
    // "drums / roomy / 0.9" for a file containing no audio at all.
    if (spectrum.empty() || juce::Decibels::gainToDecibels (peak, -120.0f) < minAnalysisPeakDb)
    {
        result.failure = "NO SIGNAL";
        return result;
    }

    result.crestDb = crest;

    // Ambience measured, not asked. A roomy source has its transients filled in
    // by reflections, so it runs a lower crest than the same kit close-miked.
    result.roomy = crest < 12.0f;

    auto shaped = bandDecibels (spectrum, sampleRate);
    makeLevelIndependent (shaped);
    const auto residual = detrend (shaped);

    // --- meters, for grounding a model -------------------------------------
    result.meters.peakDb = juce::Decibels::gainToDecibels (peak, -120.0f);
    result.meters.crestDb = crest;

    {
        // Tilt: least squares of the shaped curve against log2(f), which is the
        // same fit `detrend` removes -- recovered here rather than recomputed
        // differently, so the number the model sees is the number the band
        // placement was derived against.
        double sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, n = 0.0;
        double weighted = 0.0, total = 0.0;

        for (size_t b = 0; b < shaped.size(); ++b)
        {
            if (std::isnan (shaped[b]))
                continue;

            const auto x = std::log2 (thirdOctaveCentres[b]);
            sx += x; sy += shaped[b]; sxx += x * x; sxy += x * shaped[b]; n += 1.0;

            // Centroid from the LINEAR band powers, not the dB curve: a dB-
            // weighted mean is meaningless (negative weights).
            const auto power = std::pow (10.0, shaped[b] / 10.0);
            weighted += power * thirdOctaveCentres[b];
            total += power;
        }

        if (n > 2.0 && (n * sxx - sx * sx) != 0.0)
            result.meters.tiltDbPerOctave = (float) ((n * sxy - sx * sy) / (n * sxx - sx * sx));

        if (total > 0.0)
            result.meters.centroidHz = (float) (weighted / total);
    }

    {
        // Five bands, by third-octave centre: sub / low / mid / high-mid / air.
        constexpr float edges[6] { 0.0f, 80.0f, 300.0f, 2000.0f, 6000.0f, 30000.0f };

        for (int k = 0; k < 5; ++k)
        {
            double sum = 0.0;
            int count = 0;

            for (size_t b = 0; b < shaped.size(); ++b)
            {
                const auto fc = thirdOctaveCentres[b];

                if (! std::isnan (shaped[b]) && fc >= edges[k] && fc < edges[k + 1])
                {
                    sum += shaped[b];
                    ++count;
                }
            }

            result.meters.bandDb[(size_t) k] = count > 0 ? (float) (sum / count) : 0.0f;
        }
    }

    auto freq = std::array<float, 4> { factoryBands[0].freqHz, factoryBands[1].freqHz,
                                       factoryBands[2].freqHz, factoryBands[3].freqHz };
    auto qs = std::array<float, 4> { factoryBands[0].q, factoryBands[1].q,
                                     factoryBands[2].q, factoryBands[3].q };

    // --- PROXIMITY: where this source's low end actually sits ---------------
    if (const auto median = lowEnergyMedian (shaped, 0.5f); median > 0.0f)
    {
        freq[0] = juce::jlimit (ranges[0].minHz, ranges[0].maxHz, median * 0.75f);
        ++result.bandsMoved;
    }

    // --- ROOM: the boxiness peak, and how wide it is ------------------------
    if (const auto f = peakFrequency (residual, ranges[1].searchLoHz, ranges[1].searchHiHz, 1.5f);
        f > 0.0f)
    {
        freq[1] = juce::jlimit (ranges[1].minHz, ranges[1].maxHz, f);
        ++result.bandsMoved;
    }

    // --- PRESENCE: attack/detail energy -------------------------------------
    if (const auto f = peakFrequency (residual, ranges[2].searchLoHz, ranges[2].searchHiHz, 1.5f);
        f > 0.0f)
    {
        freq[2] = juce::jlimit (ranges[2].minHz, ranges[2].maxHz, f);
        ++result.bandsMoved;
    }

    // --- AIR: the rolloff knee ----------------------------------------------
    float slopeChange = 0.0f;
    if (const auto knee = rolloffKnee (shaped, ranges[3].searchLoHz,
                                       juce::jmin (ranges[3].searchHiHz,
                                                   (float) (sampleRate * 0.45)),
                                       slopeChange);
        knee > 0.0f)
    {
        freq[3] = juce::jlimit (ranges[3].minHz, ranges[3].maxHz, knee);
        ++result.bandsMoved;
    }

    // --- ordering: never let two bands collide ------------------------------
    freq[1] = juce::jmax (freq[1], freq[0] * minBandRatio);
    freq[2] = juce::jmax (freq[2], freq[1] * minBandRatio);
    freq[3] = juce::jmax (freq[3], freq[2] * 1.6f);

    for (size_t i = 0; i < freq.size(); ++i)
        freq[i] = juce::jlimit (ranges[i].minHz, ranges[i].maxHz, freq[i]);

    // --- Q ------------------------------------------------------------------
    // PRESENCE's Q is NOT measured: it is solved so the bell's upper skirt stays
    // pinned below this repo's 5-7 kHz harshness guard. At the factory 3200 Hz /
    // Q 1.0 that skirt already sits at 5178 Hz, so moving the band up at fixed Q
    // would push it straight through the guard.
    constexpr float presenceSkirtHz = 5178.0f;
    qs[2] = freq[2] <= 3200.0f
              ? 1.0f
              : juce::jlimit (1.0f, 3.0f,
                              qForBandwidthOctaves (2.0f * std::log2 (presenceSkirtHz / freq[2])));

    for (size_t i = 0; i < result.bands.size(); ++i)
    {
        result.bands[i].freqHz = freq[i];
        result.bands[i].q = qs[i];
        // type, closeDb, farDb and name are NEVER adapted -- they are the
        // calibrated distance model, and the level law is built around them.
    }

    result.valid = true;
    return result;
}

} // namespace ShipStudios
