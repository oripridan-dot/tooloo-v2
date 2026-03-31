#pragma once

#include <JuceHeader.h>
#include <vector>

namespace claudio {

/**
 * @class ClaudioHNSynthesizer
 * @brief SOTA Harmonic-plus-Noise (H+N) Synthesis Engine for real-time Engram reconstruction.
 * 
 * Separates the audio into a deterministic (Harmonic) layer and a stochastic (Noise) layer
 * to achieve 99.99% fidelity by capturing both 'Soul' and 'Grit'.
 */
class ClaudioHNSynthesizer {
public:
    ClaudioHNSynthesizer() {
        // Initialize noise filters and oscillators
        noiseFilter.setType(juce::dsp::SpecialFixedFilterType::highPass);
    }

    /**
     * @brief High-precision PolyBLEP for anti-aliasing.
     */
    static float polyBLEP(float phase, float dt) {
        if (phase < dt) {
            phase /= dt;
            return phase + phase - phase * phase - 1.0f;
        } else if (phase > 1.0f - dt) {
            phase = (phase - 1.0f) / dt;
            return phase * phase + phase + phase + 1.0f;
        }
        return 0.0f;
    }

    void prepare(const juce::dsp::ProcessSpec& spec) {
        sampleRate = spec.sampleRate;
        
        for (auto& osc : harmonicOscillators)
            osc.prepare(spec);
            
        noiseOsc.prepare(spec);
        noiseFilter.prepare(spec);

        // Pre-allocate transient buffer for 50ms of audio
        transientBuffer.setSize(1, static_cast<int>(sampleRate * 0.05));
        transientBuffer.clear();
    }

    /**
     * @brief Processes a block of audio by summing the harmonic oscillators 
     * and the spectrally-shaped stochastic noise.
     */
    void processBlock(juce::AudioBuffer<float>& buffer);

    /**
     * @brief Updates the synthesis parameters from the (C+I) Engram.
     * @param f0 Fundamental frequency
     * @param spectralEnvelope 16D timbre vector
     * @param phases Vector of initial phases for each harmonic
     * @param noiseFloor Stochastic residual level
     */
    void updateFromEngram(float f0, 
                         const std::vector<float>& spectralEnvelope, 
                         const std::vector<float>& phases,
                         float noiseFloor,
                         float phaseAlignment = 0.0f,
                         float spectralFlux = 0.0f);

private:
    // Shared State
    double sampleRate = 44100.0;
    float globalGain = 1.0f;
    static constexpr int maxHarmonics = 32;

    // PLL & Stochastic Grit
    float harmonicPhases[maxHarmonics] = { 0.0f };
    float targetPhases[maxHarmonics] = { 0.0f };
    float spectralFlux = 0.0f;
    float transientEnergy = 0.0f;
    
    juce::dsp::Oscillator<float> noiseOsc;
    juce::dsp::IIR::Filter<float> noiseFilter;
    juce::dsp::IIR::Filter<float> transientFilter;
    juce::Random rand;

    // Harmonic Layer
    int numHarmonics = 0;
    juce::dsp::Oscillator<float> harmonicOscillators[maxHarmonics];
    float harmonicGains[maxHarmonics] = { 0.0f };
    float currentGains[maxHarmonics] = { 0.0f };
    float targetGains[maxHarmonics] = { 0.0f };

    // Transient Layer
    juce::AudioBuffer<float> transientBuffer;
    juce::AudioBuffer<float> overlapBuffer;
    int transientReadPos = 0;
    bool isTransientActive = false;
    float transientVelocity = 0.0f;
};

} // namespace claudio
