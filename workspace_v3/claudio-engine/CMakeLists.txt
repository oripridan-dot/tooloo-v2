cmake_minimum_required(VERSION 3.22)
project(claudio_sota LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 1. JUCE Integration
find_package(JUCE CONFIG REQUIRED)

# 2. Shared Library Definition
add_library(claudio_sota SHARED
    core/ClaudioHNSynthesizer.cpp
    core/ClaudioHNSynthesizer.h
    core/bridge.cpp)

# 3. Include Paths
target_include_directories(claudio_sota PRIVATE 
    core
    /Applications/JUCE/Modules)

# 4. Linking
target_link_libraries(claudio_sota PRIVATE
    juce::juce_audio_basics
    juce::juce_dsp
    juce::juce_core)

# 5. Optimizations
target_compile_options(claudio_sota PRIVATE
    $<$<CONFIG:Release>:-O3 -ffast-math -mavx2>)
