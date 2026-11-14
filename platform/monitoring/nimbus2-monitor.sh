#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ffp: FFP-NIMBUS2-NIMBUS2-MONITOR content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² LIVE PROGRESS MONITOR — REAL-TIME STATS
# ═══════════════════════════════════════════════════════════════
# Features:
#   - Real-time progress bar
#   - Speed calculation (instant + average)
#   - ETA calculation
#   - Source/Destination display
#   - Network health monitoring
#   - Stall detection
#   - Auto-restart on failure
#   - All lessons learned incorporated
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ═══ CONFIGURATION ═══
LOG_DIR="${TX_HOME:-/var/lib/tianxia}/logs"
UPLOAD_LOG="${LOG_DIR}/nimax-correct.log"
STATS_FILE="${LOG_DIR}/nimbus2-stats.json"
HISTORY_FILE="${LOG_DIR}/nimbus2-history.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ═══ PROGRESS BAR ENGINE ═══
draw_progress() {
    local percent=$1
    local width=50
    local filled=$((percent * width / 100))
    local empty=$((width - filled))
    
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    
    printf "[${GREEN}%s${NC}] %s%%" "$bar" "$percent"
}

# ═══ SPEED CALCULATION ═══
calculate_speed() {
    local current_bytes=$1
    local last_bytes=$2
    local elapsed_seconds=$3
    
    if [[ $elapsed_seconds -gt 0 ]]; then
        local speed_bps=$(( (current_bytes - last_bytes) / elapsed_seconds ))
        echo "$speed_bps"
    else
        echo "0"
    fi
}

# ═══ ETA CALCULATION ═══
calculate_eta() {
    local remaining_bytes=$1
    local speed_bps=$2
    
    if [[ $speed_bps -gt 0 ]]; then
        local eta_seconds=$(( remaining_bytes / speed_bps ))
        local hours=$((eta_seconds / 3600))
        local minutes=$(( (eta_seconds % 3600) / 60 ))
        printf "%dh %dm" $hours $minutes
    else
        echo "calculating..."
    fi
}

# ═══ FORMAT BYTES ═══
format_bytes() {
    local bytes=$1
    
    if [[ $bytes -ge 1073741824 ]]; then
        echo "$(echo "scale=2; $bytes/1073741824" | bc) GB"
    elif [[ $bytes -ge 1048576 ]]; then
        echo "$(echo "scale=2; $bytes/1048576" | bc) MB"
    elif [[ $bytes -ge 1024 ]]; then
        echo "$(echo "scale=2; $bytes/1024" | bc) KB"
    else
        echo "${bytes} B"
    fi
}

# ═══ NETWORK HEALTH ═══
check_network() {
    local status="OK"
    local latency="0"
    
    if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        latency=$(ping -c 1 -W 2 8.8.8.8 2>/dev/null | grep "time=" | awk -F'=' '{print $2}' | awk '{print $1}')
    else
        status="DOWN"
    fi
    
    if ping -c 1 -W 2 www.googleapis.com > /dev/null 2>&1; then
        status="${status} | DNS:OK"
    else
        status="${status} | DNS:FAIL"
    fi
    
    echo "${status} (${latency}ms)"
}

# ═══ STALL DETECTION ═══
detect_stall() {
    local current_bytes=$1
    local last_bytes=$2
    local stall_count=$3
    
    if [[ $current_bytes -eq $last_bytes ]]; then
        echo $((stall_count + 1))
    else
        echo "0"
    fi
}

# ═══ MAIN MONITOR LOOP ═══
monitor() {
    local last_bytes=0
    local last_time=$(date +%s)
    local stall_count=0
    local total_checks=0
    local peak_speed=0
    
    while true; do
        # Parse rclone log
        local progress_line=$(grep "Transferred.*GiB\|Transferred.*MiB" "$UPLOAD_LOG" 2>/dev/null | tail -1)
        
        if [[ -n "$progress_line" ]]; then
            # Extract values
            local transferred=$(echo "$progress_line" | awk -F'[/,]' '{print $1}' | grep -oP '[\d.]+')
            local total=$(echo "$progress_line" | awk -F'[/,]' '{print $2}' | grep -oP '[\d.]+')
            local percent=$(echo "$progress_line" | awk -F'[/,]' '{print $3}' | grep -oP '[\d.]+')
            local speed_str=$(echo "$progress_line" | awk -F'[/,]' '{print $4}' | grep -oP '[\d.]+')
            local eta_str=$(echo "$progress_line" | awk -F'[/,]' '{print $5}' | grep -oP '[\d.hms]+')
            
            # Convert to bytes
            local transferred_bytes=0
            local total_bytes=0
            
            if [[ "$progress_line" == *"GiB"* ]]; then
                transferred_bytes=$(echo "$transferred * 1073741824" | bc 2>/dev/null | cut -d. -f1)
                total_bytes=$(echo "$total * 1073741824" | bc 2>/dev/null | cut -d. -f1)
            elif [[ "$progress_line" == *"MiB"* ]]; then
                transferred_bytes=$(echo "$transferred * 1048576" | bc 2>/dev/null | cut -d. -f1)
                total_bytes=$(echo "$total * 1048576" | bc 2>/dev/null | cut -d. -f1)
            fi
            
            local remaining_bytes=$((total_bytes - transferred_bytes))
            
            # Calculate speed
            local current_time=$(date +%s)
            local elapsed=$((current_time - last_time))
            local speed_bps=0
            
            if [[ $elapsed -gt 0 && $transferred_bytes -gt $last_bytes ]]; then
                speed_bps=$(( (transferred_bytes - last_bytes) / elapsed ))
            fi
            
            # Track peak speed
            if [[ $speed_bps -gt $peak_speed ]]; then
                peak_speed=$speed_bps
            fi
            
            # Detect stalls
            stall_count=$(detect_stall $transferred_bytes $last_bytes $stall_count)
            
            # Clear screen and draw
            clear
            printf "\n"
            printf "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}\n"
            printf "${BOLD}${CYAN}║   NIMBUS² REAL-TIME PROGRESS MONITOR                        ║${NC}\n"
            printf "${BOLD}${CYAN}║   $(date '+%Y-%m-%d %H:%M:%S %Z')                                  ║${NC}\n"
            printf "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
            printf "\n"
            
            # Progress bar
            printf "  Progress: "
            draw_progress "${percent:-0}"
            printf "\n\n"
            
            # Stats
            printf "  ${BOLD}Source:${NC}      /storage/emulated/0/Backups/Collins-Takem/sarva_samhita_20260429.tar.zst\n"
            printf "  ${BOLD}Destination:${NC} tianxia:sarva-samhita/ (Google Drive)\n"
            printf "  ${BOLD}Impersonate:${NC} collinstaken525-cloud@users.noreply.github.com\n"
            printf "\n"
            
            printf "  ${BOLD}Transferred:${NC} $(format_bytes $transferred_bytes) / $(format_bytes $total_bytes)\n"
            printf "  ${BOLD}Remaining:${NC}   $(format_bytes $remaining_bytes)\n"
            printf "  ${BOLD}Speed:${NC}       $(format_bytes $speed_bps)/s (peak: $(format_bytes $peak_speed)/s)\n"
            printf "  ${BOLD}ETA:${NC}         $eta_str\n"
            printf "\n"
            
            # Network
            printf "  ${BOLD}Network:${NC}     $(check_network)\n"
            printf "  ${BOLD}Interface:${NC}   $(ifconfig 2>/dev/null | grep -A1 "eth0\|wlan0" | grep "inet " | awk '{print $NF}' | head -1)\n"
            printf "\n"
            
            # Process status
            local rclone_count=$(pgrep -f rclone | wc -l)
            local ireb_count=$(pgrep -f ireb | wc -l)
            printf "  ${BOLD}Processes:${NC}   rclone:${rclone_count} | IREB:${ireb_count}\n"
            printf "\n"
            
            # Stall warning
            if [[ $stall_count -ge 3 ]]; then
                printf "  ${RED}${BOLD}⚠ STALL DETECTED${NC} — No progress for ${stall_count} checks\n"
            fi
            
            # Speed trend
            if [[ $speed_bps -gt 0 ]]; then
                local speed_mbps=$(echo "scale=2; $speed_bps/1048576" | bc 2>/dev/null || echo "0")
                if (( $(echo "$speed_mbps > 2.0" | bc -l 2>/dev/null || echo 0) )); then
                    printf "  ${GREEN}● EXCELLENT${NC} — Speed above 2 MB/s\n"
                elif (( $(echo "$speed_mbps > 1.0" | bc -l 2>/dev/null || echo 0) )); then
                    printf "  ${YELLOW}● GOOD${NC} — Speed above 1 MB/s\n"
                else
                    printf "  ${RED}● SLOW${NC} — Speed below 1 MB/s\n"
                fi
            fi
            
            printf "\n"
            printf "${DIM}  Refreshing every 10s... (Ctrl+C to exit)${NC}\n"
            
            # Update tracking
            last_bytes=$transferred_bytes
            last_time=$current_time
            total_checks=$((total_checks + 1))
        else
            # No progress data yet
            clear
            printf "\n"
            printf "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}\n"
            printf "${BOLD}${CYAN}║   NIMBUS² REAL-TIME PROGRESS MONITOR                        ║${NC}\n"
            printf "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
            printf "\n"
            printf "  ${YELLOW}Waiting for upload to start...${NC}\n"
            printf "\n"
            printf "  ${BOLD}Source:${NC}      /storage/emulated/0/Backups/Collins-Takem/sarva_samhita_20260429.tar.zst\n"
            printf "  ${BOLD}Destination:${NC} tianxia:sarva-samhita/ (Google Drive)\n"
            printf "\n"
            printf "  ${BOLD}Network:${NC}     $(check_network)\n"
            printf "\n"
        fi
        
        sleep 10
    done
}

# ═══ ENTRY POINT ═══
case "${1:-monitor}" in
    monitor) monitor ;;
    status)
        echo "=== NIMBUS² UPLOAD STATUS ==="
        echo ""
        grep "Transferred.*GiB\|Transferred.*MiB" "$UPLOAD_LOG" 2>/dev/null | tail -1
        echo ""
        echo "Network: $(check_network)"
        echo "Processes: rclone $(pgrep -f rclone | wc -l) | IREB $(pgrep -f ireb | wc -l)"
        ;;
    *) echo "Usage: $0 {monitor|status}" ;;
esac
#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² CONTINUOUS UPLOAD GUARDIAN
# 250 streams, zero pauses, until completion
# ═══════════════════════════════════════════════════════════════

LOG="${TX_HOME:-/var/lib/tianxia}/logs/nimbus2-guardian.log"
CHUNK_DIR="${TX_HOME:-/var/lib/tianxia}/.nimbus2-model-chunks"
DEST="tianxia:llm-models/"
IMPERSONATE="collinstaken525-cloud@users.noreply.github.com"
STREAMS=250
STALL_TIMEOUT=60  # seconds to wait before restart
CHECK_INTERVAL=30 # seconds between checks

log() { printf '[%s] [GUARDIAN] %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "$LOG"; }

# ═══ START UPLOAD ═══
start_upload() {
    export NO_PROXY="*"
    nohup rclone copy "${CHUNK_DIR}/" "${DEST}" \
        --drive-impersonate "${IMPERSONATE}" \
        --drive-chunk-size 4M \
        --transfers ${STREAMS} \
        --retries 10 \
        --low-level-retries 20 \
        --retries-sleep 60s \
        --timeout 0 \
        --drive-acknowledge-abuse \
        --stats 10s \
        --log-file="${LOG%.log}-upload.log" \
        --log-level INFO > /dev/null 2>&1 &
    echo $!
}

# ═══ CHECK IF UPLOAD COMPLETE ═══
check_complete() {
    # Check if all chunks are on Drive
    local local_count=$(ls ${CHUNK_DIR}/ 2>/dev/null | wc -l)
    local drive_count=$(rclone ls "${DEST}" --drive-impersonate "${IMPERSONATE}" 2>/dev/null | wc -l)
    
    if [[ $drive_count -ge $local_count && $local_count -gt 0 ]]; then
        return 0  # Complete
    fi
    return 1  # Not complete
}

# ═══ MAIN GUARDIAN LOOP ═══
log "═══ CONTINUOUS UPLOAD GUARDIAN ONLINE ═══"
log "Streams: ${STREAMS}"
log "Chunk dir: ${CHUNK_DIR}"
log "Destination: ${DEST}"

# Start initial upload
UPLOAD_PID=$(start_upload)
log "Initial upload started (PID: ${UPLOAD_PID})"

LAST_CHUNKS=0
STALL_COUNT=0

while true; do
    sleep ${CHECK_INTERVAL}
    
    # Check if upload process is alive
    if ! kill -0 ${UPLOAD_PID} 2>/dev/null; then
        log "Upload process died — restarting"
        UPLOAD_PID=$(start_upload)
        STALL_COUNT=0
        continue
    fi
    
    # Check chunks on Drive
    CURRENT_CHUNKS=$(rclone ls "${DEST}" --drive-impersonate "${IMPERSONATE}" 2>/dev/null | wc -l)
    
    # Check for stall
    if [[ $CURRENT_CHUNKS -eq $LAST_CHUNKS ]]; then
        STALL_COUNT=$((STALL_COUNT + 1))
        if [[ $STALL_COUNT -ge 3 ]]; then
            log "STALL DETECTED (${STALL_COUNT}x) — restarting upload"
            kill ${UPLOAD_PID} 2>/dev/null
            sleep 2
            UPLOAD_PID=$(start_upload)
            STALL_COUNT=0
        fi
    else
        STALL_COUNT=0
    fi
    
    LAST_CHUNKS=$CURRENT_CHUNKS
    
    # Check completion
    if check_complete; then
        log "═══ UPLOAD COMPLETE ═══"
        log "Total chunks: ${CURRENT_CHUNKS}"
        log "All models uploaded to ${DEST}"
        exit 0
    fi
    
    # Log progress every 5 minutes
    if [[ $((STALL_COUNT % 10)) -eq 0 ]]; then
        log "Progress: ${CURRENT_CHUNKS} chunks on Drive"
    fi
done
#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² AUTO-MONITOR — Engages automatically on upload start
# ═══════════════════════════════════════════════════════════════

MONITOR="${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set/nimbus2-live-monitor.sh"
LOG_DIR="${TX_HOME:-/var/lib/tianxia}/logs"
LAST_RCLONE_COUNT=0

while true; do
    # Check for rclone processes
    current_rclone=$(pgrep -f "rclone" | wc -l)
    
    # If rclone just started or is running
    if [[ $current_rclone -gt 0 && $LAST_RCLONE_COUNT -eq 0 ]]; then
        echo "[$(date)] Rclone detected — starting live monitor"
        $MONITOR &
        MONITOR_PID=$!
    fi
    
    # If rclone stopped
    if [[ $current_rclone -eq 0 && $LAST_RCLONE_COUNT -gt 0 ]]; then
        echo "[$(date)] Rclone stopped — stopping monitor"
        kill $MONITOR_PID 2>/dev/null
    fi
    
    LAST_RCLONE_COUNT=$current_rclone
    sleep 5
done
