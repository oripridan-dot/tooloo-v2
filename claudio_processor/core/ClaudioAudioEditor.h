#pragma once

#include <JuceHeader.h>
#include "ClaudioAudioProcessor.h"

namespace claudio {

class ClaudioAudioEditor : public juce::AudioProcessorEditor, private juce::Timer {
public:
    ClaudioAudioEditor (ClaudioAudioProcessor&);
    ~ClaudioAudioEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;

    ClaudioAudioProcessor& audioProcessor;
    juce::Label statusLabel;
    juce::TextButton loadButton;
    std::unique_ptr<juce::FileChooser> fileChooser;
    
    // SOTA Minimalist UI styling
    static const juce::Colour claudioGreen;
    static const juce::Colour claudioDark;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ClaudioAudioEditor)
};

} // namespace claudio
