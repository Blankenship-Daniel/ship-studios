#include "PluginEditor.h"

namespace
{
constexpr int editorWidth  = 360;
constexpr int editorHeight = 220;
constexpr int margin       = 20;
}

//==============================================================================
ShipStudiosMcpEditor::ShipStudiosMcpEditor (ShipStudiosMcpProcessor& p)
    : AudioProcessorEditor (&p), processorRef (p)
{
    gainLabel.setText ("GAIN", juce::dontSendNotification);
    gainLabel.setJustificationType (juce::Justification::centred);
    addAndMakeVisible (gainLabel);

    gainSlider.setSliderStyle (juce::Slider::RotaryHorizontalVerticalDrag);
    gainSlider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 80, 20);
    gainSlider.setTextValueSuffix (" dB");
    addAndMakeVisible (gainSlider);

    addAndMakeVisible (bypassButton);

    // Bind by the same ID constants the processor declares -- a typo'd string
    // literal here fails at runtime with a silent dead control, not at compile
    // time, so there is exactly one spelling of each ID in the codebase.
    gainAttachment = std::make_unique<SliderAttachment> (
        processorRef.apvts, ShipStudiosMcpProcessor::paramGainDb, gainSlider);
    bypassAttachment = std::make_unique<ButtonAttachment> (
        processorRef.apvts, ShipStudiosMcpProcessor::paramBypass, bypassButton);

    setSize (editorWidth, editorHeight);
}

ShipStudiosMcpEditor::~ShipStudiosMcpEditor() = default;

//==============================================================================
void ShipStudiosMcpEditor::paint (juce::Graphics& g)
{
    g.fillAll (juce::Colour (0xff1b1b1f));

    g.setColour (juce::Colour (0xff8a8a94));
    g.setFont (juce::FontOptions (13.0f));
    g.drawFittedText ("SHIP STUDIOS MCP",
                      getLocalBounds().removeFromTop (margin + 12),
                      juce::Justification::centred, 1);
}

void ShipStudiosMcpEditor::resized()
{
    auto area = getLocalBounds().reduced (margin);
    area.removeFromTop (margin);                       // the title drawn in paint()

    bypassButton.setBounds (area.removeFromBottom (24));
    gainLabel.setBounds (area.removeFromTop (18));
    gainSlider.setBounds (area);
}
