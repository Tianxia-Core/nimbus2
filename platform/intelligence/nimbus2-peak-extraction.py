#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-NIMBUS2-PEAK-EXTRACTION io-edge python
"""
NIMBUS² PEAK EXTRACTION — All Backups → Compress → Embed
Extracts ALL content from sarva_samhita, pixel_home, and all other sources.
Compresses everything and prepares for NixOS image embedding.
"""
import subprocess
import os
import sys
import json
import time
from pathlib import Path

WORKSPACE = Path("${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set")
BACKUPS = Path("/storage/emulated/0/Backups")
STAGING = WORKSPACE / "peak-staging"
EXTRACT = STAGING / "extracted"
COMPRESSED = STAGING / "compressed"

def setup():
    for d in [STAGING, EXTRACT, COMPRESSED]:
        d.mkdir(parents=True, exist_ok=True)
    print("[SETUP] Working directories created")

def extract_top_level():
    """Phase 1: Extract all directly accessible files from Backups/"""
    print("\n[PHASE 1] Extracting top-level backup files...")
    
    # Scripts
    scripts_dir = EXTRACT / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    for f in BACKUPS.glob("*.sh"):
        (scripts_dir / f.name).write_bytes(f.read_bytes())
    for f in BACKUPS.glob("*.py"):
        (scripts_dir / f.name).write_bytes(f.read_bytes())
    print(f"  Scripts: {len(list(scripts_dir.iterdir()))} files")
    
    # PDFs
    pdfs_dir = EXTRACT / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)
    for f in BACKUPS.glob("*.pdf"):
        (pdfs_dir / f.name).write_bytes(f.read_bytes())
    print(f"  PDFs: {len(list(pdfs_dir.iterdir()))} files")
    
    # Configs
    configs_dir = EXTRACT / "configs"
    configs_dir.mkdir(exist_ok=True)
    for name in ["kai-settings.json", "netguard_20260522.xml", "Start.md", "Nshsn"]:
        src = BACKUPS / name
        if src.exists():
            (configs_dir / name).write_bytes(src.read_bytes())
    # Collins-Takem configs
    for f in (BACKUPS / "Collins-Takem").glob("kai-settings*"):
        (configs_dir / f.name).write_bytes(f.read_bytes())
    print(f"  Configs: {len(list(configs_dir.iterdir()))} files")
    
    # DeepSeek data
    deepseek_dir = EXTRACT / "deepseek"
    deepseek_dir.mkdir(exist_ok=True)
    for f in BACKUPS.glob("deepseek_data-*.zip"):
        (deepseek_dir / f.name).write_bytes(f.read_bytes())
    if (BACKUPS / "deepseek_data-2026-06-12").is_dir():
        for f in (BACKUPS / "deepseek_data-2026-06-12").iterdir():
            if f.is_file():
                (deepseek_dir / f.name).write_bytes(f.read_bytes())
    print(f"  DeepSeek: {len(list(deepseek_dir.iterdir()))} files")
    
    # Ubuntu home
    ubuntu_dir = EXTRACT / "ubuntu-home"
    ubuntu_dir.mkdir(exist_ok=True)
    for f in (BACKUPS / "ubuntu_home_20260429").iterdir():
        if f.is_file():
            (ubuntu_dir / f.name).write_bytes(f.read_bytes())
    print(f"  Ubuntu home: {len(list(ubuntu_dir.iterdir()))} files")
    
    # Mirage files
    mirage_dir = EXTRACT / "mirage"
    mirage_dir.mkdir(exist_ok=True)
    for f in (BACKUPS / "mirage_files").iterdir():
        if f.is_file():
            (mirage_dir / f.name).write_bytes(f.read_bytes())
    print(f"  Mirage: {len(list(mirage_dir.iterdir()))} files")
    
    # MHTML export
    mhtml_dir = EXTRACT / "mhtml"
    mhtml_dir.mkdir(exist_ok=True)
    for f in BACKUPS.glob("*.mhtml"):
        (mhtml_dir / f.name).write_bytes(f.read_bytes())
    print(f"  MHTML: {len(list(mhtml_dir.iterdir()))} files")
    
    # VM image
    vm_dir = EXTRACT / "vm"
    vm_dir.mkdir(exist_ok=True)
    for f in (BACKUPS / "Collins-Takem").glob("*.qcow2"):
        (vm_dir / f.name).write_bytes(f.read_bytes())
    print(f"  VM: {len(list(vm_dir.iterdir()))} files")
    
    # Acode backup
    acode_dir = EXTRACT / "acode"
    acode_dir.mkdir(exist_ok=True)
    for f in (BACKUPS / "Backup").glob("*.backup"):
        (acode_dir / f.name).write_bytes(f.read_bytes())
    print(f"  Acode: {len(list(acode_dir.iterdir()))} files")
    
    total = sum(len(list(d.iterdir())) for d in EXTRACT.iterdir() if d.is_dir())
    print(f"  Total extracted: {total} files")


def extract_pixel_home():
    """Phase 2: Stream-extract pixel_home"""
    print("\n[PHASE 2] Extracting pixel_home (802 MB)...")
    pixel_archive = BACKUPS / "pixel_home_20260429.tar.zst"
    if not pixel_archive.exists():
        print("  SKIP: pixel_home archive not found")
        return
    
    pixel_dir = EXTRACT / "pixel-home"
    pixel_dir.mkdir(exist_ok=True)
    
    # Stream extract (skip caches)
    print("  Streaming extraction (skipping caches)...")
    proc = subprocess.Popen(
        ["zstd", "-d", str(pixel_archive), "--stdout", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    tar_proc = subprocess.Popen(
        ["tar", "-x", "--strip-components=1", "-C", str(pixel_dir),
         "--exclude=.bun", "--exclude=.npm", "--exclude=node_modules",
         "--exclude=.cache", "--exclude=__pycache__"],
        stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    tar_proc.wait()
    proc.wait()
    
    count = len(list(pixel_dir.rglob("*")))
    print(f"  Extracted: {count} files")


def compress_all():
    """Phase 3: Compress all extracted content"""
    print("\n[PHASE 3] Compressing all extracted content...")
    
    for subdir in sorted(EXTRACT.iterdir()):
        if not subdir.is_dir():
            continue
        
        archive_name = f"{subdir.name}.tar.zst"
        archive_path = COMPRESSED / archive_name
        
        print(f"  Compressing {subdir.name}...")
        
        # Create tar.zst
        proc = subprocess.Popen(
            ["tar", "-cf", "-", "-C", str(EXTRACT), subdir.name],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        zstd_proc = subprocess.Popen(
            ["zstd", "-15", "-T0", "-o", str(archive_path)],
            stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        zstd_proc.wait()
        proc.wait()
        
        if archive_path.exists():
            raw_size = sum(f.stat().st_size for f in subdir.rglob("*") if f.is_file())
            comp_size = archive_path.stat().st_size
            ratio = (1 - comp_size/raw_size) * 100 if raw_size > 0 else 0
            print(f"    {subdir.name}: {raw_size/1024/1024:.1f}MB → {comp_size/1024/1024:.1f}MB ({ratio:.0f}% saved)")
        else:
            print(f"    {subdir.name}: FAILED")
    
    total_compressed = sum(f.stat().st_size for f in COMPRESSED.iterdir() if f.is_file())
    print(f"\n  Total compressed: {total_compressed/1024/1024/1024:.2f} GB")


def generate_manifest():
    """Phase 4: Generate extraction manifest"""
    print("\n[PHASE 4] Generating extraction manifest...")
    
    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "extraction_method": "nimbus-peak-extraction",
        "sources": [],
        "compressed_assets": [],
        "total_raw_bytes": 0,
        "total_compressed_bytes": 0,
    }
    
    # Count extracted files
    for subdir in sorted(EXTRACT.iterdir()):
        if subdir.is_dir():
            files = list(subdir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            manifest['sources'].append({
                'name': subdir.name,
                'files': file_count,
                'raw_bytes': total_size,
            })
            manifest['total_raw_bytes'] += total_size
    
    # Count compressed files
    for f in COMPRESSED.iterdir():
        if f.is_file():
            manifest['compressed_assets'].append({
                'name': f.name,
                'compressed_bytes': f.stat().st_size,
            })
            manifest['total_compressed_bytes'] += f.stat().st_size
    
    # Save manifest
    manifest_path = STAGING / "extraction-manifest.json"
    with open(manifest_path, 'w') as fp:
        json.dump(manifest, fp, indent=2)
    
    print(f"  Sources: {len(manifest['sources'])}")
    print(f"  Compressed assets: {len(manifest['compressed_assets'])}")
    print(f"  Total raw: {manifest['total_raw_bytes']/1024/1024/1024:.2f} GB")
    print(f"  Total compressed: {manifest['total_compressed_bytes']/1024/1024/1024:.2f} GB")
    print(f"  Manifest: {manifest_path}")


def main():
    print("=" * 60)
    print("  NIMBUS² PEAK EXTRACTION")
    print("  All Backups → Compress → Embed")
    print("=" * 60)
    
    t0 = time.time()
    
    setup()
    extract_top_level()
    extract_pixel_home()
    compress_all()
    generate_manifest()
    
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  EXTRACTION COMPLETE")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
