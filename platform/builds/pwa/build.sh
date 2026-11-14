#!/bin/bash
# ffp: FFP-NIMBUS2-BUILD content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# Nimbus² DAS — PWA Build
# Tech: Next.js / SvelteKit / SolidStart
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "═══ Building Nimbus² PWA ═══"
echo "Stack: Next.js + SvelteKit + SolidStart"
echo ""
echo "--- Building Next.js ---"
cd "$ROOT/platforms/pwa/nextjs" && npm run build 2>&1 && echo "✓ Next.js built"
echo ""
echo "--- Building SvelteKit ---"
cd "$ROOT/platforms/pwa/sveltekit" && npm run build 2>&1 && echo "✓ SvelteKit built"
echo ""
echo "--- Building SolidStart ---"
cd "$ROOT/platforms/pwa/solidstart" && npm run build 2>&1 && echo "✓ SolidStart built"
echo ""
echo "--- Creating PWA ---"
mkdir -p "$ROOT/builds/pwa/output"
echo "✓ PWA: builds/pwa/output/"
echo "═══ PWA Build Complete ═══"
