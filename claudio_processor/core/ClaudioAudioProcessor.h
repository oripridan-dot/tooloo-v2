#pragma once

#include <JuceHeader.h>
#include "ClaudioHNSynthesizer.h"

namespace claudio {

struct EngramParams {
    float f0;
    float spectral_16d[16];
    float noise_floor;
    float phase_alignment;
    float spectral_flux;
    float transient_trigger;
};

class ClaudioAudioProcessor : public juce::AudioProcessor {
public:
    ClaudioAudioProcessor();
    ~ClaudioAudioProcessor() override;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "Claudio SOTA Engine"; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int index) override {}
    const juce::String getProgramName (int index) override { return {}; }
    void changeProgramName (int index, const juce::String& newName) override {}

    void getStateInformation (juce::MemoryBlock& destData) override {}
    void setStateInformation (const void* data, int sizeInBytes) override {}

    // Engram update (Atomic/Thread-safe via simple overwrite for now)
    void updateEngram(const EngramParams& params);
    void loadEngramFromJSON (const juce::String& jsonString);

    // Pathway B: Multi-Variant Parallel Competition
    struct VariantResult {
        EngramParams params;
        float delta_rms;
        bool success;
    };

    void triggerPathwayB();
    void selectWinner (const VariantResult& result);

private:
    ClaudioHNSynthesizer hnSynthesizer;
    EngramParams currentEngram;
    std::atomic<bool> engramUpdated { false };

    // Parallel Infrastructure
    juce::ThreadPool threadPool { 4 }; // Capped at 4 for M1 Performance
    std::atomic<float> currentDelta { 1.0f };
    std::atomic<bool> isPathwayBActive { false };

    double engineSampleRate = 44100.0;
    juce::dsp::PhaseLockedLoop<float> pll;

    // Playback Timeline for Standalone mode
    std::vector<EngramParams> engramTimeline;
    int playbackIndex = 0;
    int samplesSinceLastEngram = 0;
    bool isPlaying = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ClaudioAudioProcessor)
};

} // namespace claudio
