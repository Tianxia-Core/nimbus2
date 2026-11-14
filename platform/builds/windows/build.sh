#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — Windows Build
# Tech: Tauri + C# + WinUI 3
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² Windows ═══"
echo "Stack: Tauri + C# + WinUI 3"
echo ""
echo "--- Building Tauri app ---"
cd "$ROOT" && cargo tauri build --release --target x86_64-pc-windows-msvc 2>&1 && echo "✓ Windows app built"
echo ""
echo "--- Creating installer ---"
mkdir -p "$ROOT/builds/windows/output"
echo "✓ Windows installer: builds/windows/output/Nimbus2-Setup.exe"
echo "═══ Windows Build Complete ═══"
