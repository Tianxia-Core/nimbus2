#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — TUI Build
# Tech: ratatui (Rust) + Nim
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² TUI ═══"
echo "Stack: ratatui (Rust) + Nim"
echo ""
echo "--- Building Rust TUI ---"
cd "$ROOT" && cargo build --release --bin nimbus2-tui 2>&1 && echo "✓ Rust TUI built"
echo ""
echo "--- Building Nim TUI ---"
cd "$ROOT/languages/nim" && nimble build -d:release 2>&1 && echo "✓ Nim TUI built"
echo ""
echo "--- Combining ---"
mkdir -p "$ROOT/builds/tui/output"
cp "$ROOT/target/release/nimbus2-tui" "$ROOT/builds/tui/output/" 2>/dev/null
echo "✓ TUI binary: builds/tui/output/nimbus2-tui"
echo "═══ TUI Build Complete ═══"
