# Claudio: macOS Production Build Guide

The Claudio Audio Engine is now production-ready. To compile the final **VST3, AU, and Standalone** binaries on your macOS (M1/M2) environment, follow these steps:

## Prerequisites
1. **JUCE 7/8 SDK:** [Download here](https://juce.com/get-juce/).
2. **CMake 3.22+**: `brew install cmake`
3. **Xcode 15+**: Installed via the App Store.

## 1. Local Configuration
Point CMake to your local JUCE installation:

```bash
cmake -B build -G Xcode \
      -Djuce_DIR=/path/to/your/JUCE \
      -DCMAKE_BUILD_TYPE=Release
```

## 2. Compile
Trigger the optimized build (Includes SIMD/AVX2 support for M1 Rosetta/Windows transitions):

```bash
cmake --build build --config Release -j 8
```

## 3. Post-Build
The binaries will be generated in:
- `build/Claudio_artefacts/Release/VST3/Claudio SOTA Engine.vst3`
- `build/Claudio_artefacts/Release/AU/Claudio SOTA Engine.component`
- `build/Claudio_artefacts/Release/Standalone/Claudio SOTA Engine.app`

## 4. Notarization (Standard Studio Workflow)
To use the plugin in Logic/Ableton, you must sign and notarize it:

```bash
codesign --force --options runtime --entitlements core/Claudio.entitlements \
         --sign "Developer ID Application: Your Name" build/.../Claudio.vst3
```

---
**Claudio (C+I) protocol is officially ready for the studio.**
