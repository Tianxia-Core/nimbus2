#!/bin/bash
# ffp: FFP-NIMBUS2-NIMBUS2-EXTRACT content-pipeline bash
# NIMBUS² DIRECT EXTRACTION — ASURA MODE
# Skip full scan. Extract targeted patterns directly from archive.
# Uses tar --include for streaming extraction without index.

set -euo pipefail

ARCHIVE="/storage/emulated/0/Backups/Collins-Takem/sarva_samhita_20260429.tar.zst"
PIXEL="/storage/emulated/0/Backups/pixel_home_20260429.tar.zst"
REPO="${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
WORK="$REPO/backup-incorporation"
EXTRACT="$WORK/extracted"

echo "═══════════════════════════════════════════════════════"
echo "  NIMBUS² DIRECT EXTRACTION — ASURA MODE"
echo "═══════════════════════════════════════════════════════"

mkdir -p "$EXTRACT"/{tier_a,tier_b,pixel_home}

# ═══════════════════════════════════════════════════════
# PHASE 1: TIER A — Critical files (extract by pattern)
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 1: Tier A (Critical) ──"

echo "[A1] Session logs + LLM manifests..."
zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_a" \
    --wildcards '*/session-ses_*' \
    --wildcards '*/llm_harmonized*' \
    --wildcards '*/.maha-shield*' \
    --wildcards '*/gen_rest.py' \
    --wildcards '*/patrol_loop.sh' \
    --wildcards '*/.profile' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

echo "[A2] Security scripts..."
zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_a" \
    --wildcards '*/sarva-samhita.sh' \
    --wildcards '*/generate-fortress.sh' \
    --wildcards '*/chronoprator-deploy.sh' \
    --wildcards '*/hardenclean.sh' \
    --wildcards '*/migrate_to_nixyr*' \
    --wildcards '*/nixyr_migration*' \
    --wildcards '*/secure_mirage_installer.sh' \
    --wildcards '*/sovereign-fortress-nexus.sh' \
    --wildcards '*/nixyr_sys.md' \
    --wildcards '*/numsf_core.py' \
    --wildcards '*/netguard_*' \
    --wildcards '*/Gemma4_E4B*' \
    --wildcards '*/ubuntupixel_backup.sh' \
    --wildcards '*/qubesforen.sh' \
    --wildcards '*/mirage_installer*' \
    --wildcards '*/secure_mirage_mtp*' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

echo "[A3] KAI settings..."
zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_a" \
    --wildcards '*/kai-settings*' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

echo "[A4] Forensic evidence..."
zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_a" \
    --wildcards '*/forensic*' \
    --wildcards '*/evidence*' \
    --wildcards '*/case_*' \
    --wildcards '*/bt_forensics*' \
    --wildcards '*/forensic_shell*' \
    --wildcards '*/detection_rules*' \
    --wildcards '*/path_monitor*' \
    --wildcards '*/yubikey_guardian*' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

echo "[A5] System support logs..."
zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_a" \
    --wildcards '*/syssupprob/*' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

TIER_A_COUNT=$(find "$EXTRACT/tier_a" -type f 2>/dev/null | wc -l)
echo "[A] Total Tier A files: $TIER_A_COUNT"

# ═══════════════════════════════════════════════════════
# PHASE 2: TIER B — Zig Forward system
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 2: Tier B (Zig Forward System) ──"

zstd -d "$ARCHIVE" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/tier_b" \
    --wildcards '*/.zig_forward/*.zig' \
    --wildcards '*/.zig_forward/*.sh' \
    --wildcards '*/.zig_forward/*.txt' \
    --wildcards '*/.zig_forward/*.log' \
    --wildcards '*/.zig_forward/build.zig' \
    2>/dev/null && echo "  ✅ Zig source extracted" || echo "  ⚠️ Partial"

TIER_B_COUNT=$(find "$EXTRACT/tier_b" -type f 2>/dev/null | wc -l)
echo "[B] Total Tier B files: $TIER_B_COUNT"

# ═══════════════════════════════════════════════════════
# PHASE 3: PIXEL HOME — Full extraction (small archive)
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 3: Pixel Home (801MB) ──"

zstd -d "$PIXEL" --stdout -q 2>/dev/null | tar -x --strip-components=1 \
    -C "$EXTRACT/pixel_home" \
    --wildcards '*/.zig_forward/*.zig' \
    --wildcards '*/.zig_forward/*.sh' \
    --wildcards '*/.zig_forward/*.txt' \
    --wildcards '*/session-ses_*' \
    --wildcards '*/llm_harmonized*' \
    --wildcards '*/gen_rest.py' \
    --wildcards '*/patrol_loop.sh' \
    --wildcards '*/.maha-shield*' \
    --wildcards '*/kai-settings*' \
    2>/dev/null && echo "  ✅ Done" || echo "  ⚠️ Partial"

PIXEL_COUNT=$(find "$EXTRACT/pixel_home" -type f 2>/dev/null | wc -l)
echo "[P] Total Pixel files: $PIXEL_COUNT"

# ═══════════════════════════════════════════════════════
# PHASE 4: COLLINS-TAKEM top-level (non-archive)
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 4: Collins-Takem direct files ──"

cp /storage/emulated/0/Backups/Collins-Takem/kai-settings.json "$EXTRACT/tier_a/" 2>/dev/null && echo "  ✅ kai-settings.json"
cp /storage/emulated/0/Backups/Collins-Takem/emulation_map.qcow2 "$EXTRACT/tier_a/" 2>/dev/null && echo "  ✅ emulation_map.qcow2"
cp /storage/emulated/0/Backups/Collins-Takem/collins_paragon_20260429.tar.zst "$EXTRACT/tier_a/" 2>/dev/null && echo "  ✅ collins_paragon"

# ═══════════════════════════════════════════════════════
# PHASE 5: Copy top-level backup scripts
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 5: Top-level scripts ──"

for f in /storage/emulated/0/Backups/*.sh /storage/emulated/0/Backups/*.py /storage/emulated/0/Backups/*.md /storage/emulated/0/Backups/*.json; do
    [ -f "$f" ] && cp "$f" "$EXTRACT/tier_a/" 2>/dev/null && echo "  ✅ $(basename "$f")"
done

# ═══════════════════════════════════════════════════════
# PHASE 6: Copy mirage_files
# ═══════════════════════════════════════════════════════
echo ""
echo "── PHASE 6: Mirage firewall ──"

cp -r /storage/emulated/0/Backups/mirage_files/* "$EXTRACT/tier_b/" 2>/dev/null && echo "  ✅ Mirage files copied" || echo "  ⚠️ Partial"

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  EXTRACTION COMPLETE"
echo "═══════════════════════════════════════════════════════"

TOTAL=$(find "$EXTRACT" -type f 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$EXTRACT" 2>/dev/null | awk '{print $1}')

echo "  Total files: $TOTAL"
echo "  Total size:  $TOTAL_SIZE"
echo ""
echo "  Tier A: $(find "$EXTRACT/tier_a" -type f 2>/dev/null | wc -l) files"
echo "  Tier B: $(find "$EXTRACT/tier_b" -type f 2>/dev/null | wc -l) files"
echo "  Pixel:  $(find "$EXTRACT/pixel_home" -type f 2>/dev/null | wc -l) files"
echo ""
echo "  All extracted to: $EXTRACT"
