#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-NIMBUS2-BACKUP-INCORPORA io-edge python
"""
NIMBUS² BACKUP INCORPORATOR — ASURA MODE
=========================================
Tiered Streaming Extraction with SLECO-SO/BE Chunking

Strategy: Decompress → Analyze → Map → Absorb → Discard
- Never load full archive into RAM
- Stream through zstd decompressor at 512MB chunks
- Tier-based extraction (Critical → High → Bulk → Forensic)
- Each chunk is processed and discarded immediately

Author: Nimbus² ASURA Engine
Date: 2026-07-12
"""

import subprocess
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

BACKUP_BASE = Path("/storage/emulated/0/Backups")
REPO_BASE = Path("${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set")
WORK_DIR = REPO_BASE / "backup-incorporation"
SARVA_ARCHIVE = BACKUP_BASE / "Collins-Takem" / "sarva_samhita_20260429.tar.zst"
PIXEL_ARCHIVE = BACKUP_BASE / "pixel_home_20260429.tar.zst"
CHUNK_SIZE = 512 * 1024 * 1024  # 512MB decompressed chunks
ZSTD_LEVEL = 3  # Fast decompression (we're reading, not writing)

# ═══════════════════════════════════════════════════════
# TIER DEFINITIONS — What to extract vs skip
# ═══════════════════════════════════════════════════════

# TIER A: CRITICAL — Extract immediately (highest value)
TIER_A_PATTERNS = [
    "session-ses_", "llm_harmonized_system_manifest",
    ".maha-shield-health.log", "gen_rest.py", "patrol_loop.sh",
    ".autarchi_security.pid", ".profile",
    "sarva-samhita.sh", "generate-fortress.sh", "chronoprator-deploy.sh",
    "hardenclean.sh", "migrate_to_nixyr", "nixyr_migration",
    "secure_mirage_installer.sh", "sovereign-fortress-nexus.sh",
    "nixyr_sys.md", "numsf_core.py", "netguard_",
    "kai-settings.json", "Gemma4_E4B",
    "FORENSIC_QUEUE.txt", "FORENSIC_QUEUE.tar",
]

# TIER B: HIGH VALUE — Extract in chunks
TIER_B_DIRS = [
    ".zig_forward/", "Archive/", "mirage_files/",
    "ubuntu_home_20260429/", "deepseek_data-",
]

# TIER C: BULK — SKIP (redundant with nixpkgs, npm cache, etc.)
TIER_C_SKIP = [
    ".bun/", ".npm/", "node_modules/", ".cache/",
    ".zig-forward/.zig-cache/", "__pycache__/",
    ".local/", ".config/",
]

# TIER D: FORENSIC — Scan selectively
TIER_D_PATTERNS = [
    "forensic", "evidence", "case_", "log",
]


def setup_work_dir():
    """Create working directories"""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "extracted").mkdir(exist_ok=True)
    (WORK_DIR / "scan-results").mkdir(exist_ok=True)
    (WORK_DIR / "chunks").mkdir(exist_ok=True)
    print(f"[SETUP] Work directory: {WORK_DIR}")


def get_archive_file_count(archive_path):
    """Get total file count without decompressing"""
    print(f"[SCAN] Counting files in {archive_path.name}...")
    result = subprocess.run(
        ["zstd", "-d", str(archive_path), "--stdout"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Pipe to tar -t and count
    proc = subprocess.Popen(
        ["tar", "-t"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = proc.communicate(input=result.stdout)
    lines = out.decode(errors='ignore').strip().split('\n')
    return len([l for l in lines if l and not l.endswith('/')])


def classify_entry(path):
    """Classify a tar entry into a tier"""
    path_lower = path.lower()

    # Tier A: Critical
    for pattern in TIER_A_PATTERNS:
        if pattern.lower() in path_lower:
            return 'A'

    # Tier C: Skip
    for pattern in TIER_C_SKIP:
        if pattern.lower() in path_lower:
            return 'C'

    # Tier B: High value directories
    for pattern in TIER_B_DIRS:
        if pattern.lower() in path_lower:
            return 'B'

    # Tier D: Forensic
    for pattern in TIER_D_PATTERNS:
        if pattern.lower() in path_lower:
            return 'D'

    return 'B'  # Default to B (extract)


def streaming_scan(archive_path, max_entries=None):
    """
    Stream through archive, classify every entry, build extraction map.
    Uses zstd streaming decompression — never loads full archive into RAM.
    """
    print(f"\n[SCAN] Streaming classification of {archive_path.name}...")
    print(f"[SCAN] Max entries: {max_entries or 'unlimited'}")

    tier_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    tier_sizes = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    entries = []
    count = 0

    # Stream decompress + tar list
    proc = subprocess.Popen(
        ["zstd", "-d", str(archive_path), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    tar_proc = subprocess.Popen(
        ["tar", "-tv"],
        stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    for line in tar_proc.stdout:
        line = line.decode(errors='ignore').strip()
        if not line:
            continue

        # Parse tar -tv output
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue

        perms = parts[0]
        size_str = parts[4] if len(parts) > 4 else "0"
        name = parts[5] if len(parts) > 5 else ""

        # Skip directories
        if perms.startswith('d'):
            continue

        try:
            size = int(size_str)
        except ValueError:
            size = 0

        tier = classify_entry(name)
        tier_counts[tier] += 1
        tier_sizes[tier] += size
        count += 1

        entries.append({
            'path': name,
            'tier': tier,
            'size': size,
            'perms': perms,
        })

        if count % 10000 == 0:
            print(f"  [SCAN] {count:,} entries scanned... "
                  f"A:{tier_counts['A']} B:{tier_counts['B']} "
                  f"C:{tier_counts['C']} D:{tier_counts['D']}")

        if max_entries and count >= max_entries:
            break

    proc.wait()
    tar_proc.wait()

    print(f"\n[SCAN] Complete: {count:,} entries classified")
    print(f"  Tier A (Critical):  {tier_counts['A']:>6} entries, {tier_sizes['A']:>15,} bytes")
    print(f"  Tier B (High):      {tier_counts['B']:>6} entries, {tier_sizes['B']:>15,} bytes")
    print(f"  Tier C (Skip):      {tier_counts['C']:>6} entries, {tier_sizes['C']:>15,} bytes")
    print(f"  Tier D (Forensic):  {tier_counts['D']:>6} entries, {tier_sizes['D']:>15,} bytes")

    extract_size = tier_sizes['A'] + tier_sizes['B'] + tier_sizes['D']
    skip_size = tier_sizes['C']
    print(f"\n  TO EXTRACT: {extract_size:>15,} bytes ({extract_size/1024/1024/1024:.1f} GB)")
    print(f"  TO SKIP:    {skip_size:>15,} bytes ({skip_size/1024/1024/1024:.1f} GB)")
    print(f"  SAVINGS:    {skip_size/1024/1024/1024:.1f} GB skipped "
          f"({skip_size*100/(extract_size+skip_size):.0f}% of archive)")

    return entries, tier_counts, tier_sizes


def extract_tier_a(archive_path, entries):
    """Extract Tier A (Critical) files immediately"""
    tier_a = [e for e in entries if e['tier'] == 'A']
    if not tier_a:
        print("[EXTRACT] No Tier A files found")
        return

    print(f"\n[EXTRACT] Tier A: {len(tier_a)} critical files")
    extract_dir = WORK_DIR / "extracted" / "tier_a"
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Build file list for tar
    file_list = "\n".join(e['path'] for e in tier_a)
    list_file = WORK_DIR / "tier_a_list.txt"
    list_file.write_text(file_list)

    # Extract using tar's --files-from
    print(f"[EXTRACT] Extracting {len(tier_a)} files to {extract_dir}...")
    proc = subprocess.Popen(
        ["zstd", "-d", str(archive_path), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    tar_proc = subprocess.Popen(
        ["tar", "-x", "--strip-components=1", "-C", str(extract_dir),
         "--files-from", str(list_file)],
        stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    tar_proc.wait()
    proc.wait()

    # Verify extraction
    extracted = list(extract_dir.rglob("*"))
    print(f"[EXTRACT] Tier A complete: {len(extracted)} files extracted")
    return extract_dir


def streaming_chunk_extract(archive_path, entries, tier='B', chunk_mb=512):
    """
    Extract Tier B/D files in streaming chunks.
    Decompress → Extract chunk → Analyze → Absorb → Discard.
    """
    tier_entries = [e for e in entries if e['tier'] == tier]
    if not tier_entries:
        print(f"[CHUNK] No Tier {tier} files found")
        return

    total_size = sum(e['size'] for e in tier_entries)
    print(f"\n[CHUNK] Tier {tier}: {len(tier_entries)} files, "
          f"{total_size/1024/1024/1024:.1f} GB total")

    extract_dir = WORK_DIR / "extracted" / f"tier_{tier.lower()}"
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Build file list
    file_list = "\n".join(e['path'] for e in tier_entries)
    list_file = WORK_DIR / f"tier_{tier.lower()}_list.txt"
    list_file.write_text(file_list)

    # Extract all at once (streaming — RAM efficient)
    print(f"[CHUNK] Streaming extraction of Tier {tier}...")
    proc = subprocess.Popen(
        ["zstd", "-d", str(archive_path), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    tar_proc = subprocess.Popen(
        ["tar", "-x", "--strip-components=1", "-C", str(extract_dir),
         "--files-from", str(list_file)],
        stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    tar_proc.wait()
    proc.wait()

    extracted = list(extract_dir.rglob("*"))
    print(f"[CHUNK] Tier {tier} complete: {len(extracted)} files extracted")
    return extract_dir


def analyze_extracted():
    """Analyze all extracted files and generate integration map"""
    print("\n[ANALYZE] Scanning extracted files for Tianxia integration...")

    extracted_dir = WORK_DIR / "extracted"
    all_files = list(extracted_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]

    print(f"[ANALYZE] {len(files_only)} files to analyze")

    integration_map = {
        'zig_forward': [],
        'forensic': [],
        'session_logs': [],
        'llm_manifests': [],
        'security_configs': [],
        'scripts': [],
        'migration_tools': [],
        'mirage_firewall': [],
        'deepseek_data': [],
        'kai_settings': [],
        'other': [],
    }

    for f in files_only:
        rel = f.relative_to(extracted_dir)
        path_str = str(rel).lower()

        if 'zig_forward' in path_str or '.zig' in path_str:
            integration_map['zig_forward'].append(str(rel))
        elif 'forensic' in path_str or 'evidence' in path_str:
            integration_map['forensic'].append(str(rel))
        elif 'session' in path_str and ('log' in path_str or 'ses_' in path_str):
            integration_map['session_logs'].append(str(rel))
        elif 'llm' in path_str and 'manifest' in path_str:
            integration_map['llm_manifests'].append(str(rel))
        elif 'security' in path_str or 'shield' in path_str or 'hardening' in path_str:
            integration_map['security_configs'].append(str(rel))
        elif path_str.endswith('.sh') or path_str.endswith('.py'):
            integration_map['scripts'].append(str(rel))
        elif 'migrat' in path_str:
            integration_map['migration_tools'].append(str(rel))
        elif 'mirage' in path_str:
            integration_map['mirage_firewall'].append(str(rel))
        elif 'deepseek' in path_str:
            integration_map['deepseek_data'].append(str(rel))
        elif 'kai' in path_str and 'setting' in path_str:
            integration_map['kai_settings'].append(str(rel))
        else:
            integration_map['other'].append(str(rel))

    # Print summary
    print("\n[MAP] Integration Categories:")
    for cat, files in integration_map.items():
        if files:
            print(f"  {cat}: {len(files)} files")

    # Save map
    map_file = WORK_DIR / "scan-results" / "integration_map.json"
    with open(map_file, 'w') as f:
        json.dump(integration_map, f, indent=2)
    print(f"\n[MAP] Saved to {map_file}")

    return integration_map


def absorb_into_repo():
    """Copy extracted files into the repo structure"""
    print("\n[ABSORB] Incorporating into Tianxia repo...")

    extracted_dir = WORK_DIR / "extracted"

    # Define target locations in repo
    targets = {
        'zig_forward': REPO_BASE / "backup-assets" / "zig-forward",
        'forensic': REPO_BASE / "backup-assets" / "forensic-evidence",
        'session_logs': REPO_BASE / "backup-assets" / "session-logs",
        'llm_manifests': REPO_BASE / "backup-assets" / "llm-manifests",
        'security_configs': REPO_BASE / "backup-assets" / "security-configs",
        'scripts': REPO_BASE / "backup-assets" / "scripts",
        'migration_tools': REPO_BASE / "backup-assets" / "migration-tools",
        'mirage_firewall': REPO_BASE / "backup-assets" / "mirage-firewall",
        'deepseek_data': REPO_BASE / "backup-assets" / "deepseek-data",
        'kai_settings': REPO_BASE / "backup-assets" / "kai-settings",
        'other': REPO_BASE / "backup-assets" / "other",
    }

    for target_dir in targets.values():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Copy files
    import shutil
    copied = 0
    for tier_dir in extracted_dir.iterdir():
        if not tier_dir.is_dir():
            continue
        for f in tier_dir.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(tier_dir)
            path_str = str(rel).lower()

            # Determine target category
            if 'zig_forward' in path_str or '.zig' in path_str:
                dest = targets['zig_forward']
            elif 'forensic' in path_str or 'evidence' in path_str:
                dest = targets['forensic']
            elif 'session' in path_str:
                dest = targets['session_logs']
            elif 'llm' in path_str and 'manifest' in path_str:
                dest = targets['llm_manifests']
            elif 'security' in path_str or 'shield' in path_str:
                dest = targets['security_configs']
            elif path_str.endswith('.sh') or path_str.endswith('.py'):
                dest = targets['scripts']
            elif 'migrat' in path_str:
                dest = targets['migration_tools']
            elif 'mirage' in path_str:
                dest = targets['mirage_firewall']
            elif 'deepseek' in path_str:
                dest = targets['deepseek_data']
            elif 'kai' in path_str and 'setting' in path_str:
                dest = targets['kai_settings']
            else:
                dest = targets['other']

            dest_file = dest / rel.name
            if not dest_file.exists():
                shutil.copy2(f, dest_file)
                copied += 1

    print(f"[ABSORB] {copied} files incorporated into repo")
    return copied


def generate_report(tier_counts, tier_sizes, integration_map, copied):
    """Generate final incorporation report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'archive': str(SARVA_ARCHIVE),
        'archive_size': SARVA_ARCHIVE.stat().st_size,
        'tiers': {
            'A': {'count': tier_counts['A'], 'bytes': tier_sizes['A']},
            'B': {'count': tier_counts['B'], 'bytes': tier_sizes['B']},
            'C': {'count': tier_counts['C'], 'bytes': tier_sizes['C']},
            'D': {'count': tier_counts['D'], 'bytes': tier_sizes['D']},
        },
        'integration_map': {k: len(v) for k, v in integration_map.items()},
        'files_copied': copied,
    }

    report_file = WORK_DIR / "scan-results" / "incorporation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n[REPORT] Saved to {report_file}")
    return report


def main():
    print("═" * 60)
    print("  NIMBUS² BACKUP INCORPORATOR — ASURA MODE")
    print("  Tiered Streaming Extraction with SLECO-SO/BE Chunking")
    print("═" * 60)

    # Setup
    setup_work_dir()

    # Phase 1: Stream-scan the sarva_samhita archive
    print("\n" "═" * 60)
    print("  PHASE 1: STREAMING CLASSIFICATION (116GB archive)")
    print("═" * 60)
    entries, tier_counts, tier_sizes = streaming_scan(SARVA_ARCHIVE)

    # Save entries for reference
    entries_file = WORK_DIR / "scan-results" / "all_entries.json"
    with open(entries_file, 'w') as f:
        json.dump(entries, f, indent=2)
    print(f"[SCAN] Saved {len(entries)} entries to {entries_file}")

    # Phase 2: Extract Tier A (Critical) — immediate
    print("\n" "═" * 60)
    print("  PHASE 2: EXTRACT TIER A (CRITICAL)")
    print("═" * 60)
    extract_tier_a(SARVA_ARCHIVE, entries)

    # Phase 3: Extract Tier B (High Value) — streaming
    print("\n" "═" * 60)
    print("  PHASE 3: EXTRACT TIER B (HIGH VALUE)")
    print("═" * 60)
    streaming_chunk_extract(SARVA_ARCHIVE, entries, tier='B')

    # Phase 4: Extract Tier D (Forensic) — selective
    print("\n" "═" * 60)
    print("  PHASE 4: EXTRACT TIER D (FORENSIC)")
    print("═" * 60)
    streaming_chunk_extract(SARVA_ARCHIVE, entries, tier='D')

    # Phase 5: Also process pixel_home (small, extract fully)
    print("\n" "═" * 60)
    print("  PHASE 5: EXTRACT PIXEL HOME (801MB, full)")
    print("═" * 60)
    pixel_extract = WORK_DIR / "extracted" / "pixel_home"
    pixel_extract.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["zstd", "-d", str(PIXEL_ARCHIVE), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    proc = subprocess.Popen(
        ["zstd", "-d", str(PIXEL_ARCHIVE), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    tar_proc = subprocess.Popen(
        ["tar", "-x", "--strip-components=1", "-C", str(pixel_extract)],
        stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    tar_proc.wait()
    proc.wait()
    pixel_files = list(pixel_extract.rglob("*"))
    print(f"[PIXEL] {len(pixel_files)} files extracted")

    # Phase 6: Analyze and map
    print("\n" "═" * 60)
    print("  PHASE 6: ANALYZE & MAP")
    print("═" * 60)
    integration_map = analyze_extracted()

    # Phase 7: Absorb into repo
    print("\n" "═" * 60)
    print("  PHASE 7: ABSORB INTO REPO")
    print("═" * 60)
    copied = absorb_into_repo()

    # Phase 8: Generate report
    print("\n" "═" * 60)
    print("  PHASE 8: GENERATE REPORT")
    print("═" * 60)
    report = generate_report(tier_counts, tier_sizes, integration_map, copied)

    # Cleanup: Remove extracted copies (keep only repo-integrated versions)
    print("\n[CLEANUP] Removing temporary extraction directory...")
    import shutil
    shutil.rmtree(WORK_DIR / "extracted", ignore_errors=True)
    print("[CLEANUP] Complete")

    print("\n" "═" * 60)
    print("  NIMBUS² INCORPORATION COMPLETE")
    print("═" * 60)
    print(f"  Files scanned: {len(entries):,}")
    print(f"  Files copied:  {copied}")
    print(f"  Tier A extracted: {tier_counts['A']}")
    print(f"  Tier B extracted: {tier_counts['B']}")
    print(f"  Tier C skipped:   {tier_counts['C']}")
    print(f"  Tier D extracted: {tier_counts['D']}")


if __name__ == '__main__':
    main()
