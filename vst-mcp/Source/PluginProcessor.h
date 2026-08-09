#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>

//==============================================================================
/**
    Ship Studios MCP -- walking skeleton.

    Right now this is a transparent trim: input -> [ gain ] -> out, plus a
    host-visible bypass. That is deliberate. A plugin's identity (PLUGIN_CODE,
    BUNDLE_ID, parameter IDs) is what a host writes into a saved session, so the
    skeleton exists to get those frozen and render-verified BEFORE any DSP or
    MCP wiring lands on top of it.

    SIGNAL PATH, kept as discrete stages so later blocks drop in without
    restructuring:

        in -> [ gain ] -> out

    The gain is smoothed rather than applied per-block: a parameter jump applied
    as a step is an audible click, and hosts automate these at block rate.
*/
class ShipStudiosMcpProcessor final : public juce::AudioProcessor
{
public:
    ShipStudiosMcpProcessor();
    ~ShipStudiosMcpProcessor() override;

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
    double getTailLengthSeconds() const override               { return 0.0; }

    //==========================================================================
    // Programs: hosts require these to exist. State lives in the APVTS instead,
    // so there is exactly one program and nothing to switch between.
    int getNumPrograms() override                              { return 1; }
    int getCurrentProgram() override                           { return 0; }
    void setCurrentProgram (int) override                      {}
    const juce::String getProgramName (int) override           { return {}; }
    void changeProgramName (int, const juce::String&) override {}

    //==========================================================================
    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    //==========================================================================
    /** Every parameter lives here; the editor attaches to it by ID. */
    juce::AudioProcessorValueTreeState apvts;

    /** Parameter IDs. These are what pedalboard and the host see -- hyphens are
        illegal in VST3 parameter IDs, so they are snake_case throughout. Freeze
        them alongside the plugin codes: renaming one breaks saved automation. */
    static constexpr const char* paramGainDb = "gain_db";
    static constexpr const char* paramBypass = "bypass";

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    // Cached raw pointers: reading these on the audio thread is a load, whereas
    // getRawParameterValue() by string does a map lookup per call.
    std::atomic<float>* gainDb = nullptr;
    std::atomic<float>* bypassed = nullptr;

    juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> gainSmoothed;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ShipStudiosMcpProcessor)
};
