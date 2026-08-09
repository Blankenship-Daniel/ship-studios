#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

#include "PluginProcessor.h"

//==============================================================================
/**
    Ship Studios MCP -- walking-skeleton UI.

    One slider, one bypass toggle, both driven by APVTS attachments rather than
    listeners. The attachment is the two-way binding: it pushes host automation
    into the control and gestures back out, which is what makes automation
    recording work without a line of glue code.
*/
class ShipStudiosMcpEditor final : public juce::AudioProcessorEditor
{
public:
    explicit ShipStudiosMcpEditor (ShipStudiosMcpProcessor&);
    ~ShipStudiosMcpEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;

    ShipStudiosMcpProcessor& processorRef;

    juce::Slider gainSlider;
    juce::Label  gainLabel;
    juce::ToggleButton bypassButton { "Bypass" };

    // Attachments must outlive nothing and die BEFORE the controls they bind,
    // so they are declared after them -- destruction runs in reverse order.
    std::unique_ptr<SliderAttachment> gainAttachment;
    std::unique_ptr<ButtonAttachment> bypassAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ShipStudiosMcpEditor)
};
