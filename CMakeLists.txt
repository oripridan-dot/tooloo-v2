cmake_minimum_required(VERSION 3.22)

project(Claudio VERSION 1.2.0 LANGUAGES CXX C)

# 1. JUCE Integration
add_subdirectory(third_party/JUCE)

juce_add_plugin(Claudio
    COMPANY_NAME "TooLoo"
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD TRUE
    PLUGIN_MANUFACTURER_CODE Tool
    PLUGIN_CODE Clau
    FORMATS VST3 AU Standalone
    PRODUCT_NAME "Claudio SOTA Engine")

juce_generate_juce_header(Claudio)

# 2. Source Files
target_sources(Claudio PRIVATE
    core/ClaudioAudioProcessor.cpp
    core/ClaudioAudioProcessor.h
    core/ClaudioAudioEditor.cpp
    core/ClaudioAudioEditor.h
    core/ClaudioHNSynthesizer.cpp
    core/ClaudioHNSynthesizer.h)

# 3. Compiler Definitions & Optimizations
target_compile_definitions(Claudio PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)

if(APPLE AND CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
    target_compile_options(Claudio PRIVATE -O3 -ffast-math) # Apple Silicon SOTA
else()
    target_compile_options(Claudio PRIVATE -O3 -ffast-math -mavx2) # Intel SOTA
endif()

# 4. Linking
target_link_libraries(Claudio PRIVATE
    juce::juce_audio_utils
    juce::juce_audio_processors
    juce::juce_audio_formats
    juce::juce_audio_devices
    juce::juce_graphics
    juce::juce_gui_basics
    juce::juce_dsp)

# 5. macOS Notarization & Hardened Runtime
if(APPLE)
    set_target_properties(Claudio PROPERTIES
        XCODE_ATTRIBUTE_ENABLE_HARDENED_RUNTIME TRUE
        XCODE_ATTRIBUTE_CODE_SIGN_INJECT_BASE_ENTITLEMENTS_NOT_REQUIRED YES
        XCODE_ATTRIBUTE_CODE_SIGN_ENTITLEMENTS "${CMAKE_CURRENT_SOURCE_DIR}/core/Claudio.entitlements")
endif()
