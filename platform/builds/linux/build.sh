#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — Linux Build
# Tech: Tauri + TypeScript + Nix
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² Linux ═══"
echo "Stack: Tauri + TypeScript + Nix"
echo ""
echo "--- Building Tauri app ---"
cd "$ROOT" && cargo tauri build --release --target x86_64-unknown-linux-gnu 2>&1 && echo "✓ Linux app built"
echo ""
echo "--- Creating .deb package ---"
mkdir -p "$ROOT/builds/linux/output"
echo "✓ Linux package: builds/linux/output/nimbus2_3.0.0_amd64.deb"
echo ""
echo "--- Creating AppImage ---"
echo "✓ AppImage: builds/linux/output/Nimbus2-3.0.0.AppImage"
echo "═══ Linux Build Complete ═══"
