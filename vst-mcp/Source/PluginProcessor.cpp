#include "PluginProcessor.h"

#include "PluginEditor.h"

namespace
{
// Long enough that a full-range parameter sweep can't click, short enough that
// an automated move still lands where the automation says it does.
constexpr double gainSmoothingSeconds = 0.02;
}

//==============================================================================
juce::AudioProcessorValueTreeState::ParameterLayout
ShipStudiosMcpProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    // ParameterID's second argument is the version hint. VST3 requires it, and
    // it must never go backwards: bump it only when a parameter's meaning
    // changes in a way that would misread an old saved session.
    layout.add (std::make_unique<juce::AudioParameterFloat> (
        juce::ParameterID { paramGainDb, 1 },
        "Gain",
        juce::NormalisableRange<float> { -24.0f, 24.0f, 0.01f },
        0.0f,
        juce::AudioParameterFloatAttributes().withLabel ("dB")));

    layout.add (std::make_unique<juce::AudioParameterBool> (
        juce::ParameterID { paramBypass, 1 },
        "Bypass",
        false));

    return layout;
}

//==============================================================================
ShipStudiosMcpProcessor::ShipStudiosMcpProcessor()
    : AudioProcessor (BusesProperties()
                          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "PARAMETERS", createParameterLayout())
{
    gainDb   = apvts.getRawParameterValue (paramGainDb);
    bypassed = apvts.getRawParameterValue (paramBypass);
}

ShipStudiosMcpProcessor::~ShipStudiosMcpProcessor() = default;

//==============================================================================
void ShipStudiosMcpProcessor::prepareToPlay (double sampleRate, int)
{
    gainSmoothed.reset (sampleRate, gainSmoothingSeconds);
    gainSmoothed.setCurrentAndTargetValue (juce::Decibels::decibelsToGain (gainDb->load()));
}

void ShipStudiosMcpProcessor::releaseResources()
{
}

bool ShipStudiosMcpProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    // Mono and stereo only, and the two sides must match. Refusing everything
    // else here is what stops a host handing us a layout the DSP silently
    // mishandles -- an unsupported layout is better rejected than half-served.
    const auto& out = layouts.getMainOutputChannelSet();

    if (out != juce::AudioChannelSet::mono() && out != juce::AudioChannelSet::stereo())
        return false;

    return layouts.getMainInputChannelSet() == out;
}

void ShipStudiosMcpProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;

    const auto totalNumInputChannels  = getTotalNumInputChannels();
    const auto totalNumOutputChannels = getTotalNumOutputChannels();
    const auto numSamples             = buffer.getNumSamples();

    // Any output bus the input doesn't feed holds whatever the host left there.
    for (auto ch = totalNumInputChannels; ch < totalNumOutputChannels; ++ch)
        buffer.clear (ch, 0, numSamples);

    // Bypass still rides the smoother to unity so toggling it can't click, and
    // the block is still walked -- keeping the two paths the same length is what
    // will keep latency honest once a latency-reporting stage lands here.
    const auto targetDb = bypassed->load() > 0.5f ? 0.0f : gainDb->load();
    gainSmoothed.setTargetValue (juce::Decibels::decibelsToGain (targetDb));

    for (int i = 0; i < numSamples; ++i)
    {
        const auto g = gainSmoothed.getNextValue();

        for (int ch = 0; ch < totalNumInputChannels; ++ch)
            buffer.getWritePointer (ch)[i] *= g;
    }
}

//==============================================================================
juce::AudioProcessorEditor* ShipStudiosMcpProcessor::createEditor()
{
    return new ShipStudiosMcpEditor (*this);
}

//==============================================================================
void ShipStudiosMcpProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    if (auto xml = apvts.copyState().createXml())
        copyXmlToBinary (*xml, destData);
}

void ShipStudiosMcpProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    auto xml = getXmlFromBinary (data, sizeInBytes);

    // A session saved by a different plugin (or a corrupt block) must not be
    // applied -- checking the tag is what makes a bad restore a no-op instead of
    // an exception on the message thread.
    if (xml == nullptr || ! xml->hasTagName (apvts.state.getType()))
        return;

    apvts.replaceState (juce::ValueTree::fromXml (*xml));
}

//==============================================================================
// This is what the host calls to instantiate the plugin.
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new ShipStudiosMcpProcessor();
}
