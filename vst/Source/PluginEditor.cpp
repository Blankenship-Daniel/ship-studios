#include "PluginEditor.h"
#include "GeminiClient.h"

using namespace ShipStudios;

//==============================================================================
// Palette
//==============================================================================
const juce::Colour ShipStudiosLookAndFeel::background { 0xff141417 };
const juce::Colour ShipStudiosLookAndFeel::panel      { 0xff1c1c21 };
const juce::Colour ShipStudiosLookAndFeel::accent     { 0xffe08a3c };
const juce::Colour ShipStudiosLookAndFeel::text       { 0xffe8e8ec };
const juce::Colour ShipStudiosLookAndFeel::textMuted  { 0xff86868f };
const juce::Colour ShipStudiosLookAndFeel::track      { 0xff2a2a31 };
const juce::Colour ShipStudiosLookAndFeel::cap        { 0xffcfcfd6 };
const juce::Colour ShipStudiosLookAndFeel::accentDim  { 0xff6d6a67 };

ShipStudiosLookAndFeel::ShipStudiosLookAndFeel()
{
    setColour (juce::ResizableWindow::backgroundColourId, background);
    setColour (juce::Label::textColourId, text);
    setColour (juce::Label::backgroundColourId, juce::Colours::transparentBlack);
    setColour (juce::Label::outlineWhenEditingColourId, accent);
    setColour (juce::TextEditor::highlightColourId, accent.withAlpha (0.3f));
    setColour (juce::TextEditor::backgroundColourId, panel);
    setColour (juce::TextEditor::textColourId, text);
    setColour (juce::CaretComponent::caretColourId, accent);

    // The horizontal output trim falls through to LookAndFeel_V4's drawing, so
    // give it our colours rather than JUCE's stock blue.
    setColour (juce::Slider::backgroundColourId, track);
    setColour (juce::Slider::trackColourId, accent);
    setColour (juce::Slider::thumbColourId, cap);
    setColour (juce::Slider::textBoxTextColourId, text);
    setColour (juce::Slider::textBoxBackgroundColourId, juce::Colours::transparentBlack);
    setColour (juce::Slider::textBoxOutlineColourId, juce::Colours::transparentBlack);
}

//==============================================================================
void ShipStudiosLookAndFeel::drawLinearSlider (juce::Graphics& g,
                                               int x, int y, int width, int height,
                                               float sliderPos,
                                               float minSliderPos, float maxSliderPos,
                                               juce::Slider::SliderStyle style,
                                               juce::Slider& slider)
{
    if (style == juce::Slider::LinearHorizontal)
    {
        auto bounds = juce::Rectangle<float> ((float) x, (float) y,
                                              (float) width, (float) height);
        const auto centreY = bounds.getCentreY();
        constexpr float barHeight = 4.0f;

        const juce::Rectangle<float> groove { bounds.getX(), centreY - barHeight * 0.5f,
                                              bounds.getWidth(), barHeight };
        g.setColour (track);
        g.fillRoundedRectangle (groove, barHeight * 0.5f);

        // A BIPOLAR range fills from its centre, not from the left. Filling from
        // the left drew 0 dB on a -24..+24 control as a half-full bar, implying
        // something was applied when nothing was -- and contradicting the main
        // fader, which already fills from centre.
        const bool bipolar = slider.getMinimum() < 0.0 && slider.getMaximum() > 0.0;
        const auto originX = bipolar
            ? juce::jmap ((float) slider.valueToProportionOfLength (0.0),
                          bounds.getX(), bounds.getRight())
            : bounds.getX();

        if (std::abs (originX - sliderPos) > 0.5f)
        {
            g.setColour (accentDim);
            g.fillRoundedRectangle ({ juce::jmin (originX, sliderPos),
                                      centreY - barHeight * 0.5f,
                                      std::abs (originX - sliderPos), barHeight },
                                    barHeight * 0.5f);
        }

        if (bipolar)
        {
            g.setColour (textMuted.withAlpha (0.5f));
            g.fillRect (originX - 0.5f, centreY - 7.0f, 1.0f, 14.0f);
        }

        const auto knob = juce::jmin (13.0f, bounds.getHeight());
        const juce::Rectangle<float> thumb { sliderPos - knob * 0.5f, centreY - knob * 0.5f,
                                             knob, knob };
        g.setColour (juce::Colours::black.withAlpha (0.4f));
        g.fillEllipse (thumb.translated (0.0f, 1.0f));
        g.setColour (cap);
        g.fillEllipse (thumb);
        return;
    }

    if (style != juce::Slider::LinearVertical)
    {
        LookAndFeel_V4::drawLinearSlider (g, x, y, width, height, sliderPos,
                                          minSliderPos, maxSliderPos, style, slider);
        return;
    }

    // Unused on a single-value slider -- JUCE sets both equal to sliderPos.
    juce::ignoreUnused (minSliderPos, maxSliderPos);

    // Ticks are opt-in PER SLIDER. tickMarks lives on the LookAndFeel, which is
    // shared, so without this the input and output faders would each draw the
    // distance scale beside them.
    const bool hasTicks = ! tickMarks.isEmpty()
                       && (bool) slider.getProperties().getWithDefault ("distanceScale", false);
    const auto column = hasTicks ? grooveColumnWidth : (float) width;
    const auto centreX = (float) x + column * 0.5f;

    // Only the DISTANCE fader reaches this path now: the input and output trims
    // became GainField drag numbers, which paint themselves.
    constexpr float trackWidth = 8.0f;

    // The groove spans the THUMB'S TRAVEL, not the raw bounds: JUCE insets the
    // travel by thumbRadius at each end, so a full-bounds groove would show ends
    // the cap can never reach and put the scale out of step with it.
    const auto travelTop    = (float) y + (float) thumbRadius;
    const auto travelBottom = (float) y + (float) height - (float) thumbRadius;

    // proportion 0 == minimum value == bottom of the travel.
    const auto yForProportion = [travelTop, travelBottom] (float proportion)
    {
        return juce::jmap (proportion, 0.0f, 1.0f, travelBottom, travelTop);
    };

    const juce::Rectangle<float> groove { centreX - trackWidth * 0.5f, travelTop,
                                          trackWidth, travelBottom - travelTop };

    const auto zeroY = yForProportion ((float) slider.valueToProportionOfLength (0.0));

    g.setColour (track);
    g.fillRoundedRectangle (groove, trackWidth * 0.5f);

    // Distance is bipolar, so the fill reads from the centre rather than from
    // the bottom: closer grows upward, further drains downward.
    if (std::abs (zeroY - sliderPos) > 0.5f)
    {
        const juce::Rectangle<float> fill { centreX - trackWidth * 0.5f,
                                            juce::jmin (zeroY, sliderPos),
                                            trackWidth,
                                            std::abs (zeroY - sliderPos) };
        g.setColour (accent);
        g.fillRoundedRectangle (fill, trackWidth * 0.5f);
    }

    // Centre marker: on the distance fader it locates FLAT; on a gain fader it
    // locates unity. Either way it is the "you have not moved this" reference.
    g.setColour (textMuted.withAlpha (0.55f));
    g.fillRect (centreX - 12.0f, zeroY - 0.5f, 24.0f, 1.0f);

    // Fader cap
    const auto thisCapWidth = juce::jmin (capWidth, (float) width - 4.0f);
    const juce::Rectangle<float> thumb { centreX - thisCapWidth * 0.5f,
                                         sliderPos - capHeight * 0.5f,
                                         thisCapWidth, capHeight };

    g.setColour (juce::Colours::black.withAlpha (0.45f));
    g.fillRoundedRectangle (thumb.translated (0.0f, 1.5f), 3.5f);

    g.setGradientFill (juce::ColourGradient (cap.brighter (0.15f), 0.0f, thumb.getY(),
                                             cap.darker (0.35f),  0.0f, thumb.getBottom(),
                                             false));
    g.fillRoundedRectangle (thumb, 3.5f);

    // Grip line
    g.setColour (accent);
    g.fillRect (thumb.getX() + 5.0f, thumb.getCentreY() - 0.75f, thisCapWidth - 10.0f, 1.5f);

    // Scale, mapped through the same travel range as the thumb above.
    if (! hasTicks)
        return;

    const auto tickX = (float) x + column;
    g.setFont (juce::Font (juce::FontOptions (9.5f)));

    for (const auto& tick : tickMarks)
    {
        const auto tickY = yForProportion ((float) slider.valueToProportionOfLength ((double) tick.value));
        const bool isCentre = juce::approximatelyEqual (tick.value, 0.0f);

        g.setColour (isCentre ? textMuted : track.brighter (0.35f));
        g.fillRect (tickX, tickY - 0.5f, isCentre ? 9.0f : 6.0f, 1.0f);

        g.setColour (isCentre ? text : textMuted);
        g.drawText (tick.label,
                    juce::Rectangle<float> (tickX + tickLabelGap, tickY - 7.0f, 46.0f, 14.0f),
                    juce::Justification::centredLeft, false);
    }
}

//==============================================================================
void ShipStudiosLookAndFeel::drawToggleButton (juce::Graphics& g,
                                               juce::ToggleButton& button,
                                               bool shouldDrawButtonAsHighlighted,
                                               bool shouldDrawButtonAsDown)
{
    auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
    const auto radius = bounds.getHeight() * 0.5f;
    const bool on = button.getToggleState();

    auto fill = on ? accentDim : panel;

    if (shouldDrawButtonAsDown)
        fill = fill.darker (0.2f);
    else if (shouldDrawButtonAsHighlighted)
        fill = fill.brighter (0.12f);

    g.setColour (fill);
    g.fillRoundedRectangle (bounds, radius);

    g.setColour (on ? accentDim.brighter (0.35f) : track.brighter (0.25f));
    g.drawRoundedRectangle (bounds, radius, 1.0f);

    g.setColour (on ? background : textMuted);
    g.setFont (juce::Font (juce::FontOptions (11.5f).withStyle ("Bold")));
    g.drawText (button.getButtonText(), bounds, juce::Justification::centred, false);
}

//==============================================================================
void DisclosureButton::paintButton (juce::Graphics& g,
                                    bool shouldDrawButtonAsHighlighted, bool)
{
    const bool open = getToggleState();
    auto colour = ShipStudiosLookAndFeel::textMuted;

    if (shouldDrawButtonAsHighlighted)
        colour = ShipStudiosLookAndFeel::text;

    auto bounds = getLocalBounds().toFloat();

    g.setColour (colour);
    g.setFont (juce::Font (juce::FontOptions (10.5f).withStyle ("Bold")));
    g.drawText (open ? "LESS" : "ADVANCED",
                bounds.withTrimmedRight (16.0f), juce::Justification::centredRight, false);

    // Chevron points the way the panel will move.
    const auto cx = bounds.getRight() - 9.0f;
    const auto cy = bounds.getCentreY() + (open ? 2.0f : -2.0f);
    const auto dir = open ? -1.0f : 1.0f;

    juce::Path chevron;
    chevron.startNewSubPath (cx - 4.0f, cy);
    chevron.lineTo (cx, cy + 4.0f * dir);
    chevron.lineTo (cx + 4.0f, cy);

    g.strokePath (chevron, juce::PathStrokeType (1.6f, juce::PathStrokeType::curved,
                                                 juce::PathStrokeType::rounded));
}

//==============================================================================
void SegmentedButton::paintButton (juce::Graphics& g,
                                   bool shouldDrawButtonAsHighlighted, bool)
{
    auto bounds = getLocalBounds().toFloat().reduced (0.5f);
    const auto radius = bounds.getHeight() * 0.5f;
    const bool on = getToggleState();

    g.setColour (ShipStudiosLookAndFeel::panel);
    g.fillRoundedRectangle (bounds, radius);
    g.setColour (ShipStudiosLookAndFeel::track.brighter (0.25f));
    g.drawRoundedRectangle (bounds, radius, 1.0f);

    auto active = bounds.reduced (2.0f);
    active = on ? active.removeFromRight (active.getWidth() * 0.5f)
                : active.removeFromLeft  (active.getWidth() * 0.5f);

    auto fill = ShipStudiosLookAndFeel::accentDim;
    if (shouldDrawButtonAsHighlighted)
        fill = fill.brighter (0.15f);

    g.setColour (fill);
    g.fillRoundedRectangle (active, active.getHeight() * 0.5f);

    auto text = bounds.reduced (2.0f);
    const auto left = text.removeFromLeft (text.getWidth() * 0.5f);

    g.setFont (juce::Font (juce::FontOptions (10.5f).withStyle ("Bold")));
    g.setColour (on ? ShipStudiosLookAndFeel::textMuted : ShipStudiosLookAndFeel::background);
    g.drawText (labels[0], left, juce::Justification::centred, false);
    g.setColour (on ? ShipStudiosLookAndFeel::background : ShipStudiosLookAndFeel::textMuted);
    g.drawText (labels[1], text, juce::Justification::centred, false);
}


//==============================================================================
AnalyseControl::AnalyseControl()
{
    setMouseCursor (juce::MouseCursor::PointingHandCursor);
}

bool AnalyseControl::overRevert (juce::Point<int> p) const
{
    return showRevert && p.x > getWidth() - revertZoneWidth;
}

void AnalyseControl::setDisplay (const juce::String& text, bool revert, bool isBusy, bool isWarn)
{
    if (text == label && revert == showRevert && isBusy == busy && isWarn == warn)
        return;

    label = text;
    showRevert = revert;
    busy = isBusy;
    warn = isWarn;
    repaint();
}

void AnalyseControl::mouseMove (const juce::MouseEvent& e)
{
    if (const auto over = overRevert (e.getPosition()); over != hoverRevert)
    {
        hoverRevert = over;
        repaint();
    }
}

void AnalyseControl::mouseEnter (const juce::MouseEvent& e)
{
    hover = true;
    hoverRevert = overRevert (e.getPosition());
    repaint();
}

void AnalyseControl::mouseExit (const juce::MouseEvent&)
{
    hover = hoverRevert = false;
    repaint();
}

void AnalyseControl::mouseDown (const juce::MouseEvent& e)
{
    // Right-click is the AI option's home. Uploading audio should take a
    // deliberate detour, not sit one stray click away from ANALYSE.
    if (e.mods.isPopupMenu())
    {
        if (onMenu) onMenu();
        return;
    }

    if (busy)
        return;

    if (overRevert (e.getPosition()))
    {
        if (onRevert) onRevert();
    }
    else if (onAnalyse)
    {
        onAnalyse();
    }
}

void AnalyseControl::paint (juce::Graphics& g)
{
    using LNF = ShipStudiosLookAndFeel;

    auto bounds = getLocalBounds().toFloat().reduced (0.5f);
    const auto radius = bounds.getHeight() * 0.5f;

    const auto tint = warn      ? juce::Colour (0xffd08a5a)
                    : showRevert ? LNF::accent
                                 : LNF::textMuted;

    g.setColour (LNF::background.darker (busy ? 0.1f : 0.3f)
                                .interpolatedWith (tint, showRevert ? 0.14f : 0.0f));
    g.fillRoundedRectangle (bounds, radius);

    g.setColour (tint.withAlpha (hover && ! busy ? 0.95f : 0.55f));
    g.drawRoundedRectangle (bounds, radius, 1.0f);

    auto textArea = bounds;

    if (showRevert)
    {
        auto zone = textArea.removeFromRight ((float) revertZoneWidth);

        // Divider, so the glyph reads as its own target rather than as
        // decoration on the label.
        g.setColour (tint.withAlpha (0.35f));
        g.fillRect (zone.getX(), bounds.getY() + 5.0f, 1.0f, bounds.getHeight() - 10.0f);

        // A revert arrow: three-quarter arc, counter-clockwise, with a head.
        const auto c = zone.getCentre();
        constexpr float r = 5.2f;

        juce::Path arc;
        arc.addCentredArc (c.x, c.y, r, r, 0.0f,
                           juce::MathConstants<float>::pi * 0.35f,
                           juce::MathConstants<float>::pi * 1.95f, true);

        g.setColour (tint.withAlpha (hoverRevert ? 1.0f : 0.7f));
        g.strokePath (arc, juce::PathStrokeType (1.4f));

        juce::Path head;
        head.addTriangle (c.x - r - 2.6f, c.y - 1.0f,
                          c.x - r + 2.6f, c.y - 1.0f,
                          c.x - r,        c.y + 3.4f);
        g.fillPath (head);
    }

    g.setColour (busy ? LNF::textMuted : (showRevert || warn ? tint : LNF::text));
    g.setFont (juce::Font (juce::FontOptions (11.0f).withStyle ("Bold")));
    g.drawText (label, textArea, juce::Justification::centred, false);
}

//==============================================================================
void PowerButton::paintButton (juce::Graphics& g,
                               bool shouldDrawButtonAsHighlighted,
                               bool shouldDrawButtonAsDown)
{
    // Bound to bypass, drawn as power: lit means ACTIVE, i.e. NOT bypassed.
    const bool active = ! getToggleState();

    auto colour = active ? ShipStudiosLookAndFeel::accent
                         : ShipStudiosLookAndFeel::textMuted.withAlpha (0.55f);

    if (shouldDrawButtonAsDown)
        colour = colour.darker (0.3f);
    else if (shouldDrawButtonAsHighlighted)
        colour = colour.brighter (0.35f);

    const auto bounds = getLocalBounds().toFloat();
    const auto centre = bounds.getCentre();
    const auto radius = juce::jmin (bounds.getWidth(), bounds.getHeight()) * 0.30f;

    juce::Path symbol;

    // Ring with a gap at 12 o'clock. JUCE arc angles run clockwise from the top.
    symbol.addCentredArc (centre.x, centre.y, radius, radius, 0.0f,
                          juce::MathConstants<float>::pi * 0.26f,
                          juce::MathConstants<float>::pi * 1.74f,
                          true);

    // Stem down through the gap.
    symbol.startNewSubPath (centre.x, centre.y - radius * 1.32f);
    symbol.lineTo (centre.x, centre.y - radius * 0.10f);

    g.setColour (colour);
    g.strokePath (symbol, juce::PathStrokeType (1.9f,
                                                juce::PathStrokeType::curved,
                                                juce::PathStrokeType::rounded));
}

//==============================================================================
// Curve display
//==============================================================================
CurveDisplay::CurveDisplay (ShipStudiosGainProcessor& processorSource,
                            std::atomic<float>& distanceSource,
                            std::atomic<double>& sampleRateSource,
                            std::atomic<float>& extremeSource)
    : processorRef (processorSource),
      distanceParam (distanceSource),
      sampleRate (sampleRateSource),
      extremeParam (extremeSource)
{
    setInterceptsMouseClicks (false, false);
    startTimerHz (30);
}

void CurveDisplay::timerCallback()
{
    const auto current = distanceParam.load();
    const auto scale = extremeParam.load();
    const auto generation = processorRef.publishedGeneration.load (std::memory_order_relaxed);

    if (! juce::approximatelyEqual (current, lastDrawnDistance)
        || ! juce::approximatelyEqual (scale, lastDrawnScale)
        || generation != lastDrawnGeneration)
    {
        lastDrawnDistance = current;
        lastDrawnScale = scale;
        lastDrawnGeneration = generation;
        repaint();
    }
}

void CurveDisplay::paint (juce::Graphics& g)
{
    const auto outer = getLocalBounds().toFloat();

    g.setColour (ShipStudiosLookAndFeel::background.darker (0.3f));
    g.fillRoundedRectangle (outer, 3.0f);

    // Two reserved strips at the foot: the frequency scale, and above it the
    // band legend. The band names used to float ON the curve, where PROXIMITY
    // and ROOM sit close enough in x to collide with each other AND with the
    // line they annotate. A fixed row cannot collide with anything.
    auto bounds = outer.withTrimmedBottom (28.0f);
    const auto legendStrip = outer.withTrimmedBottom (14.0f)
                                  .withTop (outer.getBottom() - 28.0f);
    const auto axisStrip = outer.withTop (outer.getBottom() - 14.0f);

    const auto sr = sampleRate.load();
    const auto d = normaliseDistance (distanceParam.load());
    const auto extreme = extremeParam.load() > 0.5f;
    const auto scale = extreme ? extremeScale : 1.0f;

    const auto xForHz = [&bounds] (double hz)
    {
        const auto t = std::log (hz / loHz) / std::log (hiHz / loHz);
        return bounds.getX() + (float) t * bounds.getWidth();
    };

    float range = displayRangeDb;

    // By VALUE: a swap mid-paint would otherwise tear the markers off the curve.
    const auto profile = processorRef.getDisplayProfile();
    const auto& bands = profile.bands;

    std::array<juce::dsp::IIR::Coefficients<float>::Ptr, factoryBands.size()> coeffs;

    for (size_t i = 0; i < bands.size(); ++i)
        coeffs[i] = makeCoefficientsPtr (bands[i], d, sr, scale);

    // AUTO-RANGE. Fixed at +/-20 dB, a real +/-3.5 dB curve occupied 9% of the
    // plot height -- a flat squiggle pinned to the centreline inside a mostly
    // empty box. Snapping to the smallest scale that holds the curve fills the
    // space AND makes the shape legible; the label states which scale is in use.
    auto peakDb = 0.0f;

    for (int i = 0; i <= 96; ++i)
    {
        const auto hz = loHz * std::pow (hiHz / loHz, (double) i / 96.0);
        double m = 1.0;
        for (const auto& c : coeffs)
            m *= c->getMagnitudeForFrequency (hz, sr);

        peakDb = juce::jmax (peakDb, (float) std::abs (20.0 * std::log10 (juce::jmax (1.0e-9, m))));
    }

    range = displayRangeExtremeDb;

    for (const auto candidate : { 5.0f, 10.0f, 20.0f })
    {
        if (peakDb <= candidate * 0.85f) { range = candidate; break; }
    }

    const auto yForDb = [&bounds, &range] (float db)
    {
        const auto t = (db + range) / (2.0f * range);
        return bounds.getBottom() - juce::jlimit (0.0f, 1.0f, t) * bounds.getHeight();
    };

    // 5-7 kHz harshness guard. This repo hard-codes that band as the trap where
    // boosts turn brittle, so showing it makes the constraint visible rather
    // than folklore -- and lets you see the AIR shelf's skirt staying clear.
    {
        const auto lo = xForHz (5000.0);
        const auto hi = xForHz (7000.0);
        g.setColour (juce::Colour (0xffe0503c).withAlpha (0.07f));
        g.fillRect (lo, bounds.getY(), hi - lo, bounds.getHeight());

        // NAMED. An unexplained dark stripe on a graph is just a rendering
        // artefact to anyone who did not write it.
        g.setColour (juce::Colour (0xffe0503c).withAlpha (0.45f));
        g.setFont (juce::Font (juce::FontOptions (7.5f).withStyle ("Bold")));
        g.drawText ("HARSH", juce::Rectangle<float> (lo - 12.0f, bounds.getY() + 2.0f,
                                                     (hi - lo) + 24.0f, 10.0f),
                    juce::Justification::centred, false);
    }

    // Grid
    g.setColour (ShipStudiosLookAndFeel::track.withAlpha (0.7f));
    for (const auto hz : { 100.0, 1000.0, 10000.0 })
        g.fillRect (xForHz (hz), bounds.getY(), 1.0f, bounds.getHeight());

    for (const auto db : { -range * 0.5f, range * 0.5f })
        g.fillRect (bounds.getX(), yForDb (db), bounds.getWidth(), 1.0f);

    g.setColour (ShipStudiosLookAndFeel::track.brighter (0.4f));
    g.fillRect (bounds.getX(), yForDb (0.0f), bounds.getWidth(), 1.0f);

    // dB scale on the gridlines themselves, so a curve can be read off rather
    // than only compared against itself.
    g.setColour (ShipStudiosLookAndFeel::textMuted.withAlpha (0.65f));
    g.setFont (juce::Font (juce::FontOptions (8.5f)));

    for (const auto db : { range * 0.5f, -range * 0.5f })
        g.drawText ((db > 0.0f ? "+" : "") + juce::String ((int) db),
                    juce::Rectangle<float> (bounds.getRight() - 34.0f, yForDb (db) - 7.0f,
                                            30.0f, 14.0f),
                    juce::Justification::centredRight, false);

    // The curve. Coefficients are rebuilt here from the parameter -- never read
    // from the audio thread's live objects.
    juce::Path curve;
    const auto steps = juce::jmax (2, (int) bounds.getWidth());

    for (int i = 0; i <= steps; ++i)
    {
        const auto t = (double) i / (double) steps;
        const auto hz = loHz * std::pow (hiHz / loHz, t);

        double magnitude = 1.0;
        for (const auto& c : coeffs)
            magnitude *= c->getMagnitudeForFrequency (hz, sr);

        const auto db = (float) (20.0 * std::log10 (juce::jmax (1.0e-9, magnitude)));
        const auto px = bounds.getX() + (float) t * bounds.getWidth();

        if (i == 0)
            curve.startNewSubPath (px, yForDb (db));
        else
            curve.lineTo (px, yForDb (db));
    }

    // Shade between the curve and 0 dB, but clip the fill into two halves so a
    // BOOST and a CUT are different colours. One amber block spanning both, as
    // before, made a far setting read as a solid slab with no sense of which
    // way any part of it was moving.
    {
        juce::Path shaded (curve);
        shaded.lineTo (bounds.getRight(), yForDb (0.0f));
        shaded.lineTo (bounds.getX(), yForDb (0.0f));
        shaded.closeSubPath();

        const auto zeroLine = yForDb (0.0f);

        juce::Graphics::ScopedSaveState above (g);
        g.reduceClipRegion (bounds.withBottom (zeroLine).toNearestInt());
        g.setColour (ShipStudiosLookAndFeel::accent.withAlpha (0.20f));
        g.fillPath (shaded);
    }
    {
        juce::Path shaded (curve);
        shaded.lineTo (bounds.getRight(), yForDb (0.0f));
        shaded.lineTo (bounds.getX(), yForDb (0.0f));
        shaded.closeSubPath();

        juce::Graphics::ScopedSaveState below (g);
        g.reduceClipRegion (bounds.withTop (yForDb (0.0f)).toNearestInt());
        g.setColour (juce::Colour (0xff5a8fbf).withAlpha (0.20f));
        g.fillPath (shaded);
    }

    g.setColour (ShipStudiosLookAndFeel::accent);
    g.strokePath (curve, juce::PathStrokeType (1.6f));

    // Per-band markers stay ON the curve -- a dot cannot collide with anything.
    // Their NAMES and gains moved to the legend strip below.
    for (size_t i = 0; i < bands.size(); ++i)
    {
        const auto& band = bands[i];
        const auto gain = bandGainDb (band, d, scale);

        // Sit the marker on the COMPOSITE curve, not on the band's own gain --
        // the bands overlap, and the composite is what you actually hear.
        double magnitude = 1.0;
        for (const auto& c : coeffs)
            magnitude *= c->getMagnitudeForFrequency (band.freqHz, sr);

        const auto py = yForDb ((float) (20.0 * std::log10 (juce::jmax (1.0e-9, magnitude))));
        const auto active = std::abs (gain) > 0.1f;

        g.setColour (active ? ShipStudiosLookAndFeel::accent
                            : ShipStudiosLookAndFeel::textMuted.withAlpha (0.55f));
        g.fillEllipse (xForHz (band.freqHz) - 2.5f, py - 2.5f, 5.0f, 5.0f);
    }

    // --- legend --------------------------------------------------------------
    // Four equal cells, laid out in the bands' own left-to-right order, so the
    // strip reads as the same four things the dots mark.
    {
        auto strip = legendStrip.reduced (6.0f, 1.0f);
        const auto cellWidth = strip.getWidth() / (float) bands.size();

        for (size_t i = 0; i < bands.size(); ++i)
        {
            const auto gain = bandGainDb (bands[i], d, scale);
            const auto active = std::abs (gain) > 0.1f;
            auto cell = strip.removeFromLeft (cellWidth);

            g.setFont (juce::Font (juce::FontOptions (8.0f).withStyle ("Bold")));
            g.setColour (active ? ShipStudiosLookAndFeel::text
                                : ShipStudiosLookAndFeel::textMuted.withAlpha (0.5f));
            g.drawText (juce::String (bands[i].name).substring (0, 4),
                        cell.removeFromLeft (cell.getWidth() * 0.55f),
                        juce::Justification::centredRight, false);

            g.setFont (juce::Font (juce::FontOptions (8.5f)));
            g.setColour (active ? ShipStudiosLookAndFeel::accent
                                : ShipStudiosLookAndFeel::textMuted.withAlpha (0.35f));
            g.drawText (active ? (gain > 0.0f ? "+" : "") + juce::String (gain, 1)
                               : juce::String ("--"),
                        cell.reduced (3.0f, 0.0f), juce::Justification::centredLeft, false);
        }
    }

    // Level offset -- the distance cue that is NOT visible in the curve shape.
    const auto levelDb = distanceLevelDb (d, scale);

    if (std::abs (levelDb) > 0.05f)
    {
        // Kept, and NOT a duplicate of any band value: this is the level the
        // distance law applies, which the curve's shape does not show. Labelled
        // now, because an unlabelled "+3.5 dB" beside four band gains reads as
        // a fifth band gain.
        g.setColour (ShipStudiosLookAndFeel::textMuted);
        g.setFont (juce::Font (juce::FontOptions (8.5f).withStyle ("Bold")));
        g.drawText ("LEVEL " + juce::String (levelDb > 0.0f ? "+" : "")
                        + juce::String (levelDb, 1),
                    bounds.reduced (7.0f).removeFromTop (12.0f),
                    juce::Justification::topRight, false);
    }

    // Axis labels. The vertical range CHANGES with 2x (+/-20 -> +/-40 dB), so
    // without stating it a 2x curve looks identical to a 1x curve while meaning
    // something twice as extreme.
    g.setColour (ShipStudiosLookAndFeel::textMuted.withAlpha (0.8f));
    g.setFont (juce::Font (juce::FontOptions (9.0f)));
    g.drawText (juce::String (juce::CharPointer_UTF8 ("\xc2\xb1")) + juce::String ((int) range) + " dB",
                bounds.reduced (7.0f).removeFromTop (13.0f),
                juce::Justification::topLeft, false);

    for (const auto& [hz, text] : { std::pair<double, const char*> { 100.0, "100" },
                                    { 1000.0, "1k" },
                                    { 10000.0, "10k" } })
    {
        g.drawText (text,
                    juce::Rectangle<float> (xForHz (hz) - 18.0f, axisStrip.getY(), 36.0f, 13.0f),
                    juce::Justification::centred, false);
    }

    g.setColour (ShipStudiosLookAndFeel::track.brighter (0.5f));
    g.drawRoundedRectangle (outer.reduced (0.5f), 3.0f, 1.0f);
}

//==============================================================================
// Compressor display
//==============================================================================
CompressorDisplay::CompressorDisplay (std::atomic<float>& distanceSource,
                                      std::atomic<float>& gainReductionSource,
                                      std::atomic<float>& limiterSource,
                                      std::atomic<float>& clipSource,
                                      std::atomic<float>& levelSource,
                                      std::atomic<float>& extremeSource)
    : distanceParam (distanceSource),
      gainReduction (gainReductionSource),
      limiterReduction (limiterSource),
      clipReduction (clipSource),
      compLevel (levelSource),
      extremeParam (extremeSource)
{
    setInterceptsMouseClicks (false, false);
    startTimerHz (30);
}

void CompressorDisplay::timerCallback()
{
    const auto live = gainReduction.load();
    const auto liveLimiter = limiterReduction.load();

    // Fast attack / slow decay on the METERS only -- a meter that fell as fast
    // as the envelope would be unreadable.
    meterDb = live > meterDb ? live : meterDb + (live - meterDb) * 0.25f;
    limiterMeterDb = liveLimiter > limiterMeterDb
                         ? liveLimiter
                         : limiterMeterDb + (liveLimiter - limiterMeterDb) * 0.25f;

    const auto liveLevel = compLevel.load();
    levelSmoothedDb = liveLevel > levelSmoothedDb
                          ? liveLevel
                          : levelSmoothedDb + (liveLevel - levelSmoothedDb) * 0.2f;

    const auto liveClip = clipReduction.load();
    clipMeterDb = liveClip > clipMeterDb
                      ? liveClip
                      : clipMeterDb + (liveClip - clipMeterDb) * 0.25f;

    const auto current = distanceParam.load();

    if (! juce::approximatelyEqual (current, lastDrawnDistance)
        || meterDb > 0.01f || limiterMeterDb > 0.01f || clipMeterDb > 0.01f)
    {
        lastDrawnDistance = current;
        repaint();
    }
}

void CompressorDisplay::paint (juce::Graphics& g)
{
    auto bounds = getLocalBounds().toFloat();

    g.setColour (ShipStudiosLookAndFeel::background.darker (0.3f));
    g.fillRoundedRectangle (bounds, 3.0f);

    const auto d = normaliseDistance (distanceParam.load());
    const auto scale = extremeParam.load() > 0.5f ? extremeScale : 1.0f;
    const auto settings = compressorFor (d, scale);

    auto area = bounds.reduced (6.0f);

    // Cap the plot. Sizing it to the panel height meant a taller panel stole
    // width from the readouts -- the TRANS bars ended up ~30 px wide.
    const auto plotSide = juce::jmin (area.getHeight(), 118.0f);
    auto plot = area.removeFromLeft (plotSide).withHeight (plotSide);
    area.removeFromLeft (12.0f);

    // --- transfer curve ---------------------------------------------------
    const auto mapX = [&plot] (float db)
    {
        return plot.getX() + (1.0f - db / floorDb) * plot.getWidth();
    };
    const auto mapY = [&plot] (float db)
    {
        return plot.getBottom() - (1.0f - db / floorDb) * plot.getHeight();
    };

    g.setColour (ShipStudiosLookAndFeel::track.withAlpha (0.8f));
    g.drawRoundedRectangle (plot, 2.0f, 1.0f);

    // 1:1 reference
    g.setColour (ShipStudiosLookAndFeel::track.brighter (0.3f));
    g.drawLine (mapX (floorDb), mapY (floorDb), mapX (0.0f), mapY (0.0f), 1.0f);

    juce::Path transfer;
    constexpr int steps = 64;

    for (int i = 0; i <= steps; ++i)
    {
        const auto inDb = floorDb + (0.0f - floorDb) * ((float) i / (float) steps);
        // Compression only -- makeup is a separate adaptive stage and is not
        // part of this curve's shape.
        const auto outDb = inDb - compressorGainReductionDb (settings, inDb);
        const auto px = mapX (inDb);
        const auto py = mapY (juce::jlimit (floorDb, 6.0f, outDb));

        if (i == 0) transfer.startNewSubPath (px, py);
        else        transfer.lineTo (px, py);
    }

    g.setColour (ShipStudiosLookAndFeel::accent);
    g.strokePath (transfer, juce::PathStrokeType (1.6f));

    // Where you actually are on that curve. Without it the plot is a diagram of
    // a setting; with it, it is a display of what the audio is doing.
    if (levelSmoothedDb > floorDb)
    {
        const auto inDb = juce::jlimit (floorDb, 0.0f, levelSmoothedDb);
        const auto outDb = inDb - compressorGainReductionDb (settings, inDb);

        g.setColour (ShipStudiosLookAndFeel::text);
        g.fillEllipse (mapX (inDb) - 3.0f, mapY (juce::jlimit (floorDb, 6.0f, outDb)) - 3.0f,
                       6.0f, 6.0f);
    }

    // --- readouts + meters -------------------------------------------------
    // No "DYNAMICS" header: it labelled a panel that obviously shows dynamics.
    g.setColour (ShipStudiosLookAndFeel::text);
    g.setFont (juce::Font (juce::FontOptions (10.0f)));
    g.drawText ("COMP  " + juce::String (settings.ratio, 1) + ":1  "
                    + juce::String ((int) std::lround (settings.attackMs)) + " ms",
                area.removeFromTop (13.0f), juce::Justification::centredLeft, false);

    // The transient shaper drawn, not just named. It is the stage doing the most
    // distinctive work at the far end, and it had no visual at all.
    // No "TRANSIENT" header either: it labelled two rows already called ATK
    // and SUS.
    const auto trans = transientFor (d, scale);

    const auto drawBipolar = [&g] (juce::Rectangle<float> cell, const juce::String& tag,
                                   float valueDb, float fullScale)
    {
        g.setColour (ShipStudiosLookAndFeel::textMuted);
        g.setFont (juce::Font (juce::FontOptions (9.0f)));
        g.drawText (tag, cell.removeFromLeft (26.0f), juce::Justification::centredLeft, false);

        // Keep the number: the bar shows direction and relative size at a
        // glance, the value is what you quote when comparing settings.
        auto readout = cell.removeFromRight (34.0f);
        g.setColour (std::abs (valueDb) > 0.05f ? ShipStudiosLookAndFeel::text
                                                : ShipStudiosLookAndFeel::textMuted);
        g.setFont (juce::Font (juce::FontOptions (9.0f)));
        g.drawText ((valueDb > 0.0f ? "+" : "") + juce::String (valueDb, 1), readout,
                    juce::Justification::centredRight, false);

        auto bar = cell.reduced (3.0f, 4.0f);
        g.setColour (ShipStudiosLookAndFeel::track);
        g.fillRoundedRectangle (bar, 1.5f);

        const auto mid = bar.getCentreX();
        const auto extent = juce::jlimit (-1.0f, 1.0f, valueDb / fullScale)
                          * bar.getWidth() * 0.5f;

        if (std::abs (extent) > 0.5f)
        {
            // Boost amber, cut blue -- same language as the EQ curve fill.
            g.setColour (valueDb > 0.0f ? ShipStudiosLookAndFeel::accentDim.brighter (0.25f)
                                        : juce::Colour (0xff4b6d8c));
            g.fillRoundedRectangle ({ juce::jmin (mid, mid + extent), bar.getY(),
                                      std::abs (extent), bar.getHeight() }, 1.5f);
        }

        g.setColour (ShipStudiosLookAndFeel::textMuted.withAlpha (0.7f));
        g.fillRect (mid - 0.5f, bar.getY() - 1.0f, 1.0f, bar.getHeight() + 2.0f);
    };

    // Stacked rows rather than side-by-side: two labelled bipolar bars plus
    // their values do not fit across one narrow column legibly.
    area.removeFromTop (3.0f);
    drawBipolar (area.removeFromTop (15.0f), "ATK", trans.attackDb, 10.0f);
    drawBipolar (area.removeFromTop (15.0f), "SUS", trans.sustainDb, 10.0f);
    area.removeFromTop (5.0f);

    // ONE stacked bar, not three. Three separate meters all reading "-0.0 dB"
    // is a panel of zeros: it costs three rows to say nothing, and the thing
    // actually worth knowing -- how much total gain reduction is happening, and
    // which stage owns it -- was the one thing it did not show.
    g.setColour (ShipStudiosLookAndFeel::textMuted);
    g.setFont (juce::Font (juce::FontOptions (8.5f).withStyle ("Bold")));
    g.drawText ("GAIN REDUCTION", area.removeFromTop (12.0f),
                juce::Justification::centredLeft, false);

    {
        auto row = area.removeFromTop (16.0f);
        auto readout = row.removeFromRight (52.0f);
        auto bar = row.reduced (0.0f, 3.0f);

        g.setColour (ShipStudiosLookAndFeel::track);
        g.fillRoundedRectangle (bar, 2.0f);

        const auto total = meterDb + clipMeterDb + limiterMeterDb;

        struct Seg { float db; juce::Colour colour; const char* tag; };
        const Seg segs[] {
            { meterDb,        ShipStudiosLookAndFeel::accent,                         "CMP"  },
            { clipMeterDb,    ShipStudiosLookAndFeel::accent.withRotatedHue (0.10f),  "CLIP" },
            { limiterMeterDb, ShipStudiosLookAndFeel::accent.withRotatedHue (0.42f),  "LIM"  },
        };

        auto x = bar.getX();

        for (const auto& seg : segs)
        {
            const auto w = juce::jlimit (0.0f, 1.0f, seg.db / meterMaxDb) * bar.getWidth();

            if (w > 0.5f)
            {
                g.setColour (seg.colour);
                g.fillRoundedRectangle ({ x, bar.getY(), w, bar.getHeight() }, 2.0f);
                x += w;
            }
        }

        g.setColour (total > 0.05f ? ShipStudiosLookAndFeel::text
                                   : ShipStudiosLookAndFeel::textMuted);
        g.setFont (juce::Font (juce::FontOptions (9.5f)));
        g.drawText ("-" + juce::String (total, 1) + " dB", readout,
                    juce::Justification::centredRight, false);

        // A key, so the colours in the bar mean something. It replaces three
        // rows with one, and only the segments actually contributing are lit.
        auto key = area.removeFromTop (11.0f);
        g.setFont (juce::Font (juce::FontOptions (8.0f)));

        // Width computed ONCE. Re-reading key.getWidth() inside the loop divides
        // the SHRINKING remainder, so the cells come out 1/3, 2/9, 4/27 -- the
        // last label gets clipped to "LI".
        const auto cellWidth = key.getWidth() / 3.0f;

        for (const auto& seg : segs)
        {
            auto cell = key.removeFromLeft (cellWidth);
            const auto live = seg.db > 0.05f;

            g.setColour (live ? seg.colour : ShipStudiosLookAndFeel::track.brighter (0.2f));
            g.fillRoundedRectangle (cell.removeFromLeft (7.0f).reduced (0.0f, 3.0f), 1.0f);

            g.setColour (live ? ShipStudiosLookAndFeel::text
                              : ShipStudiosLookAndFeel::textMuted.withAlpha (0.7f));
            g.drawText (seg.tag, cell.reduced (3.0f, 0.0f),
                        juce::Justification::centredLeft, false);
        }
    }

    g.setColour (ShipStudiosLookAndFeel::track.brighter (0.5f));
    g.drawRoundedRectangle (bounds.reduced (0.5f), 3.0f, 1.0f);
}

//==============================================================================
// Meter fader
//==============================================================================
GainField::GainField (juce::String caption, std::atomic<float>& levelSource)
    : captionText (std::move (caption)), levelDb (levelSource)
{
    // LinearBarVertical is what makes a drag up/down change the value. Nothing
    // of its LOOK survives -- paint() is overridden outright.
    setSliderStyle (juce::Slider::LinearBarVertical);
    setTextBoxStyle (juce::Slider::NoTextBox, false, 0, 0);
    setDoubleClickReturnValue (true, 0.0);

    // BOTH of these are load-bearing on a control this small.
    //
    // snapsToMousePosition defaults TRUE, which makes a linear slider ABSOLUTE:
    // clicking anywhere in the field would jump the value to that spot, and a
    // 34 px-tall field spanning -24..+24 dB means one careless click is a 48 dB
    // move. Off, the drag becomes relative to where you grabbed it.
    //
    // Velocity mode then decouples resolution from the widget's SIZE. Without
    // it JUCE maps the full range across the slider's own 34 px, i.e. ~1.4 dB
    // per pixel -- unusable for a trim. With it, the range is a function of how
    // far you drag, so a small field is still a fine control.
    setSliderSnapsToMousePosition (false);
    setVelocityBasedMode (true);
    setVelocityModeParameters (1.0, 1, 0.0, false);
    setMouseCursor (juce::MouseCursor::UpDownResizeCursor);
    startTimerHz (30);
}

void GainField::timerCallback()
{
    const auto live = levelDb.load();

    // Fast attack, slow decay, plus a ~1 s peak hold. A meter that fell as fast
    // as the audio is unreadable.
    shownDb = live > shownDb ? live : shownDb + (live - shownDb) * 0.25f;

    if (live >= holdDb)
    {
        holdDb = live;
        holdCounter = 30;
    }
    else if (--holdCounter <= 0)
    {
        holdDb += (live - holdDb) * 0.12f;
    }

    repaint();
}

void GainField::paint (juce::Graphics& g)
{
    using LNF = ShipStudiosLookAndFeel;

    auto bounds = getLocalBounds().toFloat().reduced (0.5f);

    g.setColour (LNF::background.darker (0.25f));
    g.fillRoundedRectangle (bounds, 4.0f);

    // --- meter fill, BEHIND the number --------------------------------------
    // Deliberately not the accent colour: this is a passive readout, and if it
    // shared the distance fader's amber it would compete with the one control
    // that is the point of the plugin.
    const auto proportion = [] (float db)
    {
        return juce::jlimit (0.0f, 1.0f, (db - meterFloorDb) / (0.0f - meterFloorDb));
    };

    if (shownDb > meterFloorDb)
    {
        const auto w = bounds.getWidth() * proportion (shownDb);

        // Over 0 dBFS turns red -- the one meter state worth shouting about.
        g.setColour (shownDb > 0.0f ? juce::Colour (0xffe0503c).withAlpha (0.55f)
                                    : LNF::track.brighter (0.55f));
        g.fillRoundedRectangle (bounds.withWidth (juce::jmax (4.0f, w)), 4.0f);
    }

    if (holdDb > meterFloorDb)
    {
        const auto x = bounds.getX() + bounds.getWidth() * proportion (holdDb);
        g.setColour (LNF::textMuted.withAlpha (0.8f));
        g.fillRect (x - 0.5f, bounds.getY() + 3.0f, 1.0f, bounds.getHeight() - 6.0f);
    }

    // --- caption + value ----------------------------------------------------
    auto inner = bounds.reduced (8.0f, 0.0f);

    g.setColour (LNF::textMuted);
    g.setFont (juce::Font (juce::FontOptions (9.0f).withStyle ("Bold")));
    g.drawText (captionText, inner.removeFromLeft (26.0f),
                juce::Justification::centredLeft, false);

    const auto db = (float) getValue();
    g.setColour (std::abs (db) > 0.05f ? LNF::text : LNF::textMuted);
    g.setFont (juce::Font (juce::FontOptions (13.0f)));
    g.drawText ((db > 0.0f ? "+" : "") + juce::String (db, 1) + " dB", inner,
                juce::Justification::centredRight, false);

    g.setColour (LNF::track.brighter (isMouseOverOrDragging() ? 0.7f : 0.25f));
    g.drawRoundedRectangle (bounds, 4.0f, 1.0f);
}

//==============================================================================
// Editor
//==============================================================================
ShipStudiosGainEditor::ShipStudiosGainEditor (ShipStudiosGainProcessor& p)
    : AudioProcessorEditor (&p),
      processorRef (p),
      curveDisplay (p,
                    *p.apvts.getRawParameterValue (ShipStudiosGainProcessor::distanceParamID),
                    p.displaySampleRate,
                    *p.apvts.getRawParameterValue (ShipStudiosGainProcessor::extremeParamID)),
      compressorDisplay (*p.apvts.getRawParameterValue (ShipStudiosGainProcessor::distanceParamID),
                         p.displayGainReductionDb,
                         p.displayLimiterGrDb,
                         p.displayClipGrDb,
                         p.displayCompLevelDb,
                         *p.apvts.getRawParameterValue (ShipStudiosGainProcessor::extremeParamID)),
      inputSlider ("IN", p.displayInputLevelDb),
      outputSlider ("OUT", p.displayOutputLevelDb)
{
    lookAndFeelInstance.tickMarks = juce::Array<ShipStudiosLookAndFeel::Tick> {
        // All words, no bare numbers: the readout already carries the value, and
        // "CLOSE / +50 / 0 / -50 / FAR" mixed two vocabularies with no unit.
        ShipStudiosLookAndFeel::Tick {  100.0f, "CLOSE" },
        ShipStudiosLookAndFeel::Tick {    0.0f, "FLAT"  },
        ShipStudiosLookAndFeel::Tick { -100.0f, "FAR"   },
    };
    setLookAndFeel (&lookAndFeelInstance);

    addAndMakeVisible (curveDisplay);
    addAndMakeVisible (compressorDisplay);

    distanceSlider.setSliderStyle (juce::Slider::LinearVertical);
    distanceSlider.getProperties().set ("distanceScale", true);
    distanceSlider.setTextBoxStyle (juce::Slider::NoTextBox, false, 0, 0);
    distanceSlider.setDoubleClickReturnValue (true, 0.0);   // double-click -> flat
    distanceSlider.onValueChange = [this] { updateReadout(); };
    addAndMakeVisible (distanceSlider);

    readoutLabel.setJustificationType (juce::Justification::centred);
    readoutLabel.setFont (juce::Font (juce::FontOptions (13.0f)));
    readoutLabel.setEditable (false, false, false);
    addAndMakeVisible (readoutLabel);

    distanceCaption.setText ("DISTANCE", juce::dontSendNotification);
    distanceCaption.setFont (juce::Font (juce::FontOptions (10.0f).withStyle ("Bold")));
    distanceCaption.setColour (juce::Label::textColourId, ShipStudiosLookAndFeel::textMuted);
    distanceCaption.setJustificationType (juce::Justification::centred);
    addAndMakeVisible (distanceCaption);



    addAndMakeVisible (inputSlider);
    inputSlider.setTooltip ("Input trim -- drag up or down. Double-click for 0 dB.\n"
                            "The bar behind the number is the incoming level.");
    inputSlider.setColour (juce::Slider::trackColourId, juce::Colours::transparentBlack);

    addAndMakeVisible (outputSlider);
    outputSlider.setTooltip ("Output trim -- drag up or down. Double-click for 0 dB.\n"
                             "The bar behind the number is the outgoing level.");
    outputSlider.setColour (juce::Slider::trackColourId, juce::Colours::transparentBlack);

    ceilingSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    ceilingSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 56, 20);
    ceilingSlider.setTextValueSuffix (" dB");
    ceilingSlider.setDoubleClickReturnValue (true, -0.3);
    ceilingSlider.setColour (juce::Slider::textBoxTextColourId, ShipStudiosLookAndFeel::text);
    ceilingSlider.setColour (juce::Slider::textBoxBackgroundColourId,
                             juce::Colours::transparentBlack);
    ceilingSlider.setColour (juce::Slider::textBoxOutlineColourId,
                             juce::Colours::transparentBlack);
    addAndMakeVisible (ceilingSlider);

    ceilingLabel.setText ("CEILING", juce::dontSendNotification);
    ceilingLabel.setFont (juce::Font (juce::FontOptions (10.0f).withStyle ("Bold")));
    ceilingLabel.setColour (juce::Label::textColourId, ShipStudiosLookAndFeel::textMuted);
    ceilingLabel.setJustificationType (juce::Justification::centredLeft);
    addAndMakeVisible (ceilingLabel);

    clipModeButton.onStateChange = [this]
    {
        clipModeButton.setButtonText (clipModeButton.getToggleState() ? "HARD" : "SOFT");
    };
    addAndMakeVisible (clipModeButton);

    clipModeLabel.setText ("CLIP", juce::dontSendNotification);
    clipModeLabel.setFont (juce::Font (juce::FontOptions (9.5f).withStyle ("Bold")));
    clipModeLabel.setColour (juce::Label::textColourId, ShipStudiosLookAndFeel::textMuted);
    clipModeLabel.setJustificationType (juce::Justification::centredLeft);
    addAndMakeVisible (clipModeLabel);

    presetBox.setTooltip ("Factory presets. A trailing * means the settings no "
                          "longer match the named preset.");
    presetBox.setTextWhenNothingSelected ("PRESET");
    presetBox.setColour (juce::ComboBox::backgroundColourId, ShipStudiosLookAndFeel::panel);
    presetBox.setColour (juce::ComboBox::textColourId, ShipStudiosLookAndFeel::text);
    presetBox.setColour (juce::ComboBox::outlineColourId,
                         ShipStudiosLookAndFeel::track.brighter (0.25f));
    presetBox.setColour (juce::ComboBox::arrowColourId, ShipStudiosLookAndFeel::textMuted);

    for (int i = 0; i < processorRef.getNumPrograms(); ++i)
        presetBox.addItem (processorRef.getProgramName (i), i + 1);

    presetBox.setSelectedId (processorRef.getCurrentProgram() + 1,
                             juce::dontSendNotification);
    presetBox.onChange = [this]
    {
        const auto index = presetBox.getSelectedId() - 1;
        if (index >= 0)
            processorRef.setCurrentProgram (index);
    };
    addAndMakeVisible (presetBox);

    const auto styleTextButton = [] (juce::TextButton& b)
    {
        b.setColour (juce::TextButton::buttonColourId, ShipStudiosLookAndFeel::panel);
        b.setColour (juce::TextButton::buttonOnColourId, ShipStudiosLookAndFeel::accentDim);
        b.setColour (juce::TextButton::textColourOffId, ShipStudiosLookAndFeel::textMuted);
        b.setColour (juce::TextButton::textColourOnId, ShipStudiosLookAndFeel::background);
    };
    styleTextButton (abButton);
    styleTextButton (autoGainButton);
    styleTextButton (linkButton);

    // Instance link. The button is a plain toggle over the processor's link
    // flag; all the actual mirroring lives processor-side so it works with the
    // editor closed.
    linkButton.setClickingTogglesState (true);
    linkButton.setTooltip ("Link this instance into the global group: while lit, "
                           "changing any control here changes it on every other "
                           "linked instance (and theirs change this one). ANALYSE "
                           "stays per-instance. Unlit instances are unaffected.");
    linkButton.setToggleState (processorRef.isLinkEnabled(), juce::dontSendNotification);
    linkButton.onClick = [this]
    {
        processorRef.setLinkEnabled (linkButton.getToggleState());
    };
    addAndMakeVisible (linkButton);

    // Auto gain staging: one click arms an open-ended scan, a second click (or
    // the transport stopping) applies. The button lives under the INPUT fader
    // because that is the primary move -- it sets INPUT to calibrate the drive
    // and mirrors the change into OUTPUT, no hidden gain of its own.
    autoGainButton.setTooltip ("Auto gain staging: scans everything you play -- arm "
                               "it, play the whole region, then stop (or click "
                               "again). Sets INPUT so the source hits the level the "
                               "dynamics are calibrated for (-18 LUFS, peaks kept "
                               "under -3 dBFS) and sets OUTPUT to mirror the move, "
                               "so the track's level in the mix stays put.");
    autoGainButton.onClick = [this]
    {
        if (processorRef.isAutoGainLearning())
            processorRef.autoGainFinishEarly();
        else
            processorRef.autoGainStart();
    };
    addAndMakeVisible (autoGainButton);

    // A/B: stash the current settings in the slot you are leaving, then recall
    // the other. Both slots live on the PROCESSOR so they survive the window
    // being closed.
    abButton.onClick = [this]
    {
        // Alt-click copies instead of swapping. This absorbed the COPY button:
        // one chip for a feature most sessions never touch.
        if (juce::ModifierKeys::currentModifiers.isAltDown())
        {
            processorRef.storeAbSlot (1 - processorRef.currentAbSlot);
            return;
        }

        const auto from = processorRef.currentAbSlot;
        const auto to = 1 - from;

        processorRef.storeAbSlot (from);

        if (processorRef.hasAbSlot (to))
            processorRef.recallAbSlot (to);
        else
            processorRef.storeAbSlot (to);

        processorRef.currentAbSlot = to;
        abButton.setButtonText (to == 0 ? "A" : "B");
        updateReadout();
    };
    abButton.setTooltip ("A/B compare: stores the current settings and recalls the "
                         "other slot.\n\nAlt-click to COPY these settings into the "
                         "other slot instead of swapping.");
    addAndMakeVisible (abButton);

    extremeButton.setTooltip ("Doubles the EQ, compression and transient amounts -- "
                              "scales THIS fader, which is why it lives on its column");
    addAndMakeVisible (extremeButton);
    addAndMakeVisible (bypassButton);

    // --- adaptive EQ ------------------------------------------------------
    haveApiKey = ShipStudios::GeminiClient::hasApiKey();

    // Group entry point: on a linked instance this fires ANALYSE on every
    // linked peer too, each adapting to its own source.
    analyseControl.onAnalyse = [this] { processorRef.requestAnalysisGroup(); };
    analyseControl.onRevert  = [this] { processorRef.revertToFactory(); };
    analyseControl.onMenu    = [this] { showAnalyseMenu(); };
    analyseControl.setTooltip ("Listen to 10 seconds of what is playing and move the four "
                               "band frequencies onto this source's own features. "
                               "Start playback first.\n\n"
                               "Right-click for AI classification and the API key.");
    addAndMakeVisible (analyseControl);

    distanceAttachment = std::make_unique<SliderAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::distanceParamID, distanceSlider);

    outputAttachment = std::make_unique<SliderAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::outputParamID, outputSlider);

    inputAttachment = std::make_unique<SliderAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::inputParamID, inputSlider);

    ceilingAttachment = std::make_unique<SliderAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::ceilingParamID, ceilingSlider);

    clipModeAttachment = std::make_unique<ButtonAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::hardClipParamID, clipModeButton);

    extremeAttachment = std::make_unique<ButtonAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::extremeParamID, extremeButton);

    bypassAttachment = std::make_unique<ButtonAttachment> (
        processorRef.apvts, ShipStudiosGainProcessor::bypassParamID, bypassButton);


    bypassButton.onStateChange = [this] { refreshBypassLook(); };

    advancedButton.onClick = [this]
    {
        showAdvanced = advancedButton.getToggleState();
        processorRef.apvts.state.setProperty ("advancedView", showAdvanced, nullptr);
        applyViewMode();
    };
    addAndMakeVisible (advancedButton);

    showAdvanced = (bool) processorRef.apvts.state.getProperty ("advancedView", false);
    advancedButton.setToggleState (showAdvanced, juce::dontSendNotification);

    updateReadout();
    refreshPresetName();
    applyViewMode();
    startTimerHz (12);
}

void ShipStudiosGainEditor::timerCallback()
{
    refreshPresetName();
    refreshAnalysisStatus();

    // The LINK chip follows the processor, not just its own clicks -- a
    // session restore can flip membership underneath an open editor.
    if (linkButton.getToggleState() != processorRef.isLinkEnabled())
        linkButton.setToggleState (processorRef.isLinkEnabled(), juce::dontSendNotification);

    // While listening, the AUTO button becomes its own progress readout --
    // accent text is what says "armed" without spending a second lamp on it.
    const auto learning = processorRef.isAutoGainLearning();
    // Seconds heard, not a percentage: the scan is OPEN-ENDED, so a percentage
    // would have to invent a denominator and would sit at a made-up number
    // while the user plays.
    const auto percent = learning
        ? juce::jlimit (0, 999, (int) processorRef.autoGainSecondsHeard())
        : -1;

    if (learning != shownAutoLearning || percent != shownAutoPercent)
    {
        shownAutoLearning = learning;
        shownAutoPercent = percent;

        autoGainButton.setButtonText (learning ? juce::String (percent) + "s" : "AUTO");
        autoGainButton.setColour (juce::TextButton::textColourOffId,
                                  learning ? ShipStudiosLookAndFeel::accent
                                           : ShipStudiosLookAndFeel::textMuted);
    }
}

void ShipStudiosGainEditor::refreshAnalysisStatus()
{
    using State = ShipStudiosGainProcessor::AnalysisState;

    const auto state = processorRef.analysisState.load();

    juce::String text;
    auto revert = false, busy = false, warn = false;

    switch (state)
    {
        case State::capturing:
        {
            const auto cap = juce::jmax (1, processorRef.captureCapacity.load());
            const auto pct = juce::jlimit (0, 99,
                (int) (100.0f * (float) processorRef.captureProgress.load() / (float) cap));
            text = "LISTENING " + juce::String (pct) + "%";
            busy = true;
            break;
        }

        case State::analysing:   text = "ANALYSING";    busy = true; break;
        case State::classifying: text = "ASKING AI";    busy = true; break;
        case State::assisting:   text = "SUGGESTING";   busy = true; break;

        // A failure keeps the button live: the fix for the common one
        // ("NO SIGNAL") is to press play and try again, right here.
        case State::failed:      text = processorRef.getAnalysisShortLabel(); warn = true; break;

        case State::adapted:     text = processorRef.getAnalysisShortLabel(); revert = true; break;

        case State::idle:
        default:                 text = "ANALYSE"; break;
    }

    if (text != shownAnalysisStatus)
    {
        shownAnalysisStatus = text;

        // The full sentence lives in the tooltip, so the control stays one
        // short word without throwing the detail away.
        const auto detail = processorRef.getAnalysisLabel();
        analyseControl.setTooltip (
            detail.isNotEmpty()
                ? detail + "\n\nClick to re-analyse, or the arrow to go back to factory."
                : juce::String ("Listen to 10 seconds of what is playing and move the four "
                                "band frequencies onto this source's own features. "
                                "Start playback first.\n\n"
                                "Right-click for AI classification and the API key."));
    }

    analyseControl.setDisplay (text, revert, busy, warn);
}

void ShipStudiosGainEditor::showAnalyseMenu()
{
    auto* gemini = dynamic_cast<juce::AudioParameterBool*> (
        processorRef.apvts.getParameter (ShipStudiosGainProcessor::geminiParamID));

    if (gemini == nullptr)
        return;

    juce::PopupMenu menu;
    menu.addSectionHeader ("Adaptive EQ");

    // The wording is the consent. It has to say what actually happens at the
    // point of the click, not in a manual.
    menu.addItem (1, "Ask AI what the source is (uploads ~10 s of audio)",
                  true, gemini->get());
    menu.addSeparator();
    // The wording says where it LANDS. "Set my controls for me" with no hint of
    // what happens to the settings you already have is not a fair offer.
    menu.addItem (4, "Suggest settings for this audio \xe2\x86\x92 B slot", haveApiKey);
    menu.addSeparator();
    menu.addItem (2, haveApiKey ? "Change API key\xe2\x80\xa6" : "Set API key\xe2\x80\xa6");
    menu.addSeparator();
    menu.addItem (3, "Back to factory curve", processorRef.publishedGeneration.load() != 0);

    // SafePointer, not `this`: the menu outlives a closed editor (the host can
    // destroy the plugin window while it is up), and the async callback would
    // otherwise fire into freed memory. `gemini` is owned by the processor and
    // survives the editor, so guarding the editor is enough.
    juce::Component::SafePointer<ShipStudiosGainEditor> self (this);

    menu.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (analyseControl),
        [self, gemini] (int result)
        {
            if (self == nullptr)
                return;

            if (result == 1)
            {
                const auto turningOn = ! gemini->get();
                gemini->setValueNotifyingHost (turningOn ? 1.0f : 0.0f);

                if (turningOn && ! self->haveApiKey)
                    self->promptForApiKey (true);
            }
            else if (result == 2)
            {
                self->promptForApiKey (false);
            }
            else if (result == 3)
            {
                self->processorRef.revertToFactory();
            }
        });
}

void ShipStudiosGainEditor::promptForApiKey (bool cancelDisablesAi)
{
    auto* window = new juce::AlertWindow (
        "Gemini API key",
        "Pressing ANALYSE with AI on uploads about ten seconds of your audio to Google.\n\n"
        "The key is saved in PLAIN TEXT under ~/Library/Application Support/Ship Studios/. "
        "There is no keychain integration. Set GEMINI_API_KEY in the environment instead "
        "if that matters to you.",
        juce::MessageBoxIconType::NoIcon);

    window->addTextEditor ("key", {}, "API key");
    window->addButton ("Save", 1);
    window->addButton ("Cancel", 0);

    // The alert is a TOP-LEVEL window: it survives the editor being closed, so
    // the callback guards `this` with a SafePointer -- storing the key still
    // works editor-less (it is a static), but nothing touches editor state.
    // keyPrompt lets the destructor dismiss an orphaned dialog outright.
    keyPrompt = window;
    juce::Component::SafePointer<ShipStudiosGainEditor> self (this);

    window->enterModalState (true, juce::ModalCallbackFunction::create (
        [self, window, cancelDisablesAi] (int result)
        {
            const auto key = window->getTextEditorContents ("key").trim();

            if (result == 1 && key.isNotEmpty())
            {
                ShipStudios::GeminiClient::storeApiKey (key);

                if (self != nullptr)
                    self->haveApiKey = true;
            }
            else if (cancelDisablesAi && self != nullptr)
            {
                // Leaving AI on with no key would silently fall back to the
                // measured-only path and look like the switch did nothing.
                if (auto* gemini = dynamic_cast<juce::AudioParameterBool*> (
                        self->processorRef.apvts.getParameter (ShipStudiosGainProcessor::geminiParamID)))
                    gemini->setValueNotifyingHost (0.0f);
            }

            delete window;
        }), false);
}

void ShipStudiosGainEditor::refreshPresetName()
{
    const auto index = processorRef.getCurrentProgram();
    const auto modified = ! processorRef.matchesProgram (index);

    if (index == shownPreset && modified == shownModified)
        return;

    shownPreset = index;
    shownModified = modified;

    // A preset menu that keeps reading "Flat" while the fader sits at FAR 89 is
    // simply lying. Once anything is touched, clear the selection and show the
    // name greyed with an asterisk -- it says where you started from without
    // claiming that is where you are.
    if (modified)
    {
        presetBox.setTextWhenNothingSelected (processorRef.getProgramName (index) + " *");
        presetBox.setSelectedId (0, juce::dontSendNotification);
    }
    else
    {
        presetBox.setSelectedId (index + 1, juce::dontSendNotification);
    }
}

//==============================================================================
void ShipStudiosGainEditor::applyViewMode()
{
    for (auto* c : { (juce::Component*) &compressorDisplay,
                     (juce::Component*) &ceilingSlider, (juce::Component*) &ceilingLabel,
                     (juce::Component*) &clipModeButton, (juce::Component*) &clipModeLabel })
        c->setVisible (showAdvanced);

    setSize (editorWidth, showAdvanced ? advancedHeight : simpleHeight);
    resized();
}

ShipStudiosGainEditor::~ShipStudiosGainEditor()
{
    // Dismiss an open key prompt rather than orphan it: exitModalState fires
    // its callback (self is null by then -- guarded), which deletes the window.
    if (keyPrompt != nullptr)
        keyPrompt->exitModalState (0);

    setLookAndFeel (nullptr);
}

void ShipStudiosGainEditor::updateReadout()
{
    const auto value = distanceSlider.getValue();

    if (std::abs (value) < 0.5)
    {
        readoutLabel.setText ("FLAT", juce::dontSendNotification);
        readoutLabel.setColour (juce::Label::textColourId, ShipStudiosLookAndFeel::text);
        distanceSlider.setTooltip ("Reference distance -- the plugin is transparent here");
        return;
    }

    const auto word = value > 0.0 ? "CLOSE " : "FAR ";
    readoutLabel.setText (word + juce::String (std::abs (value), 0),
                          juce::dontSendNotification);
    readoutLabel.setColour (juce::Label::textColourId, ShipStudiosLookAndFeel::accent);

    // "100" on its own means nothing. The level law IS a distance law -- 6 dB
    // per doubling -- so the fader position converts straight back into the
    // physical quantity it is modelling. That conversion moved to the TOOLTIP:
    // it is worth having, but not worth a permanent second line under a number
    // the fader's own scale already labels.
    const auto scale = processorRef.apvts
                           .getRawParameterValue (ShipStudiosGainProcessor::extremeParamID)
                           ->load() > 0.5f ? extremeScale : 1.0f;
    const auto levelDb = distanceLevelDb (normaliseDistance ((float) value), scale);
    const auto doublings = -levelDb / dbPerDoubling;
    const auto ratio = std::pow (2.0f, doublings);

    distanceSlider.setTooltip (juce::String (ratio, ratio < 1.0f ? 2 : 1)
                                   + " x distance   "
                                   + (levelDb > 0.0f ? "+" : "")
                                   + juce::String (levelDb, 1) + " dB");
}

void ShipStudiosGainEditor::refreshBypassLook()
{
    repaint();
}

//==============================================================================
void ShipStudiosGainEditor::paint (juce::Graphics& g)
{
    // Background: a slight top-down lift keeps the panel from reading flat.
    g.setGradientFill (juce::ColourGradient (
        ShipStudiosLookAndFeel::panel,      0.0f, 0.0f,
        ShipStudiosLookAndFeel::background, 0.0f, (float) getHeight(),
        false));
    g.fillAll();

    // ONE header row: title left, preset centre, power right. Two stacked rows
    // read as two separate headers and cost 28 px to say so.
    g.setColour (ShipStudiosLookAndFeel::text);
    g.setFont (juce::Font (juce::FontOptions (15.0f)));
    g.drawText ("Distance", getLocalBounds().removeFromTop (headerHeight).withTrimmedLeft (22),
                juce::Justification::centredLeft, false);

    g.setColour (ShipStudiosLookAndFeel::track);
    g.fillRect (22, headerHeight, getWidth() - 44, 1);

    // The fader scale is drawn by the LookAndFeel alongside the fader, not here
    // -- it needs the thumb's travel range to stay aligned with the cap.
}

void ShipStudiosGainEditor::paintOverChildren (juce::Graphics& g)
{
    if (! bypassButton.getToggleState())
        return;

    // Bypassed: a 30 px icon changing colour is easy to miss. Veiling the whole
    // panel makes the state unmissable at a glance.
    g.setColour (ShipStudiosLookAndFeel::background.withAlpha (0.62f));
    g.fillRect (getLocalBounds().withTrimmedTop (46));

    // Centred on the panel with its own backing, so it cannot land on top of a
    // control the way a fixed top offset did (it collided with COPY).
    const auto badge = getLocalBounds().withSizeKeepingCentre (150, 32).toFloat();

    g.setColour (ShipStudiosLookAndFeel::background.withAlpha (0.92f));
    g.fillRoundedRectangle (badge, badge.getHeight() * 0.5f);
    g.setColour (ShipStudiosLookAndFeel::textMuted.withAlpha (0.6f));
    g.drawRoundedRectangle (badge.reduced (0.5f), badge.getHeight() * 0.5f, 1.0f);

    g.setColour (ShipStudiosLookAndFeel::textMuted);
    g.setFont (juce::Font (juce::FontOptions (13.0f).withStyle ("Bold")));
    g.drawText ("BYPASSED", badge, juce::Justification::centred, false);
}

void ShipStudiosGainEditor::resized()
{
    auto area = getLocalBounds();

    {
        auto header = area.removeFromTop (headerHeight);
        bypassButton.setBounds (header.removeFromRight (46).withSizeKeepingCentre (26, 26));
        abButton.setBounds (header.removeFromRight (38).reduced (0, 8));
        header.removeFromRight (5);
        linkButton.setBounds (header.removeFromRight (52).reduced (0, 8));
        header.removeFromRight (5);
        presetBox.setBounds (header.removeFromRight (150).reduced (0, 6));
        // The title is painted, not a component; it takes what is left.
    }

    area.removeFromTop (8);
    area.removeFromBottom (6);

    // Gain staging as ONE row of drag numbers, signal flowing left to right.
    // Two full-height channel columns cost 164 px of width to hold two trims
    // that get set once, and framed them as peers of the distance fader.
    {
        auto row = area.removeFromTop (GainField::preferredHeight).reduced (14, 0);
        const auto half = (row.getWidth() - 52) / 2;

        inputSlider.setBounds (row.removeFromLeft (half));
        row.removeFromLeft (6);
        autoGainButton.setBounds (row.removeFromLeft (40).reduced (0, 5));
        row.removeFromLeft (6);
        outputSlider.setBounds (row.removeFromRight (half));

        area.removeFromTop (8);
    }

    // The distance fader owns a full-height column of its own -- and now that
    // the channel strips are gone it is the ONLY fader on the panel, which is
    // the point.
    {
        auto strip = area.removeFromRight (distanceColumnWidth);
        distanceCaption.setBounds (strip.removeFromTop (14));
        strip.removeFromTop (4);

        // 2x sits at the HEAD of this column and the value at its FOOT, giving
        // the distance fader the same anatomy as INPUT and OUTPUT: caption,
        // control, number.
        extremeButton.setBounds (strip.removeFromTop (22).withSizeKeepingCentre (52, 22));
        strip.removeFromTop (4);
        readoutLabel.setBounds (strip.removeFromBottom (20));
        strip.removeFromBottom (2);

        using LNF = ShipStudiosLookAndFeel;
        constexpr auto inkLeft  = LNF::grooveColumnWidth * 0.5f - LNF::capWidth * 0.5f;
        constexpr auto inkRight = LNF::grooveColumnWidth + LNF::tickLabelGap
                                + LNF::tickLabelInkWidth;
        const auto inkCentre = (int) ((inkLeft + inkRight) * 0.5f);

        distanceSlider.setBounds (strip.reduced (0, 4)
                                       .withWidth (170)
                                       .withX (strip.getCentreX() - inkCentre));
    }

    // Centre stack, allocated BOTTOM-UP so the displays absorb the slack.
    // Previously everything was a fixed height and the leftover -- about 40% of
    // the column in the simple view -- became two dead gaps with a readout
    // floating in between.
    advancedButton.setBounds (area.removeFromBottom (34).withSizeKeepingCentre (150, 22));

    if (showAdvanced)
    {
        const auto row = [&area] (juce::Component& label, juce::Component& control)
        {
            auto r = area.removeFromBottom (32).reduced (14, 3);
            label.setBounds (r.removeFromLeft (56));
            control.setBounds (r);
        };

        row (clipModeLabel, clipModeButton);
        row (ceilingLabel, ceilingSlider);
        area.removeFromBottom (4);
    }

    // Whatever is left is display space. The dynamics panel keeps a fixed
    // height; the EQ curve -- the only display in the simple view -- takes the
    // rest instead of being pinned at 156 px inside an 800 px column.
    if (showAdvanced)
    {
        compressorDisplay.setBounds (area.removeFromBottom (150).reduced (10, 4));
        area.removeFromBottom (2);
    }

    // ONE control, directly under the curve in both views: it changes what that
    // curve IS, so anywhere else it would read as another trim.
    {
        auto strip = area.removeFromBottom (32).reduced (10, 0);
        analyseControl.setBounds (strip.removeFromTop (24).withSizeKeepingCentre (190, 24));
    }

    curveDisplay.setBounds (area.reduced (10, 4));
}
