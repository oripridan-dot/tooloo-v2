cmake_minimum_required(VERSION 3.22)

project(Claudio VERSION 1.2.0 LANGUAGES CXX C)

# --- 1. JUCE Integration (Headless Pulse) ---
include(FetchContent)
FetchContent_Declare(
    juce
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.2 # Latest SOTA for macOS 15.1
)
FetchContent_MakeAvailable(juce)

# --- 2. Global JUCE Configuration (Headless SOTA) ---
add_definitions(
    -DJUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1
    -DJUCE_WEB_BROWSER=0
    -DJUCE_USE_CURL=0
    -DCLAUDIO_HEADLESS=1
)

# --- 3. Source Files ---
set(Claudio_SOURCES
    claudio_processor/core/ClaudioAudioProcessor.cpp
    claudio_processor/core/ClaudioAudioProcessor.h
    claudio_processor/core/ClaudioHNSynthesizer.cpp
    claudio_processor/core/ClaudioHNSynthesizer.h
    claudio_processor/core/ClaudioDecompiler.cpp
    claudio_processor/core/ClaudioDecompiler.h
    claudio_processor/core/ClaudioCollaborationPulse.cpp
    claudio_processor/core/ClaudioCollaborationPulse.h
    claudio_processor/core/ClaudioGearSimulator.h
    claudio_processor/core/ClaudioSovereignBridge.cpp)

# --- 3. Sovereign Shared Library (Non-GUI Engine) ---
add_library(ClaudioEngine SHARED ${Claudio_SOURCES})

target_compile_definitions(ClaudioEngine PRIVATE 
    CLAUDIO_SHARED_LIB=1)

if(APPLE AND CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
    target_compile_options(ClaudioEngine PRIVATE -O3 -ffast-math)
else()
    target_compile_options(ClaudioEngine PRIVATE -O3 -ffast-math -mavx2)
endif()

target_link_libraries(ClaudioEngine PRIVATE
    juce::juce_audio_utils
    juce::juce_audio_processors
    juce::juce_audio_formats
    juce::juce_audio_devices
    juce::juce_core
    juce::juce_events
    juce::juce_data_structures
    juce::juce_dsp)

# --- 4. Executables ---
add_executable(ClaudioDiagnostic isolated_claudio_engine/bridge_test.cpp)
target_link_libraries(ClaudioDiagnostic PRIVATE ClaudioEngine juce::juce_audio_basics juce::juce_dsp juce::juce_events)
target_compile_definitions(ClaudioDiagnostic PRIVATE JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED)

add_executable(claudio_batch_processor isolated_claudio_engine/claudio_batch_processor.cpp)
target_link_libraries(claudio_batch_processor PRIVATE ClaudioEngine juce::juce_audio_basics juce::juce_audio_formats juce::juce_dsp juce::juce_core)
target_compile_definitions(claudio_batch_processor PRIVATE JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED)

# --- 5. macOS Notarization & Hardened Runtime ---
if(APPLE)
    set_target_properties(ClaudioEngine PROPERTIES
        XCODE_ATTRIBUTE_ENABLE_HARDENED_RUNTIME TRUE
        XCODE_ATTRIBUTE_CODE_SIGN_INJECT_BASE_ENTITLEMENTS_NOT_REQUIRED YES
        BUNDLE_DESTINATION "${CMAKE_CURRENT_BINARY_DIR}")
endif()
