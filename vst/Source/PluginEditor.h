#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

#include "PluginProcessor.h"
#include "DistanceCurve.h"

//==============================================================================
/**
    Custom drawing for the fader and the bypass toggle.

    Kept separate from the editor so the palette lives in one place -- restyling
    the plugin means editing the colours below, not hunting through paint code.
*/
class ShipStudiosLookAndFeel final : public juce::LookAndFeel_V4
{
public:
    ShipStudiosLookAndFeel();

    void drawLinearSlider (juce::Graphics&, int x, int y, int width, int height,
                           float sliderPos, float minSliderPos, float maxSliderPos,
                           juce::Slider::SliderStyle, juce::Slider&) override;

    void drawToggleButton (juce::Graphics&, juce::ToggleButton&,
                           bool shouldDrawButtonAsHighlighted,
                           bool shouldDrawButtonAsDown) override;

    // JUCE insets a linear slider's thumb travel by this radius, then maps
    // values into the inset range. Pinning it to a constant is what lets the
    // groove and the scale be positioned from the same arithmetic JUCE uses for
    // the thumb -- otherwise they drift apart.
    //
    // Do NOT reach for the minSliderPos/maxSliderPos passed to
    // drawLinearSlider: on a single-value slider JUCE sets both equal to
    // sliderPos, so they describe a point, not a range.
    int getSliderThumbRadius (juce::Slider&) override { return thumbRadius; }

    static constexpr int thumbRadius = 10;

    /** A labelled mark on the fader scale. `value` is in the slider's own units. */
    struct Tick
    {
        float value;
        juce::String label;
    };

    // Marks to draw alongside a vertical fader, top (max) to bottom (min).
    // Drawn by drawLinearSlider rather than by the editor so they share the
    // thumb's travel range.
    juce::Array<Tick> tickMarks;

    // Fader geometry. Shared with the editor's resized(), which needs it to
    // centre the visible ink rather than the slider's (much wider) bounds.
    static constexpr float grooveColumnWidth = 68.0f;   // groove column; ticks sit right of it
    static constexpr float capWidth          = 38.0f;   // fader cap
    static constexpr float capHeight         = 17.0f;
    static constexpr float tickLabelGap      = 14.0f;   // tick mark -> label
    static constexpr float tickLabelInkWidth = 42.0f;   // rendered width of "CLOSE"

    // Palette. Warm amber on near-black -- deliberately not JUCE's stock
    // grey/blue, so the plugin reads as ours at a glance in a plugin list.
    static const juce::Colour background;
    static const juce::Colour panel;
    static const juce::Colour accent;
    static const juce::Colour text;
    static const juce::Colour textMuted;
    static const juce::Colour track;
    static const juce::Colour cap;

    /** A LIT-but-not-shouting colour for secondary state -- an engaged trim, a
        selected segment, an informational bar.

        Accent is reserved for the distance fader and its curve. With fifteen
        amber elements on the panel nothing read as primary, and a display where
        everything is emphasised feels crowded even when it is not. */
    static const juce::Colour accentDim;
};

//==============================================================================
/**
    Live plot of the distance EQ curve.

    Recomputes coefficients from the PARAMETER value into its own scratch
    objects. It must never read the audio thread's live Coefficients -- those are
    not thread-safe, and JUCE documents coefficient thread-safety as the caller's
    problem. Reading the parameter also means the curve tracks the fader even
    when no audio is running.
*/
class CurveDisplay final : public juce::Component,
                           private juce::Timer
{
public:
    CurveDisplay (ShipStudiosGainProcessor& processorSource,
                  std::atomic<float>& distanceSource,
                  std::atomic<double>& sampleRateSource,
                  std::atomic<float>& extremeSource);

    void paint (juce::Graphics&) override;

private:
    void timerCallback() override;

    // The processor, for the ADAPTED band table: the display must draw the
    // curve the audio thread is actually running, not the factory one it
    // started from -- otherwise ANALYSE changes the sound and nothing on screen
    // moves.
    ShipStudiosGainProcessor& processorRef;
    std::atomic<float>&  distanceParam;
    std::atomic<double>& sampleRate;
    std::atomic<float>&  extremeParam;
    float lastDrawnDistance = std::numeric_limits<float>::lowest();
    float lastDrawnScale = 0.0f;
    juce::uint32 lastDrawnGeneration = 0xffffffffu;

    // Vertical half-range, per scale. Must clear the largest endpoint in
    // factoryBands (-18 dB air shelf, -36 dB at 2x) or the curve draws
    // off the graph.
    static constexpr float displayRangeDb = 20.0f;
    static constexpr float displayRangeExtremeDb = 40.0f;
    static constexpr double loHz = 20.0;
    static constexpr double hiHz = 20000.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (CurveDisplay)
};

//==============================================================================
/**
    Compressor transfer curve + live gain-reduction meter.

    The curve is the static one, drawn from the SAME compressorGainReductionDb()
    the audio thread uses, so it cannot describe a compressor other than the one
    running. The meter is the live envelope, published per block by the processor.
*/
class CompressorDisplay final : public juce::Component,
                                private juce::Timer
{
public:
    CompressorDisplay (std::atomic<float>& distanceSource,
                       std::atomic<float>& gainReductionSource,
                       std::atomic<float>& limiterSource,
                       std::atomic<float>& clipSource,
                       std::atomic<float>& levelSource,
                       std::atomic<float>& extremeSource);

    void paint (juce::Graphics&) override;

private:
    void timerCallback() override;

    std::atomic<float>& distanceParam;
    std::atomic<float>& gainReduction;
    std::atomic<float>& limiterReduction;
    std::atomic<float>& clipReduction;
    std::atomic<float>& compLevel;
    std::atomic<float>& extremeParam;

    float lastDrawnDistance = std::numeric_limits<float>::lowest();
    float meterDb = 0.0f;          // decays toward the live value, so it reads
    float limiterMeterDb = 0.0f;
    float clipMeterDb = 0.0f;
    float levelSmoothedDb = -100.0f;

    static constexpr float floorDb  = -54.0f;   // transfer curve x/y range
    static constexpr float meterMaxDb = 12.0f;  // full scale of the GR meter

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (CompressorDisplay)
};

//==============================================================================
/**
    Minimal power symbol (IEC 60417-5009): a broken ring with a stem.

    NOTE THE INVERSION. This is bound to the BYPASS parameter, but a power button
    must read lit-when-ACTIVE -- a lamp that comes on to tell you the plugin is
    switched off would be backwards. So the drawing uses `! getToggleState()`
    while the attachment stays bound to bypass as normal.
*/
/**
    A disclosure control, deliberately NOT styled like the processing toggles.
    ADVANCED previously used the same lit pill as 2X, which made a view switch
    compete visually with things that change the sound.
*/
class DisclosureButton final : public juce::ToggleButton
{
public:
    DisclosureButton() : juce::ToggleButton ("ADVANCED") {}

    void paintButton (juce::Graphics&, bool, bool) override;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DisclosureButton)
};

//==============================================================================
/**
    Two named segments, one lit. A single toggle showing only the ACTIVE mode
    forces the reader to know what the other state would be; showing both means
    the control explains itself.
*/
class SegmentedButton final : public juce::ToggleButton
{
public:
    SegmentedButton (juce::String offLabel, juce::String onLabel)
        : juce::ToggleButton ("Clip Mode"),
          labels { std::move (offLabel), std::move (onLabel) } {}

    void paintButton (juce::Graphics&, bool, bool) override;

private:
    juce::String labels[2];

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (SegmentedButton)
};

//==============================================================================
/**
    The whole adaptive-EQ feature as ONE control.

    It replaced four: ANALYSE, an AI toggle, FACTORY and a status line -- four
    rows of chrome for something you press once. FACTORY in particular had
    nothing to revert to until an analysis had run, so it spent most of its life
    as a live button that did nothing.

    So the button carries its own state instead: it reads ANALYSE, then
    LISTENING 40%, then DRUMS with a revert glyph. The glyph only exists once
    there IS something to revert. The AI option -- which uploads audio, and so
    must be a deliberate act -- lives in the right-click menu.
*/
class AnalyseControl final : public juce::Component,
                            public juce::SettableTooltipClient
{
public:
    AnalyseControl();

    void paint (juce::Graphics&) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseMove (const juce::MouseEvent&) override;
    void mouseEnter (const juce::MouseEvent&) override;
    void mouseExit (const juce::MouseEvent&) override;

    /** @param busy  no action available; the plugin is already working
        @param warn  the last attempt failed -- shown in the warning colour */
    void setDisplay (const juce::String& text, bool showRevert, bool busy, bool warn);

    std::function<void()> onAnalyse, onRevert, onMenu;

private:
    bool overRevert (juce::Point<int>) const;

    static constexpr int revertZoneWidth = 30;

    juce::String label { "ANALYSE" };
    bool showRevert = false;
    bool busy = false;
    bool warn = false;
    bool hover = false;
    bool hoverRevert = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (AnalyseControl)
};

//==============================================================================
class PowerButton final : public juce::ToggleButton
{
public:
    PowerButton() : juce::ToggleButton ("Bypass") {}

    void paintButton (juce::Graphics&, bool shouldDrawButtonAsHighlighted,
                      bool shouldDrawButtonAsDown) override;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PowerButton)
};

//==============================================================================
/**
    A gain trim as a NUMBER you drag, with its meter behind it.

    It replaced a full-height channel fader per side. Two 82 px columns running
    the whole height of the window is a lot of real estate for two trims that
    are set once and then left -- and it framed them as peers of the distance
    fader, which is the only control here that is actually the point.

    Drag behaviour comes from Slider's own LinearBarVertical style (drag up to
    raise, down to lower); everything drawn is ours. Double-click returns to
    0 dB, which is what a trim should do and is more useful here than typing.

    The meter did NOT get dropped in the shrink: it is the fill behind the
    number, so gain staging stays visible at a glance. Losing it would have made
    this a smaller control that tells you less, rather than the same information
    in less space.
*/
class GainField final : public juce::Slider,
                        private juce::Timer
{
public:
    GainField (juce::String caption, std::atomic<float>& levelSource);

    void paint (juce::Graphics&) override;

    static constexpr float meterFloorDb = -48.0f;
    static constexpr int   preferredHeight = 34;

private:
    void timerCallback() override;

    juce::String captionText;
    std::atomic<float>& levelDb;
    float shownDb = -100.0f;
    float holdDb = -100.0f;
    int holdCounter = 0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (GainField)
};

//==============================================================================
/**
    Two views over the same processor.

    SIMPLE (default) shows the one thing this plugin is actually about: the
    distance fader, its curve, its readout, and 2x -- which stays visible because
    it is a character choice, not a trim. Everything else (the dynamics display
    and the input/output/clip/ceiling trims) is hidden behind ADVANCED. Six controls on the front panel obscured the fact that this is a
    one-fader idea.

    The curve display stays in the simple view deliberately: it is not something
    you can modify, and it is what makes an abstract "distance" value legible.

    The fader carries no text box of its own: the readout is a separate label,
    which keeps the slider's bounds equal to the fader track plus its scale.
*/
class ShipStudiosGainEditor final : public juce::AudioProcessorEditor,
                                    private juce::Timer
{
public:
    explicit ShipStudiosGainEditor (ShipStudiosGainProcessor&);
    ~ShipStudiosGainEditor() override;

    void paint (juce::Graphics&) override;
    void paintOverChildren (juce::Graphics&) override;
    void resized() override;

private:
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;

    void updateReadout();
    void applyViewMode();

    /** UI state, not a parameter -- but stored in the APVTS ValueTree so it
        persists with the session and with presets, like a real plugin's panel
        state rather than resetting every time the window reopens. */
    bool showAdvanced = false;

    static constexpr int editorWidth    = 520;
    static constexpr int simpleHeight   = 452;
    static constexpr int advancedHeight = 618;

    // The distance fader gets its own full-height column so it reads as the
    // product rather than as a control tucked between two panels. Wide enough
    // for the groove column plus its CLOSE/FLAT/FAR scale.
    static constexpr int distanceColumnWidth = 136;

    // Header: one title line. "SHIP STUDIOS" above it duplicated the name the
    // host already shows in its own plugin header.
    static constexpr int headerHeight = 36;

    // Declared first so it outlives the components that point at it --
    // members are destroyed in reverse declaration order.
    ShipStudiosLookAndFeel lookAndFeelInstance;

    ShipStudiosGainProcessor& processorRef;

    CurveDisplay curveDisplay;
    CompressorDisplay compressorDisplay;

    juce::TooltipWindow tooltips { nullptr, 500 };
    juce::ComboBox presetBox;
    // ONE chip, not two. COPY was a second button for the rarest action on the
    // panel; alt-click does it, and the tooltip says so.
    juce::TextButton abButton { "A" };

    // Instance link: lit = this instance mirrors, and is mirrored by, every
    // other lit instance. A toggle-styled chip in the header because it is
    // session plumbing, not a sound control.
    juce::TextButton linkButton { "LINK" };

    juce::Slider distanceSlider;
    juce::Label  distanceCaption;
    // The distance value now sits at the FOOT of the distance column, where
    // INPUT and OUTPUT put theirs -- three faders, one anatomy. The old centre
    // block (48 pt "FLAT" + a "reference distance" caption) said the same thing
    // the fader's own FLAT tick already said, twice.
    juce::Label  readoutLabel;
    GainField    inputSlider;
    juce::TextButton autoGainButton { "AUTO" };
    GainField    outputSlider;
    juce::Slider ceilingSlider;
    juce::Label  ceilingLabel;
    SegmentedButton clipModeButton { "SOFT", "HARD" };
    juce::Label  clipModeLabel;
    // Lives at the head of the DISTANCE column: it scales that fader and
    // nothing else. Floating alone mid-panel it read as a global mode.
    juce::ToggleButton extremeButton { "2X" };

    AnalyseControl analyseControl;
    PowerButton bypassButton;
    DisclosureButton advancedButton;

    std::unique_ptr<SliderAttachment> distanceAttachment;
    std::unique_ptr<SliderAttachment> inputAttachment;
    std::unique_ptr<SliderAttachment> outputAttachment;
    std::unique_ptr<SliderAttachment> ceilingAttachment;
    std::unique_ptr<ButtonAttachment> clipModeAttachment;
    std::unique_ptr<ButtonAttachment> extremeAttachment;
    std::unique_ptr<ButtonAttachment> bypassAttachment;

    void refreshAnalysisStatus();
    void showAnalyseMenu();
    void promptForApiKey (bool cancelDisablesAi);
    juce::String shownAnalysisStatus;

    // The API-key dialog is a TOP-LEVEL window that outlives a closed editor.
    // Held as a SafePointer so the destructor can dismiss it instead of
    // leaving an orphan; its callback guards the editor the same way.
    juce::Component::SafePointer<juce::AlertWindow> keyPrompt;

    // Looked up ONCE. hasApiKey() opens a PropertiesFile, and the status
    // refresh runs at 12 Hz -- polling it would be a disk read per frame for a
    // string that only changes when the user types a key in.
    bool haveApiKey = false;

    void refreshBypassLook();
    void timerCallback() override;
    void refreshPresetName();

    int shownPreset = -1;
    bool shownModified = false;

    // Last auto-gain state pushed into the AUTO button, so the 12 Hz timer
    // only touches the component when something actually changed.
    bool shownAutoLearning = false;
    int  shownAutoPercent = -1;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ShipStudiosGainEditor)
};
