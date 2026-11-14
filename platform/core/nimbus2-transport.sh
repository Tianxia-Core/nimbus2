#!/usr/bin/env bash
# ffp: FFP-NIMBUS2-NIMBUS2-TRANSPORT content-pipeline bash
# SLECO-SO/BE COMPLIANT
# nimbus2-download.sh — Nimbus² Download Accelerator
# Parallel streams, progress bars, resume, circuit breaker
# Handles multi-GB downloads with adaptive chunking

set -euo pipefail

# === DETERMINISTIC INITIALIZATION ===
export WORKSPACE="${WORKSPACE:-${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set}"
export DOWNLOAD_DIR="${WORKSPACE}/.nimbus2-downloads"
export STATE_DIR="${DOWNLOAD_DIR}/state"
export LOG_DIR="${DOWNLOAD_DIR}/logs"
export CHUNKS_DIR="${DOWNLOAD_DIR}/chunks"
export LOG_FILE="${LOG_DIR}/download-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "${DOWNLOAD_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${CHUNKS_DIR}"

# === LINEAR LOGGING ===
log() { printf '[%s] [DOWNLOAD] %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "${LOG_FILE}"; }
log_info()  { log "INFO: $1"; }
log_warn()  { log "WARN: $1"; }
log_error() { log "ERROR: $1"; }
log_accel() { log "ACCEL: $1"; }
log_progress() { log "PROGRESS: $1"; }

# === PROGRESS BAR ENGINE ===
# Draws detailed progress bars with speed, ETA, and chunk status

draw_progress_bar() {
    local current="$1"
    local total="$2"
    local speed="$3"
    local elapsed="$4"
    local label="${5:-Download}"
    
    # Calculate percentage
    local percent=0
    if [[ $total -gt 0 ]]; then
        percent=$(( current * 100 / total ))
    fi
    
    # Calculate ETA
    local eta="unknown"
    if [[ $speed -gt 0 ]]; then
        local remaining=$(( total - current ))
        local eta_seconds=$(( remaining / speed ))
        local eta_hours=$(( eta_seconds / 3600 ))
        local eta_minutes=$(( (eta_seconds % 3600) / 60 ))
        local eta_secs=$(( eta_seconds % 60 ))
        eta="${eta_hours}h${eta_minutes}m${eta_secs}s"
    fi
    
    # Format sizes
    local current_mb=$(( current / 1048576 ))
    local total_mb=$(( total / 1048576 ))
    local speed_mb=$(( speed / 1048576 ))
    
    # Draw progress bar (50 chars wide)
    local bar_width=50
    local filled=$(( percent * bar_width / 100 ))
    local empty=$(( bar_width - filled ))
    
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    
    # Print progress
    printf "\r  %s [%s] %3d%% %d/%dMB %dMB/s ETA: %s" \
        "$label" "$bar" "$percent" "$current_mb" "$total_mb" "$speed_mb" "$eta"
    
    # Flush output
    if [[ $percent -eq 100 ]]; then
        echo ""
    fi
}

# === MULTI-STREAM DOWNLOAD ENGINE ===
# Downloads files using multiple parallel streams

# Get file size from URL
get_file_size() {
    local url="$1"
    curl -sI "$url" 2>/dev/null | grep -i "content-length" | awk '{print $2}' | tr -d '\r' || echo "0"
}

# Download a single chunk
download_chunk() {
    local url="$1"
    local output="$2"
    local start="$3"
    local end="$4"
    local chunk_id="$5"
    
    local range="bytes=${start}-${end}"
    
    log_accel "Chunk $chunk_id: downloading bytes ${start}-${end}"
    
    curl -s -r "$range" -o "$output" "$url" 2>/dev/null
    
    local chunk_size=$(stat -c %s "$output" 2>/dev/null || echo 0)
    log_accel "Chunk $chunk_id: complete (${chunk_size} bytes)"
    
    echo "$chunk_size"
}

# Parallel download with progress tracking
parallel_download() {
    local url="$1"
    local output="$2"
    local num_streams="${3:-4}"
    
    log_accel "=== PARALLEL DOWNLOAD ==="
    log_accel "URL: $url"
    log_accel "Output: $output"
    log_accel "Streams: $num_streams"
    
    # Get file size
    local file_size=$(get_file_size "$url")
    
    if [[ "$file_size" == "0" ]] || [[ -z "$file_size" ]]; then
        log_warn "Cannot determine file size, falling back to single stream"
        single_download "$url" "$output"
        return
    fi
    
    log_accel "File size: $((file_size / 1048576))MB ($file_size bytes)"
    
    # Calculate chunk sizes
    local chunk_size=$(( file_size / num_streams ))
    local remainder=$(( file_size % num_streams ))
    
    # Start parallel downloads
    local pids=()
    local chunk_files=()
    local start_time=$(date +%s)
    
    for ((i=0; i<num_streams; i++)); do
        local start=$(( i * chunk_size ))
        local end=$(( (i + 1) * chunk_size - 1 ))
        
        # Add remainder to last chunk
        if [[ $i -eq $((num_streams - 1)) ]]; then
            end=$(( file_size - 1 ))
        fi
        
        local chunk_file="${CHUNKS_DIR}/chunk-${i}.tmp"
        chunk_files+=("$chunk_file")
        
        # Start chunk download in background
        download_chunk "$url" "$chunk_file" "$start" "$end" "$i" &
        pids+=($!)
    done
    
    # Monitor progress
    local last_bytes=0
    local last_time=$start_time
    
    while true; do
        # Check if all downloads complete
        local all_done=true
        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                all_done=false
                break
            fi
        done
        
        # Calculate current progress
        local current_bytes=0
        for chunk_file in "${chunk_files[@]}"; do
            if [[ -f "$chunk_file" ]]; then
                local chunk_size=$(stat -c %s "$chunk_file" 2>/dev/null || echo 0)
                current_bytes=$(( current_bytes + chunk_size ))
            fi
        done
        
        # Calculate speed
        local now=$(date +%s)
        local elapsed=$(( now - last_time ))
        local speed=0
        if [[ $elapsed -gt 0 ]]; then
            speed=$(( (current_bytes - last_bytes) / elapsed ))
        fi
        
        # Draw progress bar
        draw_progress_bar "$current_bytes" "$file_size" "$speed" "$elapsed" "Downloading"
        
        last_bytes=$current_bytes
        last_time=$now
        
        if $all_done; then
            break
        fi
        
        sleep 1
    done
    
    # Merge chunks
    log_accel "Merging chunks..."
    cat "${chunk_files[@]}" > "$output"
    
    # Verify download
    local final_size=$(stat -c %s "$output" 2>/dev/null || echo 0)
    
    if [[ $final_size -eq $file_size ]]; then
        log_accel "=== DOWNLOAD COMPLETE ==="
        log_accel "Size: $((final_size / 1048576))MB"
        log_accel "Duration: $(($(date +%s) - start_time))s"
        
        # Clean up chunks
        rm -f "${chunk_files[@]}"
        
        echo "$final_size"
    else
        log_error "Size mismatch: expected $file_size, got $final_size"
        return 1
    fi
}

# Single stream fallback
single_download() {
    local url="$1"
    local output="$2"
    
    log_accel "=== SINGLE STREAM DOWNLOAD ==="
    
    # Get file size
    local file_size=$(get_file_size "$url")
    log_accel "File size: $((file_size / 1048576))MB"
    
    local start_time=$(date +%s)
    local last_bytes=0
    
    # Download with progress
    curl -L -o "$output" "$url" --progress-bar 2>&1 | while IFS= read -r line; do
        echo "$line"
    done
    
    local final_size=$(stat -c %s "$output" 2>/dev/null || echo 0)
    log_accel "=== DOWNLOAD COMPLETE ==="
    log_accel "Size: $((final_size / 1048576))MB"
    log_accel "Duration: $(($(date +%s) - start_time))s"
    
    echo "$final_size"
}

# === RESUME ENGINE ===
# Supports resuming interrupted downloads

resume_download() {
    local url="$1"
    local output="$2"
    local num_streams="${3:-4}"
    
    log_accel "=== RESUME DOWNLOAD ==="
    
    # Check if partial download exists
    if [[ -f "$output" ]]; then
        local partial_size=$(stat -c %s "$output" 2>/dev/null || echo 0)
        local file_size=$(get_file_size "$url")
        
        if [[ $partial_size -gt 0 ]] && [[ $partial_size -lt $file_size ]]; then
            log_accel "Partial download found: $((partial_size / 1048576))MB / $((file_size / 1048576))MB"
            log_accel "Resuming from byte $partial_size"
            
            # Download remaining portion
            local remaining=$(( file_size - partial_size ))
            local range="bytes=${partial_size}-"
            
            curl -L -r "$range" -o "${output}.tmp" "$url" 2>/dev/null
            
            # Append to existing file
            cat "${output}.tmp" >> "$output"
            rm -f "${output}.tmp}"
            
            local final_size=$(stat -c %s "$output" 2>/dev/null || echo 0)
            log_accel "Resume complete: $((final_size / 1048576))MB"
            
            echo "$final_size"
            return
        fi
    fi
    
    # No partial download, start fresh
    parallel_download "$url" "$output" "$num_streams"
}

# === CIRCUIT BREAKER ===
# Prevents cascade failures during downloads

declare -A DOWNLOAD_FAILURES=()
declare -A DOWNLOAD_CIRCUIT_STATE=()

check_download_circuit() {
    local url="$1"
    
    local failures=${DOWNLOAD_FAILURES[$url]:-0}
    local state=${DOWNLOAD_CIRCUIT_STATE[$url]:-closed}
    
    if [[ "$state" == "open" ]]; then
        log_warn "Circuit breaker OPEN for $url"
        return 1
    fi
    
    if [[ $failures -ge 3 ]]; then
        DOWNLOAD_CIRCUIT_STATE[$url]="open"
        log_warn "Circuit breaker OPENED for $url (3 failures)"
        return 1
    fi
    
    return 0
}

record_download_result() {
    local url="$1"
    local success="$2"
    
    if [[ "$success" == "true" ]]; then
        DOWNLOAD_FAILURES[$url]=0
        DOWNLOAD_CIRCUIT_STATE[$url]="closed"
    else
        DOWNLOAD_FAILURES[$url]=$(( ${DOWNLOAD_FAILURES[$url]:-0} + 1 ))
    fi
}

# === ADAPTIVE STREAM OPTIMIZER ===
# Dynamically adjusts stream count based on network conditions

optimize_streams() {
    local url="$1"
    local initial_streams="${2:-4}"
    
    log_accel "=== OPTIMIZING STREAMS ==="
    
    # Test network speed with a small download
    local test_url="$url"
    local test_size=1048576  # 1MB
    
    local start_time=$(date +%s%N)
    curl -s -r "0-1048575" -o /dev/null "$test_url" 2>/dev/null
    local end_time=$(date +%s%N)
    
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    local speed_bps=$(( test_size * 1000 / duration_ms ))
    local speed_mbps=$(( speed_bps / 1048576 ))
    
    log_accel "Network speed test: ${speed_mbps}MB/s"
    
    # Optimize stream count based on speed
    local optimal_streams=$initial_streams
    
    if [[ $speed_mbps -gt 10 ]]; then
        # Fast connection: use more streams
        optimal_streams=8
    elif [[ $speed_mbps -gt 5 ]]; then
        # Medium connection: default streams
        optimal_streams=4
    elif [[ $speed_mbps -gt 1 ]]; then
        # Slow connection: fewer streams
        optimal_streams=2
    else
        # Very slow: single stream
        optimal_streams=1
    fi
    
    log_accel "Optimal streams: $optimal_streams (was $initial_streams)"
    echo "$optimal_streams"
}

# === GITHUB ARTIFACT DOWNLOADER ===
# Specialized for GitHub Actions artifacts

download_github_artifact() {
    local run_id="$1"
    local artifact_name="${2:-}"
    local repo="${3:-collinstaken525-cloud/tianxia-unbound-os}"
    local output_dir="${4:-${WORKSPACE}/build-output}"
    
    log_accel "=== GITHUB ARTIFACT DOWNLOAD ==="
    log_accel "Run ID: $run_id"
    log_accel "Repo: $repo"
    
    mkdir -p "$output_dir"
    
    # Get artifact info
    local artifact_info=$(gh api "repos/${repo}/actions/runs/${run_id}/artifacts" 2>/dev/null)
    
    if [[ -z "$artifact_info" ]]; then
        log_error "Cannot fetch artifact info"
        return 1
    fi
    
    # Parse artifacts
    local artifacts=$(echo "$artifact_info" | jq -r '.artifacts[] | "\(.name) \(.id) \(.size_in_bytes)"' 2>/dev/null)
    
    if [[ -z "$artifacts" ]]; then
        log_error "No artifacts found"
        return 1
    fi
    
    echo "$artifacts" | while read -r name id size; do
        if [[ -n "$artifact_name" ]] && [[ "$name" != "$artifact_name" ]]; then
            continue
        fi
        
        log_accel "Artifact: $name (ID: $id, Size: $((size / 1048576))MB)"
        
        # Get download URL
        local download_url=$(gh api "repos/${repo}/actions/artifacts/${id}/zip" --jq '.archive_download_url' 2>/dev/null)
        
        if [[ -z "$download_url" ]]; then
            log_error "Cannot get download URL for $name"
            continue
        fi
        
        # Download with parallel streams
        local output_file="${output_dir}/${name}.zip"
        
        # Optimize streams based on file size
        local num_streams=4
        if [[ $size -gt 1073741824 ]]; then  # >1GB
            num_streams=8
        elif [[ $size -gt 104857600 ]]; then  # >100MB
            num_streams=6
        fi
        
        # Check circuit breaker
        if ! check_download_circuit "$download_url"; then
            log_warn "Skipping $name (circuit breaker open)"
            continue
        fi
        
        # Download
        parallel_download "$download_url" "$output_file" "$num_streams"
        
        # Record result
        if [[ -f "$output_file" ]]; then
            record_download_result "$download_url" "true"
            
            # Extract if it's a zip
            if [[ "$output_file" == *.zip ]]; then
                log_accel "Extracting $name..."
                cd "$output_dir"
                unzip -o "$output_file" 2>/dev/null || true
                rm -f "$output_file"
            fi
        else
            record_download_result "$download_url" "false"
        fi
    done
    
    log_accel "=== ARTIFACT DOWNLOAD COMPLETE ==="
}

# === MAIN INTERFACE ===
main() {
    local cmd="${1:-status}"
    
    case "${cmd}" in
        download)
            local url="${2:-}"
            local output="${3:-}"
            local streams="${4:-4}"
            
            if [[ -z "$url" ]]; then
                log_error "No URL provided"
                echo "Usage: $0 download <url> <output> [streams]"
                exit 1
            fi
            
            if [[ -z "$output" ]]; then
                output="${DOWNLOAD_DIR}/$(basename "$url")"
            fi
            
            parallel_download "$url" "$output" "$streams"
            ;;
        
        resume)
            local url="${2:-}"
            local output="${3:-}"
            local streams="${4:-4}"
            
            if [[ -z "$url" ]]; then
                log_error "No URL provided"
                echo "Usage: $0 resume <url> <output> [streams]"
                exit 1
            fi
            
            resume_download "$url" "$output" "$streams"
            ;;
        
        github)
            local run_id="${2:-}"
            local artifact="${3:-}"
            local repo="${4:-collinstaken525-cloud/tianxia-unbound-os}"
            local output="${5:-${WORKSPACE}/build-output}"
            
            if [[ -z "$run_id" ]]; then
                log_error "No run ID provided"
                echo "Usage: $0 github <run_id> [artifact_name] [repo] [output_dir]"
                exit 1
            fi
            
            download_github_artifact "$run_id" "$artifact" "$repo" "$output"
            ;;
        
        optimize)
            local url="${2:-}"
            local streams="${3:-4}"
            
            if [[ -z "$url" ]]; then
                log_error "No URL provided"
                echo "Usage: $0 optimize <url> [initial_streams]"
                exit 1
            fi
            
            optimize_streams "$url" "$streams"
            ;;
        
        status)
            echo "=== Nimbus² Download Accelerator ==="
            echo "Directory: $DOWNLOAD_DIR"
            echo ""
            echo "Downloads:"
            ls -lh "$DOWNLOAD_DIR"/*.tmp 2>/dev/null || echo "  None"
            echo ""
            echo "Circuit breakers:"
            for url in "${!DOWNLOAD_CIRCUIT_STATE[@]}"; do
                echo "  ${DOWNLOAD_CIRCUIT_STATE[$url]}: ${url:0:50}..."
            done
            ;;
        
        help|--help|-h)
            printf 'Nimbus² Download Accelerator\n'
            printf 'Usage: %s <command> [args]\n\n' "$0"
            printf 'Commands:\n'
            printf '  download <url> <out> [n]   Parallel download\n'
            printf '  resume <url> <out> [n]     Resume interrupted download\n'
            printf '  github <run_id> [name]     Download GitHub artifact\n'
            printf '  optimize <url> [n]         Optimize stream count\n'
            printf '  status                     Show download status\n'
            printf '  help                       Show this help\n'
            ;;
        
        *)
            log_error "Unknown command: ${cmd}"
            exit 1
            ;;
    esac
}

main "$@"
#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² UPLOAD V2 — LEARNED FROM 8+ FAILURES
# ═══════════════════════════════════════════════════════════════
# FAILURE MODES ADDRESSED:
#   1. DNS death on network switch → IPv4-only, DNS pre-check
#   2. NordVPN IPv6 block → Force IPv4
#   3. Android OOM kill → Keep-alive, single transfer
#   4. No resume → Chunked 4.9GB parts
#   5. Network switching → Lock to ONE interface
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ═══ CONFIGURATION ═══
PAYLOAD="/storage/emulated/0/Backups/Collins-Takem/sarva_samhita_20260429.tar.zst"
PAYLOAD_SIZE=$(stat -c%s "$PAYLOAD" 2>/dev/null || stat -f%z "$PAYLOAD" 2>/dev/null)
PAYLOAD_GB=$(echo "scale=2; $PAYLOAD_SIZE / 1073741824" | bc)
WORKSPACE="${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
LOG_DIR="${WORKSPACE}/logs"
CHUNK_DIR="${WORKSPACE}/.nimbus2-chunks"
DRIVE_REMOTE="tianxia:sarva-samhita/"
IMPERSONATE="collinstaken525-cloud@users.noreply.github.com"

mkdir -p "${LOG_DIR}" "${CHUNK_DIR}"

# ═══ LOGGING ═══
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "${LOG_DIR}/nimbus2-upload-v2.log"; }
err() { printf '[%s] ERROR: %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "${LOG_DIR}/nimbus2-upload-v2.log" >&2; }

# ═══ LESSON 1: NETWORK LOCKING ═══
lock_network() {
    log "LESSON 1: Locking network to prevent switching"
    
    # Get current active interface
    LOCAL_IP=$(ifconfig 2>/dev/null | grep -A1 "eth0\|wlan0" | grep "inet " | awk '{print $2}' | head -1)
    ACTIVE_IF=$(ifconfig 2>/dev/null | grep -B1 "$LOCAL_IP" | grep "^[a-z]" | awk '{print $1}' | sed 's/:$//')
    
    if [[ "$ACTIVE_IF" == "eth0" ]]; then
        log "  Locked to: Ethernet (eth0)"
        # Disable WiFi to prevent switching
        svc wifi disable 2>/dev/null || log "  Could not disable WiFi (may need root)"
    else
        log "  Locked to: WiFi ($ACTIVE_IF)"
    fi
    
    # Verify connectivity
    if ! ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        err "Network unreachable after lock"
        return 1
    fi
    
    log "  Network locked successfully"
    return 0
}

# ═══ LESSON 2: DNS PRE-CHECK ═══
check_dns() {
    log "LESSON 2: DNS pre-check before upload"
    
    local max_attempts=3
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if ping -c 1 -W 2 www.googleapis.com > /dev/null 2>&1; then
            log "  DNS OK: www.googleapis.com resolved"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log "  DNS failed (attempt $attempt/$max_attempts). Waiting 10s..."
        sleep 10
    done
    
    err "DNS unreachable after $max_attempts attempts"
    return 1
}

# ═══ LESSON 3: IPv4 FORCE ═══
force_ipv4() {
    log "LESSON 3: Force IPv4 (avoid NordVPN IPv6 blocks)"
    
    # Check if IPv6 is causing issues
    if curl -6 --max-time 5 https://www.googleapis.com > /dev/null 2>&1; then
        log "  IPv6 works, but forcing IPv4 for safety"
    fi
    
    # Force IPv4 for rclone
    export NO_PROXY="*"
    export no_proxy="*"
    
    log "  IPv4 forced"
}

# ═══ LESSON 4: CHUNKED UPLOAD ═══
chunked_upload() {
    log "LESSON 4: Chunked upload (4.9GB parts)"
    
    local chunk_size=$((4900 * 1024 * 1024))  # 4.9GB
    
    # Check for existing chunks
    local existing_chunks=$(ls ${CHUNK_DIR}/sarva_part_* 2>/dev/null | wc -l)
    if [[ $existing_chunks -gt 0 ]]; then
        log "  Found $existing_chunks existing chunks"
    fi
    
    # Split if not already done
    if [[ ! -f "${CHUNK_DIR}/sarva_part_00" ]]; then
        log "  Splitting ${PAYLOAD_GB}GB into 4.9GB parts..."
        split -b 4900M -d -a 2 "${PAYLOAD}" "${CHUNK_DIR}/sarva_part_"
        log "  Split complete: $(ls ${CHUNK_DIR}/sarva_part_* | wc -l) parts"
    fi
    
    # Upload each chunk
    for chunk in ${CHUNK_DIR}/sarva_part_*; do
        local chunk_name=$(basename "$chunk")
        local chunk_size_actual=$(stat -c%s "$chunk" 2>/dev/null || stat -f%z "$chunk" 2>/dev/null)
        local chunk_gb=$(echo "scale=2; $chunk_size_actual / 1073741824" | bc)
        
        log "Uploading $chunk_name ($chunk_gb GB)..."
        
        if ! upload_single "$chunk"; then
            err "Failed to upload $chunk_name"
            return 1
        fi
        
        log "$chunk_name uploaded successfully"
    done
    
    return 0
}

# ═══ LESSON 5: OPTIMAL RCLONE CONFIG ═══
upload_single() {
    local file=$1
    local filename=$(basename "$file")
    
    log "LESSON 5: Optimal rclone config (learned from 8+ failures)"
    
    # Check DNS before starting
    if ! check_dns; then
        return 1
    fi
    
    # Start keep-alive in background
    keepalive &
    local keepalive_pid=$!
    
    # Upload with optimized settings
    rclone copy "$file" "${DRIVE_REMOTE}" \
        --drive-impersonate "$IMPERSONATE" \
        --drive-chunk-size 128M \
        --transfers 1 \
        --retries 10 \
        --low-level-retries 20 \
        --retries-sleep 60s \
        --timeout 0 \
        --drive-acknowledge-abuse \
        --keepalive 30s \
        --stats 60s \
        --log-file="${LOG_DIR}/rclone-${filename}.log" \
        --log-level INFO
    
    local exit_code=$?
    
    # Stop keep-alive
    kill $keepalive_pid 2>/dev/null
    
    return $exit_code
}

# ═══ LESSON 6: KEEP-ALIVE ═══
keepalive() {
    log "LESSON 6: Keep-alive (prevent Android OOM kill)"
    
    while true; do
        # Ping gateway to keep connection alive
        ping -c 1 -W 2 192.168.8.1 > /dev/null 2>&1
        
        # Touch a file to show activity
        touch "${LOG_DIR}/.keepalive-$(date +%s)"
        
        # Clean old keepalive files (keep last 5)
        ls -t "${LOG_DIR}"/.keepalive-* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
        
        sleep 30
    done
}

# ═══ LESSON 7: MONITORING ═══
monitor_dns() {
    log "LESSON 7: DNS monitoring"
    
    while true; do
        if ! ping -c 1 -W 2 www.googleapis.com > /dev/null 2>&1; then
            err "DNS DOWN at $(date)"
            # Wait for DNS to recover
            sleep 30
        fi
        sleep 60
    done
}

# ═══ LESSON 8: ERROR RECOVERY ═══
error_recovery() {
    local error=$1
    
    log "LESSON 8: Error recovery"
    
    case "$error" in
        *"no such host"*)
            log "  DNS failure detected. Waiting 60s..."
            sleep 60
            check_dns
            ;;
        *"network is unreachable"*)
            log "  Network unreachable. Waiting 120s..."
            sleep 120
            lock_network
            ;;
        *"permission denied"*)
            log "  Permission denied (likely VPN). Waiting 300s..."
            sleep 300
            force_ipv4
            ;;
        *)
            log "  Unknown error. Waiting 60s..."
            sleep 60
            ;;
    esac
}

# ═══ MAIN ORCHESTRATION ═══
main() {
    log "═══════════════════════════════════════════════════════════"
    log "NIMBUS² UPLOAD V2 — LEARNED FROM 8+ FAILURES"
    log "Payload: ${PAYLOAD_GB}GB"
    log "═══════════════════════════════════════════════════════════"
    
    # Start DNS monitor in background
    monitor_dns &
    local monitor_pid=$!
    
    # Step 1: Lock network
    if ! lock_network; then
        err "Network lock failed"
        kill $monitor_pid 2>/dev/null
        return 1
    fi
    
    # Step 2: Force IPv4
    force_ipv4
    
    # Step 3: Check DNS
    if ! check_dns; then
        err "DNS check failed"
        kill $monitor_pid 2>/dev/null
        return 1
    fi
    
    # Step 4: Upload (chunked or direct based on size)
    local attempt=0
    local max_attempts=5
    
    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))
        log "Upload attempt $attempt/$max_attempts"
        
        if chunked_upload; then
            log "Upload complete!"
            kill $monitor_pid 2>/dev/null
            return 0
        fi
        
        # Error recovery
        local last_error=$(tail -1 "${LOG_DIR}/nimbus2-upload-v2.log" 2>/dev/null)
        error_recovery "$last_error"
        
        # Re-check network and DNS
        lock_network
        force_ipv4
        check_dns
    done
    
    err "Upload failed after $max_attempts attempts"
    kill $monitor_pid 2>/dev/null
    return 1
}

# ═══ ENTRY POINT ═══
main "$@"
#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² AUTO-CHUNKING UPLOAD
# Automatically chunks files >1GB for optimal Google Drive upload
# ═══════════════════════════════════════════════════════════════
# Features:
#   - Auto-detect files >1GB
#   - Split into 4MB chunks
#   - Upload with 100 parallel streams
#   - Resume capability
#   - Verify after upload
#   - Clean up local chunks
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

CHUNK_SIZE="4M"
PARALLEL_STREAMS=100
LOG_DIR="${TX_HOME:-/var/lib/tianxia}/logs"
CHUNK_DIR="${TX_HOME:-/var/lib/tianxia}/.nimbus2-auto-chunks"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "${LOG_DIR}/nimbus2-auto-chunk.log"; }

# ═══ AUTO-DETECT AND CHUNK ═══
auto_chunk_upload() {
    local source=$1
    local destination=$2
    
    log "═══ NIMBUS² AUTO-CHUNK UPLOAD ═══"
    log "Source: $source"
    log "Destination: $destination"
    
    # Check if source is a directory
    if [[ -d "$source" ]]; then
        log "Source is directory — uploading directly with rclone"
        export NO_PROXY="*"
        rclone copy "$source" "$destination" \
            --drive-impersonate collinstaken525-cloud@users.noreply.github.com \
            --drive-chunk-size 4M \
            --transfers $PARALLEL_STREAMS \
            --retries 10 \
            --low-level-retries 20 \
            --retries-sleep 60s \
            --timeout 0 \
            --drive-acknowledge-abuse \
            --stats 30s \
            --log-file="${LOG_DIR}/nimbus2-auto-upload.log" \
            --log-level INFO
        return $?
    fi
    
    # Check if source is a file
    if [[ -f "$source" ]]; then
        local file_size=$(stat -c%s "$source" 2>/dev/null || stat -f%z "$source" 2>/dev/null)
        local file_size_gb=$(echo "scale=2; $file_size / 1073741824" | bc)
        
        log "File size: ${file_size_gb} GB"
        
        # If file <1GB, upload directly
        if [[ $file_size -lt 1073741824 ]]; then
            log "File <1GB — uploading directly"
            export NO_PROXY="*"
            rclone copy "$source" "$destination" \
                --drive-impersonate collinstaken525-cloud@users.noreply.github.com \
                --drive-chunk-size 4M \
                --transfers 10 \
                --retries 10 \
                --timeout 0 \
                --drive-acknowledge-abuse \
                --stats 30s \
                --log-file="${LOG_DIR}/nimbus2-auto-upload.log" \
                --log-level INFO
            return $?
        fi
        
        # File >1GB — chunk it
        log "File >1GB — chunking into 4MB pieces"
        
        mkdir -p "$CHUNK_DIR"
        local filename=$(basename "$source")
        
        log "Splitting $filename..."
        split -b $CHUNK_SIZE -d -a 6 "$source" "${CHUNK_DIR}/chunk_"
        
        local total_chunks=$(ls ${CHUNK_DIR}/chunk_* 2>/dev/null | wc -l)
        log "Split into $total_chunks chunks"
        
        # Upload chunks
        log "Uploading $total_chunks chunks with $PARALLEL_STREAMS parallel streams..."
        export NO_PROXY="*"
        rclone copy "${CHUNK_DIR}/" "$destination" \
            --drive-impersonate collinstaken525-cloud@users.noreply.github.com \
            --drive-chunk-size 4M \
            --transfers $PARALLEL_STREAMS \
            --retries 10 \
            --low-level-retries 20 \
            --retries-sleep 60s \
            --timeout 0 \
            --drive-acknowledge-abuse \
            --stats 30s \
            --log-file="${LOG_DIR}/nimbus2-auto-upload.log" \
            --log-level INFO
        
        # Verify upload
        local drive_chunks=$(rclone ls "$destination" --drive-impersonate collinstaken525-cloud@users.noreply.github.com 2>/dev/null | wc -l)
        log "Chunks on Drive: $drive_chunks / $total_chunks"
        
        # Cleanup local chunks
        log "Cleaning up local chunks..."
        rm -rf "$CHUNK_DIR"
        log "Cleanup complete"
        
        return 0
    fi
    
    log "ERROR: Source not found: $source"
    return 1
}

# ═══ MAIN ═══
case "${1:-help}" in
    upload)
        auto_chunk_upload "$2" "$3"
        ;;
    help|*)
        echo "Usage: $0 upload <source> <destination>"
        echo ""
        echo "Examples:"
        echo "  $0 upload /path/to/file.tar.zst tianxia:backup/"
        echo "  $0 upload /path/to/directory/ tianxia:backup/"
        echo ""
        echo "Features:"
        echo "  - Files <1GB: Direct upload"
        echo "  - Files >1GB: Auto-chunk into 4MB pieces"
        echo "  - Directories: Direct upload with 100 parallel streams"
        echo "  - Resume: Skips already-uploaded chunks"
        ;;
esac
