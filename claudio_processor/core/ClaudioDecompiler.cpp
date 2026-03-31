/*
  ==============================================================================
    ClaudioDecompiler.cpp
    Created: 27 Mar 2026
    Author: TooLoo Principal Systems Architect
  ==============================================================================
*/

#include "ClaudioDecompiler.h"
#include <cmath>
#include <algorithm>

namespace claudio {

ClaudioDecompiler::ClaudioDecompiler(double sampleRate) 
    : mSampleRate(sampleRate)
{
    // Pre-allocate analysis buffer for 10ms at 96kHz (960 samples)
    int maxSamples = static_cast<int>(sampleRate * 0.015); // 15ms safety margin
    mAnalysisBuffer.setSize(1, maxSamples);
}

void ClaudioDecompiler::processBlock(const juce::AudioBuffer<float>& buffer)
{
    const int numSamples = buffer.getNumSamples();
    const float* channelData = buffer.getReadPointer(0);

    // 1. Extract Velocity (RMS -> dB)
    float rms = calculateRMS(channelData, numSamples);
    float velocityDb = 20.0f * std::log10(rms + 1e-9f);
    mLatestVelocity.store(velocityDb);

    // 2. Extract Pitch (f0_hz) via YIN/Autocorrelation
    // In a real JUCE app, this would be a more robust YIN implementation
    performYINAnalysis(channelData, numSamples);
}

float ClaudioDecompiler::calculateRMS(const float* data, int numSamples)
{
    float sumSquares = 0.0f;
    for (int i = 0; i < numSamples; ++i) {
        sumSquares += data[i] * data[i];
    }
    return std::sqrt(sumSquares / static_cast<float>(numSamples));
}

void ClaudioDecompiler::performYINAnalysis(const float* data, int numSamples)
{
    // Simplified Autocorrelation-based pitch detection for header implementation
    // A production YIN would include Step 2 (Difference Function) and 
    // Step 3 (Cumulative Mean Normalized Difference)
    
    std::vector<float> corr(numSamples, 0.0f);
    
    for (int tau = 0; tau < numSamples / 2; ++tau) {
        for (int i = 0; i < numSamples / 2; ++i) {
            corr[tau] += data[i] * data[i + tau];
        }
    }

    // Peak picking for fundamental frequency
    int peakIdx = 0;
    float maxCorr = -1.0f;
    bool passedZeroCrossing = false;

    for (int i = 1; i < numSamples / 2; ++i) {
        if (!passedZeroCrossing) {
            if (corr[i] < 0) passedZeroCrossing = true;
            continue;
        }

        if (corr[i] > maxCorr) {
            maxCorr = corr[i];
            peakIdx = i;
        }
    }

    if (peakIdx > 0) {
        float f0 = static_cast<float>(mSampleRate / peakIdx);
        mLatestF0.store(f0);
    }
}

IntentEngram ClaudioDecompiler::getLatestEngram() const
{
    IntentEngram engram;
    engram.f0_hz = mLatestF0.load();
    engram.velocity_db = mLatestVelocity.load();
    engram.timestamp_us = static_cast<uint64_t>(juce::Time::getHighResolutionTicks());
    
    // In production, timbre_16d would be populated via FFT/STFT analysis
    engram.timbre_16d = std::vector<float>(16, 0.42f); 
    
    return engram;
}

} // namespace claudio
