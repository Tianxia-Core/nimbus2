#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ffp: FFP-NIMBUS2-NIMBUS2-DEVICE-BACKUP content-pipeline bash
# ═══════════════════════════════════════════════════════════════
# NIMBUS² DEVICE BACKUP — Pixel 8 Pro Optimized
# ═══════════════════════════════════════════════════════════════
# Preserves:
#   - Profiles
#   - App data
#   - Settings
#   - SSH keys
#   - Workspace
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

WORKSPACE="${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
LOG_DIR="${WORKSPACE}/logs"
BACKUP_REMOTE="tianxia:pixel8pro-backup/"
IMPERSONATE="collinstaken525-cloud@users.noreply.github.com"
CHUNK_SIZE="4M"
TRANSFERS=225

mkdir -p "${LOG_DIR}"

log() { printf '[%s] [BACKUP] %s\n' "$(date +%H:%M:%S)" "$1" | tee -a "${LOG_DIR}/device-backup.log"; }

# ═══ CRITICAL DATA PATHS ═══
declare -A BACKUP_PATHS=(
    ["profiles"]="${TX_HOME:-/var/lib/tianxia}/.config"
    ["app-data"]="${TX_HOME:-/var/lib/tianxia}/.local"
    ["settings"]="${TX_HOME:-/var/lib/tianxia}/.termux"
    ["ssh-keys"]="${TX_HOME:-/var/lib/tianxia}/.ssh"
    ["workspace"]="${TX_WORKSPACE:-/var/lib/tianxia}"
    ["opencode"]="${TX_HOME:-/var/lib/tianxia}/.config/opencode"
    ["secure-vault"]="${TX_HOME:-/var/lib/tianxia}/.secure-vault"
    ["rclone-config"]="${TX_HOME:-/var/lib/tianxia}/.config/rclone"
)

# ═══ BACKUP FUNCTION ═══
backup_component() {
    local name=$1
    local path=$2
    
    if [[ -d "$path" ]]; then
        log "Backing up $name: $path"
        export NO_PROXY="*"
        rclone copy "$path" "${BACKUP_REMOTE}${name}/" \
            --drive-impersonate "$IMPERSONATE" \
            --drive-chunk-size "$CHUNK_SIZE" \
            --transfers $TRANSFERS \
            --retries 10 \
            --low-level-retries 20 \
            --retries-sleep 60s \
            --timeout 0 \
            --drive-acknowledge-abuse \
            --stats 30s \
            --log-file="${LOG_DIR}/backup-${name}.log" \
            --log-level INFO
        log "$name backup complete"
    else
        log "WARNING: $path not found, skipping"
    fi
}

# ═══ MAIN ═══
log "═══ NIMBUS² DEVICE BACKUP ═══"
log "Target: Pixel 8 Pro"
log "Remote: $BACKUP_REMOTE"

# Backup each component
for name in "${!BACKUP_PATHS[@]}"; do
    backup_component "$name" "${BACKUP_PATHS[$name]}"
done

# Create backup manifest
log "Creating backup manifest..."
cat > "${LOG_DIR}/backup-manifest.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "device": "Pixel 8 Pro",
    "backup_remote": "$BACKUP_REMOTE",
    "components": {
$(for name in "${!BACKUP_PATHS[@]}"; do
    echo "        \"$name\": \"${BACKUP_PATHS[$name]}\","
done)
    },
    "status": "complete"
}
EOF

log "Backup manifest created"
log "═══ BACKUP COMPLETE ═══"
