#!/bin/bash

# Claudio SOTA Build Orchestrator (macOS)
# Translating mathematical victory into production binary.

set -e

PROJECT_ROOT=$(pwd)
BUILD_DIR="$PROJECT_ROOT/build"
ENTITLEMENTS="$PROJECT_ROOT/core/Claudio.entitlements"

echo "[BUILDING] Initializing SOTA Release Build..."

# 1. Configuration (Release Mode + Xcode Generator)
cmake -B "$BUILD_DIR" -G Xcode -DCMAKE_BUILD_TYPE=Release

# 2. Build (Parallel)
echo "[BUILDING] Compiling VST3, AU, and Standalone..."
cmake --build "$BUILD_DIR" --config Release -j 8

# 3. Post-Build Verification
echo "[VERIFYING] Auditing Bundles..."

VST3_PATH="$BUILD_DIR/Claudio_artefacts/Release/VST3/Claudio SOTA Engine.vst3"
AU_PATH="$BUILD_DIR/Claudio_artefacts/Release/AU/Claudio SOTA Engine.component"
STANDALONE_PATH="$BUILD_DIR/Claudio_artefacts/Release/Standalone/Claudio SOTA Engine.app"

if [ -d "$VST3_PATH" ]; then echo "SUCCESS: VST3 Generated."; else echo "FAIL: VST3 Missing."; exit 1; fi
if [ -d "$AU_PATH" ]; then echo "SUCCESS: AU Generated."; else echo "FAIL: AU Missing."; exit 1; fi
if [ -d "$STANDALONE_PATH" ]; then echo "SUCCESS: Standalone Generated."; else echo "FAIL: Standalone Missing."; exit 1; fi

echo "[SUCCESS] Claudio SOTA Engine is ready for the studio."
