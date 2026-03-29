#include "ClaudioAudioProcessor.h"
#include "ClaudioAudioEditor.h"

namespace claudio {

const juce::Colour ClaudioAudioEditor::claudioGreen = juce::Colour::fromFloatRGBA(0.0f, 1.0f, 0.4f, 1.0f);
const juce::Colour ClaudioAudioEditor::claudioDark  = juce::Colour::fromFloatRGBA(0.05f, 0.05f, 0.07f, 1.0f);

ClaudioAudioEditor::ClaudioAudioEditor (ClaudioAudioProcessor& p)
    : AudioProcessorEditor (&p), audioProcessor (p)
{
    setSize (400, 300);
    
    statusLabel.setText("CLAUDIO SOTA ENGINE: STANDALONE", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    statusLabel.setFont(juce::Font(22.0f, juce::Font::bold));
    statusLabel.setColour(juce::Label::textColourId, claudioGreen);
    addAndMakeVisible(statusLabel);

    loadButton.setButtonText("LOAD ENGRAM (.json)");
    loadButton.setColour(juce::TextButton::buttonColourId, juce::Colours::transparentBlack);
    loadButton.setColour(juce::TextButton::textColourOffId, claudioGreen);
    loadButton.onClick = [this] {
        fileChooser = std::make_unique<juce::FileChooser> ("Select Engram", juce::File::getSpecialLocation(juce::File::userHomeDirectory), "*.json");
        auto flags = juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles;
        
        fileChooser->launchAsync (flags, [this] (const juce::FileChooser& fc) {
            auto file = fc.getResult();
            if (file.existsAsFile()) {
                audioProcessor.loadEngramFromJSON(file.loadFileAsString());
            }
        });
    };
    addAndMakeVisible(loadButton);

    startTimerHz(30); // 30 FPS UI refresh
}

ClaudioAudioEditor::~ClaudioAudioEditor() {}

void ClaudioAudioEditor::paint (juce::Graphics& g)
{
    g.fillAll (claudioDark);
    
    // Draw SOTA 'Engram Wave' Visualization
    g.setColour(claudioGreen.withAlpha(0.2f));
    auto bounds = getLocalBounds().toFloat();
    float centerY = bounds.getCentreY();
    
    juce::Path wavePath;
    wavePath.startNewSubPath(0, centerY);
    
    for (int x = 0; x < getWidth(); x += 5) {
        float offset = std::sin(x * 0.05f + (float)juce::Time::getMillisecondCounterHiRes() * 0.01f) * 20.0f;
        wavePath.lineTo(x, centerY + offset);
    }
    
    g.strokePath(wavePath, juce::PathStrokeType(2.0f));
}

void ClaudioAudioEditor::resized()
{
    statusLabel.setBounds(0, 50, getWidth(), 50);
    loadButton.setBounds(getLocalBounds().withSizeKeepingCentre(200, 40).withY(150));
}

void ClaudioAudioEditor::timerCallback()
{
    repaint();
}

} // namespace claudio
