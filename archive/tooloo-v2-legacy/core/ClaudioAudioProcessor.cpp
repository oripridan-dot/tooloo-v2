#include "ClaudioAudioProcessor.h"
#include "ClaudioAudioEditor.h"

namespace claudio {

ClaudioAudioProcessor::ClaudioAudioProcessor()
    : AudioProcessor (BusesProperties()
                      .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                      .withOutput ("Output", juce::AudioChannelSet::stereo(), true))
{
}

ClaudioAudioProcessor::~ClaudioAudioProcessor() 
{
    threadPool.removeAllJobs (true, 1000);
}

// Pathway B: Multi-Variant Job
class ParallelVariantJob : public juce::ThreadPoolJob
{
public:
    ParallelVariantJob (ClaudioAudioProcessor& p, ClaudioAudioProcessor::EngramParams variantParams, juce::String name)
        : ThreadPoolJob (name), processor (p), params (variantParams)
    {}

    juce::JobStatus runJob() override
    {
        // 1. Simulate Synthesis Cycle for this variant
        // In a real SOTA engine, this would call the H+N Synthesizer in a sandbox
        // For this implementation, we calculate a mock fidelity delta based on 'hop_size' simulation
        
        float mock_delta = 0.04f + (static_cast<float>(rand() % 100) / 10000.0f);
        
        // 2. Report Result back to Processor
        ClaudioAudioProcessor::VariantResult result { params, mock_delta, true };
        processor.selectWinner (result);
        
        return jobHasFinished;
    }

private:
    ClaudioAudioProcessor& processor;
    ClaudioAudioProcessor::EngramParams params;
};

void ClaudioAudioProcessor::triggerPathwayB()
{
    if (isPathwayBActive.exchange (true)) return;

    // 1. Define SOTA strategies
    std::vector<EngramParams> strategies;
    
    // High Temporal Resolution
    EngramParams highRes = currentEngram;
    highRes.spectral_flux *= 1.2f;
    strategies.push_back (highRes);

    // Spectral Stability
    EngramParams spectralSync = currentEngram;
    spectralSync.phase_alignment = 1.0f;
    strategies.push_back (spectralSync);

    // 2. Launch Jobs
    for (int i = 0; i < strategies.size(); ++i)
        threadPool.addJob (new ParallelVariantJob (*this, strategies[i], "PathwayB_Variant_" + juce::String (i)), true);
}

void ClaudioAudioProcessor::selectWinner (const VariantResult& result)
{
    // SOTA: Competitive selection logic
    if (result.delta_rms < currentDelta.load())
    {
        currentDelta.store (result.delta_rms);
        updateEngram (result.params);
        
        // 1. Log to Console
        juce::Logger::writeToLog ("[GOVERNOR] Pathway B Winner: Δ=" + juce::String (result.delta_rms));

        // 2. Persist Telemetry for 22D Unification
        juce::DynamicObject::Ptr telemetry = new juce::DynamicObject();
        telemetry->setProperty ("delta_rms", result.delta_rms);
        telemetry->setProperty ("pathway", "B");
        telemetry->setProperty ("timestamp", juce::Time::getCurrentTime().toMilliseconds());
        
        juce::DynamicObject::Ptr params = new juce::DynamicObject();
        params->setProperty ("f0", result.params.f0);
        params->setProperty ("spectral_flux", result.params.spectral_flux);
        params->setProperty ("phase_alignment", result.params.phase_alignment);
        telemetry->setProperty ("winning_params", params.get());

        // Write to results/native_telemetry.json (Relative to Plugin/Host executable)
        // In this workspace, we target the results/ directory.
        auto resultsDir = juce::File::getCurrentWorkingDirectory().getChildFile ("results");
        if (!resultsDir.exists()) resultsDir.createDirectory();
        
        auto telemetryFile = resultsDir.getChildFile ("native_telemetry.json");
        telemetryFile.replaceWithText (juce::JSON::toString (telemetry.get()));
    }
    
    if (threadPool.getNumJobs() == 0)
        isPathwayBActive.store (false);
}

void ClaudioAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    // 1. Lock to Host Sample Rate
    engineSampleRate = sampleRate;
    
    juce::dsp::ProcessSpec spec;
    spec.sampleRate = sampleRate;
    spec.maximumBlockSize = samplesPerBlock;
    spec.numChannels = getTotalNumOutputChannels();

    // 2. Propagate to the H+N Synthesizer
    hnSynthesizer.prepare(spec);
    
    // 3. Update the PLL (Phase-Locked Loop) to track the new Nyquist limit
    pll.setSampleRate(sampleRate);
}

void ClaudioAudioProcessor::releaseResources() {}

void ClaudioAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    auto numSamples = buffer.getNumSamples();

    // 1. Advance Timeline (Standalone Mode)
    if (isPlaying && !engramTimeline.empty())
    {
        samplesSinceLastEngram += numSamples;
        int samplesPerEngram = static_cast<int>(getSampleRate() * 0.01); // 10ms

        if (samplesSinceLastEngram >= samplesPerEngram)
        {
            playbackIndex = (playbackIndex + 1) % engramTimeline.size();
            updateEngram(engramTimeline[playbackIndex]);
            samplesSinceLastEngram = 0;
        }
    }

    // 2. Thread-Safe Engram Update
    if (engramUpdated.exchange(false))
    {
        std::vector<float> specVec(std::begin(currentEngram.spectral_16d), std::end(currentEngram.spectral_16d));
        std::vector<float> zeroPhases(32, 0.0f); // Default phases
        
        hnSynthesizer.updateFromEngram(currentEngram.f0, 
                                       specVec,
                                       zeroPhases,
                                       currentEngram.noise_floor);
        
        // SOTA: Auto-trigger Pathway B if signal complexity is high
        if (currentEngram.spectral_flux > 0.8f && currentDelta.load() > 0.1f)
            triggerPathwayB();
    }

    // 3. Clear and Synthesize
    buffer.clear();
    hnSynthesizer.processBlock(buffer);
}

void ClaudioAudioProcessor::loadEngramFromJSON (const juce::String& jsonString)
{
    auto json = juce::JSON::parse (jsonString);
    if (auto* intent = json.getDynamicObject()->getProperty ("intent").getDynamicObject())
    {
        EngramParams p;
        p.f0 = (float)intent->getProperty ("f0_global");
        p.phase_alignment = (float)intent->getProperty ("phase_alignment");
        p.spectral_flux = (float)intent->getProperty ("spectral_flux");
        p.transient_trigger = (float)intent->getProperty ("transient_trigger");
        
        // Simplified: push one frame for now to verify 'Lock'
        engramTimeline.clear();
        engramTimeline.push_back(p);
        playbackIndex = 0;
        isPlaying = true;
    }
}

void ClaudioAudioProcessor::updateEngram(const EngramParams& params)
{
    currentEngram = params;
    engramUpdated.store(true);
}

juce::AudioProcessorEditor* ClaudioAudioProcessor::createEditor()
{
    return new ClaudioAudioEditor (*this);
}

} // namespace claudio

// Global factory function required by JUCE
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new claudio::ClaudioAudioProcessor();
}
