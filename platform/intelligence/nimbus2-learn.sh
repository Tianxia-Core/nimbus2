#!/usr/bin/env bash
# ffp: FFP-NIMBUS2-NIMBUS2-LEARN content-pipeline bash
# SLECO-SO/BE COMPLIANT
# nimbus2-learn.sh — Persistent Build Learning System
# Tracks success/failure per platform, learns optimal build locations
# Auto-skips after 3 consecutive failures
# Targets 90% success rate for builds >500K lines

# === DETERMINISTIC INITIALIZATION ===
export WORKSPACE="${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
export LOG_DIR="${WORKSPACE}/logs"
export RULES_FILE="${WORKSPACE}/.nimbus2-rules.json"
export STATS_FILE="${WORKSPACE}/.nimbus2-stats.json"
export LOG_FILE="${LOG_DIR}/nimbus2-learn-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "${LOG_DIR}"

# === LINEAR LOGGING ===
log() { printf '[%s] [%s] %s\n' "$(date +%H:%M:%S)" "$1" "$2" | tee -a "${LOG_FILE}"; }
log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_learn() { log "LEARN" "$@"; }

# === PERSISTENT RULES ===
init_rules() {
    if [[ ! -f "$RULES_FILE" ]]; then
        cat > "$RULES_FILE" << 'EOF'
{
  "platforms": {
    "nixbuild.net": {
      "success": 0,
      "failure": 0,
      "consecutive_failures": 0,
      "best_for": [],
      "worst_for": [],
      "skip_until": null
    },
    "github-actions": {
      "success": 0,
      "failure": 0,
      "consecutive_failures": 0,
      "best_for": [],
      "worst_for": [],
      "skip_until": null
    },
    "local-pixel8": {
      "success": 0,
      "failure": 0,
      "consecutive_failures": 0,
      "best_for": [],
      "worst_for": [],
      "skip_until": null
    }
  },
  "components": {
    "zlib-ng": {
      "best_platform": null,
      "attempts": {},
      "skip_after_failures": 3
    },
    "zstd": {
      "best_platform": null,
      "attempts": {},
      "skip_after_failures": 3
    },
    "zram-generator": {
      "best_platform": null,
      "attempts": {},
      "skip_after_failures": 3
    },
    "zvbi": {
      "best_platform": null,
      "attempts": {},
      "skip_after_failures": 3
    },
    "zxing-cpp": {
      "best_platform": null,
      "attempts": {},
      "skip_after_failures": 3
    }
  },
  "rules": {
    "max_consecutive_failures": 3,
    "target_success_rate": 0.90,
    "min_lines_for_learning": 500000
  },
  "last_updated": null
}
EOF
        log_learn "Rules file created"
    fi
}

# === PERSISTENT STATS ===
init_stats() {
    if [[ ! -f "$STATS_FILE" ]]; then
        cat > "$STATS_FILE" << 'EOF'
{
  "total_builds": 0,
  "successful_builds": 0,
  "failed_builds": 0,
  "skipped_builds": 0,
  "success_rate": 0.0,
  "build_history": []
}
EOF
        log_learn "Stats file created"
    fi
}

# === LEARN FROM BUILD RESULT ===
learn_from_result() {
    local platform="$1"
    local component="$2"
    local result="$3"  # success or failure
    local lines="$4"   # lines of code
    
    log_learn "Learning from: platform=$platform component=$component result=$result lines=$lines"
    
    # Update platform stats
    local success_count=$(jq -r ".platforms.\"$platform\".success // 0" "$RULES_FILE")
    local failure_count=$(jq -r ".platforms.\"$platform\".failure // 0" "$RULES_FILE")
    local consecutive=$(jq -r ".platforms.\"$platform\".consecutive_failures // 0" "$RULES_FILE")
    
    if [[ "$result" == "success" ]]; then
        success_count=$((success_count + 1))
        consecutive=0
        log_learn "  Platform $platform: SUCCESS (total: $success_count)"
    else
        failure_count=$((failure_count + 1))
        consecutive=$((consecutive + 1))
        log_learn "  Platform $platform: FAILURE (total: $failure_count, consecutive: $consecutive)"
    fi
    
    # Update rules
    jq ".platforms.\"$platform\".success = $success_count | .platforms.\"$platform\".failure = $failure_count | .platforms.\"$platform\".consecutive_failures = $consecutive | .last_updated = \"$(date -Iseconds)\"" "$RULES_FILE" > "${RULES_FILE}.tmp" && mv "${RULES_FILE}.tmp" "$RULES_FILE"
    
    # Update component stats
    local component_attempts=$(jq -r ".components.\"$component\".attempts.\"$platform\" // 0" "$RULES_FILE")
    component_attempts=$((component_attempts + 1))
    jq ".components.\"$component\".attempts.\"$platform\" = $component_attempts" "$RULES_FILE" > "${RULES_FILE}.tmp" && mv "${RULES_FILE}.tmp" "$RULES_FILE"
    
    # Learn best platform for component
    if [[ "$result" == "success" ]]; then
        local current_best=$(jq -r ".components.\"$component\".best_platform // \"null\"" "$RULES_FILE")
        if [[ "$current_best" == "null" ]]; then
            jq ".components.\"$component\".best_platform = \"$platform\"" "$RULES_FILE" > "${RULES_FILE}.tmp" && mv "${RULES_FILE}.tmp" "$RULES_FILE"
            log_learn "  Learned: $component best built on $platform"
        fi
    fi
    
    # Update stats
    local total=$(jq -r ".total_builds // 0" "$STATS_FILE")
    local successful=$(jq -r ".successful_builds // 0" "$STATS_FILE")
    local failed=$(jq -r ".failed_builds // 0" "$STATS_FILE")
    
    total=$((total + 1))
    if [[ "$result" == "success" ]]; then
        successful=$((successful + 1))
    else
        failed=$((failed + 1))
    fi
    
    local success_rate=$(echo "scale=2; $successful * 100 / $total" | bc 2>/dev/null || echo "0")
    
    jq ".total_builds = $total | .successful_builds = $successful | .failed_builds = $failed | .success_rate = $success_rate" "$STATS_FILE" > "${STATS_FILE}.tmp" && mv "${STATS_FILE}.tmp" "$STATS_FILE"
    
    log_learn "  Stats: total=$total success=$successful failed=$failed rate=$success_rate%"
}

# === CHECK IF SHOULD SKIP ===
should_skip() {
    local platform="$1"
    local component="$2"
    
    # Check platform consecutive failures
    local consecutive=$(jq -r ".platforms.\"$platform\".consecutive_failures // 0" "$RULES_FILE")
    local max_failures=$(jq -r ".rules.max_consecutive_failures // 3" "$RULES_FILE")
    
    if [[ $consecutive -ge $max_failures ]]; then
        log_warn "SKIPPING: $platform has $consecutive consecutive failures (max: $max_failures)"
        return 0
    fi
    
    # Check component skip threshold
    local attempts=$(jq -r ".components.\"$component\".attempts.\"$platform\" // 0" "$RULES_FILE")
    local skip_after=$(jq -r ".components.\"$component\".skip_after_failures // 3" "$RULES_FILE")
    
    if [[ $attempts -ge $skip_after ]]; then
        local successes=$(jq -r ".components.\"$component\".attempts.\"$platform\" // 0" "$RULES_FILE")
        if [[ $successes -eq 0 ]]; then
            log_warn "SKIPPING: $component failed $attempts times on $platform"
            return 0
        fi
    fi
    
    return 1
}

# === GET BEST PLATFORM ===
get_best_platform() {
    local component="$1"
    
    local best=$(jq -r ".components.\"$component\".best_platform // \"null\"" "$RULES_FILE")
    
    if [[ "$best" != "null" ]]; then
        log_learn "Best platform for $component: $best"
        echo "$best"
        return 0
    fi
    
    # Default: try platforms in order of success rate
    local platforms=("local-pixel8" "nixbuild.net" "github-actions")
    for platform in "${platforms[@]}"; do
        if ! should_skip "$platform" "$component"; then
            log_learn "Default platform for $component: $platform"
            echo "$platform"
            return 0
        fi
    done
    
    log_warn "No platform available for $component"
    echo "none"
    return 1
}

# === SHOW RULES ===
show_rules() {
    log_learn "=== PERSISTENT RULES ==="
    cat "$RULES_FILE" | jq '.'
    log_learn "=== RULES COMPLETE ==="
}

# === SHOW STATS ===
show_stats() {
    log_learn "=== BUILD STATS ==="
    cat "$STATS_FILE" | jq '.'
    log_learn "=== STATS COMPLETE ==="
}

# === MAIN ===
main() {
    local cmd="${1:-help}"
    
    log "NIMBUS²-LEARN" "=== NIMBUS² PERSISTENT LEARNING SYSTEM ==="
    
    # Initialize files
    init_rules
    init_stats
    
    case "${cmd}" in
        learn)
            learn_from_result "$2" "$3" "$4" "$5"
            ;;
        skip)
            if should_skip "$2" "$3"; then
                echo "SKIP"
            else
                echo "BUILD"
            fi
            ;;
        best)
            get_best_platform "$2"
            ;;
        rules)
            show_rules
            ;;
        stats)
            show_stats
            ;;
        help|--help|-h)
            printf 'Nimbus² Persistent Learning System\n'
            printf 'Usage: %s <command> [args]\n\n' "$0"
            printf 'Commands:\n'
            printf '  learn <platform> <component> <result> <lines>   Learn from build\n'
            printf '  skip <platform> <component>                     Check if should skip\n'
            printf '  best <component>                               Get best platform\n'
            printf '  rules                                           Show persistent rules\n'
            printf '  stats                                           Show build stats\n'
            printf '  help                                            Show this help\n'
            ;;
        *)
            log_error "Unknown command: ${cmd}"
            exit 1
            ;;
    esac
    
    log "NIMBUS²-LEARN" "=== LEARNING COMPLETE ==="
}

main "$@"
