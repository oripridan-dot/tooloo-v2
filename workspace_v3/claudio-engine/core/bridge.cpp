#include "ClaudioHNSynthesizer.h"
#include <iostream>

extern "C" {
    /**
     * @brief Creates a new synthesizer instance.
     */
    claudio::ClaudioHNSynthesizer* claudio_create() {
        return new claudio::ClaudioHNSynthesizer();
    }

    /**
     * @brief Prepares the synthesizer for processing.
     */
    void claudio_prepare(claudio::ClaudioHNSynthesizer* synth, double sampleRate, int blockSize) {
        if (!synth) return;
        juce::dsp::ProcessSpec spec;
        spec.sampleRate = sampleRate;
        spec.maximumBlockSize = static_cast<juce::uint32>(blockSize);
        spec.numChannels = 2;
        synth->prepare(spec);
    }

    /**
     * @brief Updates engine parameters from an Engram.
     */
    void claudio_update(claudio::ClaudioHNSynthesizer* synth, 
                        float f0, 
                        const float* spectralEnvelope, 
                        int envSize,
                        const float* phases,
                        int phaseSize,
                        float noiseFloor) {
        if (!synth) return;
        
        std::vector<float> env(spectralEnvelope, spectralEnvelope + envSize);
        std::vector<float> ph(phases, phases + phaseSize);
        
        synth->updateFromEngram(f0, env, ph, noiseFloor);
    }

    /**
     * @brief Processes a block of audio.
     */
    void claudio_process(claudio::ClaudioHNSynthesizer* synth, float* left, float* right, int numSamples) {
        if (!synth) return;

        // Wrap the raw pointers into a JUCE AudioBuffer
        float* channels[] = { left, right };
        juce::AudioBuffer<float> buffer(channels, 2, numSamples);
        
        synth->processBlock(buffer);
    }

    /**
     * @brief Deletes the synthesizer instance.
     */
    void claudio_destroy(claudio::ClaudioHNSynthesizer* synth) {
        delete synth;
    }
}
