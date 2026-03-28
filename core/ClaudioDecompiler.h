/*
  ==============================================================================
    ClaudioDecompiler.h
    Created: 27 Mar 2026
    Author: TooLoo Principal Systems Architect
    
    The Mathematical Inverse: EM_actual * E_local^-1 = (C+I)
    High-performance C++/JUCE implementation for sub-millisecond 
    Intent extraction.
  ==============================================================================
*/

#pragma once

#include <juce_audio_basics/juce_audio_basics.h>
#include <atomic>
#include <vector>

namespace claudio {

/**
    Represents the 16D Intent vector for a performance engram.
*/
struct IntentEngram {
    float f0_hz;
    float velocity_db;
    std::vector<float> timbre_16d;
    float pitch_modulation;
    uint64_t timestamp_us;
};

/**
    The Decompiler Core.
    Designed for zero-allocation processing on the real-time audio thread.
*/
class ClaudioDecompiler {
public:
    ClaudioDecompiler(double sampleRate);
    ~ClaudioDecompiler() = default;

    /**
        Processes a block of incoming EM_actual audio.
        Extracts Intent (C+I) and updates the internal state.
    */
    void processBlock(const juce::AudioBuffer<float>& buffer);

    /**
        Returns the latest extracted engram. 
        Thread-safe for consumption by the Network Thread.
    */
    IntentEngram getLatestEngram() const;

private:
    double mSampleRate;
    
    // Internal analysis buffers (Pre-allocated)
    juce::AudioBuffer<float> mAnalysisBuffer;
    
    // Extracted Intent (Atomic-guaranteed or double-buffered)
    std::atomic<float> mLatestF0 { 0.0f };
    std::atomic<float> mLatestVelocity { -96.0f };
    
    // Helper methods for spectral analysis
    void performYINAnalysis(const float* data, int numSamples);
    float calculateRMS(const float* data, int numSamples);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ClaudioDecompiler)
};

} // namespace claudio
