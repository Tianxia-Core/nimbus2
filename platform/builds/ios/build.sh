#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — iOS Build
# Tech: Pure Swift
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² iOS ═══"
echo "Stack: Pure Swift (SwiftUI)"
echo ""
echo "--- Building Swift app ---"
cd "$ROOT/platforms/ios" && xcodebuild -scheme Nimbus2 -sdk iphoneos -configuration Release 2>&1 && echo "✓ iOS app built"
echo ""
echo "--- Creating IPA ---"
mkdir -p "$ROOT/builds/ios/output"
cp -r "$ROOT/platforms/ios/build/Release-iphoneos/Nimbus2.app" "$ROOT/builds/ios/output/" 2>/dev/null
echo "✓ iOS app: builds/ios/output/Nimbus2.app"
echo "═══ iOS Build Complete ═══"
