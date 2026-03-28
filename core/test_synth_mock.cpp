#include <iostream>
#include <vector>
#include <cmath>
#include <cassert>
#include "ClaudioHNSynthesizer.h"

// Mock JUCE components for standalone verification
namespace juce {
    namespace dsp {
        template <typename T>
        struct ProcessSpec { double sampleRate; int maximumBlockSize; int numChannels; };
        
        template <typename T>
        struct Oscillator {
            void prepare(const ProcessSpec<T>&) {}
            void setFrequency(T) {}
            T processSample(T) { return 0.5f; } // Mock constant tone
        };

        namespace IIR {
            template <typename T>
            struct Filter {
                void prepare(const ProcessSpec<T>&) {}
                void setCutoffFrequency(T) {}
                T processSample(T in) { return in; } // Mock transparent filter
            }
        }
    }

    struct AudioBuffer<typename T> {
        int numChannels;
        int numSamples;
        std::vector<std::vector<T>> data;
        
        AudioBuffer(int c, int s) : numChannels(c), numSamples(s), data(c, std::vector<T>(s, 0.0f)) {}
        int getNumChannels() const { return numChannels; }
        int getNumSamples() const { return numSamples; }
        void setSample(int c, int s, T v) { data[c][s] = v; }
        void applyGain(T g) { /* mock */ }
    };

    struct Random {
        float nextFloat() { return 0.1f; } // Mock fixed random
    };
}

int main() {
    std::cout << "Starting Claudio C++ Synthesis Verification..." << std::endl;
    
    claudio::ClaudioHNSynthesizer synth;
    juce::dsp::ProcessSpec<float> spec = { 44100.0, 512, 2 };
    synth.prepare(spec);

    std::vector<float> envelope(32, 0.5f);
    std::vector<float> phases(32, 0.0f);
    synth.updateFromEngram(440.0f, envelope, phases, 0.1f);

    juce::AudioBuffer<float> buffer(2, 128);
    synth.processBlock(buffer);

    // Verify Stereo Output (all channels should have data)
    assert(buffer.data[0][0] != 0.0f);
    assert(buffer.data[1][0] != 0.0f);
    assert(std::abs(buffer.data[0][0] - buffer.data[1][0]) < 1e-6f);

    std::cout << "SUCCESS: C++ Stereo 32D Kernel Verified." << std::endl;
    return 0;
}
