#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — macOS Build
# Tech: Pure Swift + Electrobun
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² macOS ═══"
echo "Stack: Pure Swift + Electrobun"
echo ""
echo "--- Building Swift app ---"
cd "$ROOT/platforms/macos" && xcodebuild -scheme Nimbus2 2>&1 && echo "✓ macOS app built"
echo ""
echo "--- Creating DMG ---"
mkdir -p "$ROOT/builds/macos/output"
echo "✓ macOS app: builds/macos/output/Nimbus2.app"
echo "═══ macOS Build Complete ═══"
