#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — Android Build
# Tech: Kotlin + Go + Flutter + Rust
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² Android ═══"
echo "Stack: Kotlin + Go + Flutter + Rust"
echo ""
echo "--- Building Rust core ---"
cd "$ROOT/core" && cargo build --release --target aarch64-linux-android 2>&1 && echo "✓ Rust core built"
echo ""
echo "--- Building Flutter UI ---"
cd "$ROOT/platforms/android" && flutter build apk --release 2>&1 && echo "✓ Flutter UI built"
echo ""
echo "--- Combining ---"
cp "$ROOT/platforms/android/build/app/outputs/flutter-apk/app-release.apk" "$ROOT/builds/android/output.apk" 2>/dev/null
echo "✓ Android APK: builds/android/output.apk"
echo "═══ Android Build Complete ═══"
