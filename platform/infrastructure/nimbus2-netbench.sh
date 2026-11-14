#!${TX_PREFIX:-/usr/local}/files/usr/bin/bash
# ffp: FFP-NIMBUS2-NIMBUS2-NETBENCH content-pipeline bash
# SLECO-SO/BE COMPLIANT
# nimbus2-netbench.sh — Tianxia Network Benchmark Suite
# Multi-point download + upload + latency + DNS + jitter test
# UE300C ethernet optimized

set -euo pipefail

export WORKSPACE="${WORKSPACE:-${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set}"
export LOG_DIR="${WORKSPACE}/logs"
export REPORT="${LOG_DIR}/netbench-$(date +%Y%m%d-%H%M%S).json"
export TMPDIR="${TMPDIR:-/tmp}"

mkdir -p "${LOG_DIR}"

# === DETERMINISTIC INITIALIZATION ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$1"; }
header() { printf "\n${BOLD}${CYAN}═══ %s ═══${NC}\n" "$1"; }
result() { printf "  ${GREEN}✓${NC} %s: ${BOLD}%s${NC}\n" "$1" "$2"; }
warn() { printf "  ${YELLOW}⚠${NC} %s: ${BOLD}%s${NC}\n" "$1" "$2"; }
fail() { printf "  ${RED}✗${NC} %s: ${BOLD}%s${NC}\n" "$1" "$2"; }

# === START ===
echo ""
printf "${BOLD}${CYAN}╔══════════════════════════════════════════╗${NC}\n"
printf "${BOLD}${CYAN}║   TIANXIA NIMBUS² NETWORK BENCHMARK     ║${NC}\n"
printf "${BOLD}${CYAN}║   UE300C Ethernet • $(date +%Y-%m-%d)          ║${NC}\n"
printf "${BOLD}${CYAN}╚══════════════════════════════════════════╝${NC}\n"

# === INTERFACE STATUS ===
header "INTERFACE STATUS"
ETH_IP=$(ifconfig 2>/dev/null | grep -A1 "^eth0" | grep -oP 'inet \K[\d.]+' || echo "NONE")
ETH_MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || echo "unknown")
GW=$(route -n 2>/dev/null | grep '^0.0.0.0' | awk '{print $2}' || echo "unknown")
DNS=$(grep nameserver /etc/resolv.conf 2>/dev/null | head -1 | awk '{print $2}' || echo "unknown")

if [[ "$ETH_IP" == "NONE" ]]; then
    fail "eth0" "NOT CONNECTED"
    exit 1
fi

result "IP" "$ETH_IP"
result "Gateway" "$GW"
result "DNS" "$DNS"
result "MAC" "$ETH_MAC"

# === LATENCY & JITTER ===
header "LATENCY & JITTER"

latency_test() {
    local target=$1
    local label=$2
    local count=${3:-20}
    
    local output=$(ping -c "$count" -W 2 "$target" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        local avg=$(echo "$output" | tail -1 | awk -F'/' '{print $5}')
        local min=$(echo "$output" | tail -1 | awk -F'/' '{print $4}')
        local max=$(echo "$output" | tail -1 | awk -F'/' '{print $6}')
        local mdev=$(echo "$output" | tail -1 | awk -F'/' '{print $7}')
        local loss=$(echo "$output" | grep -oP '\d+(?=% packet loss)')
        result "$label" "${avg}ms avg (${min}-${max}ms, jitter ${mdev}ms, loss ${loss}%)"
        echo "{\"target\":\"$target\",\"avg_ms\":$avg,\"min_ms\":$min,\"max_ms\":$max,\"jitter_ms\":$mdev,\"loss_pct\":$loss}"
    else
        fail "$label" "UNREACHABLE"
        echo "{\"target\":\"$target\",\"error\":\"unreachable\"}"
    fi
}

GW_LAT=$(latency_test "$GW" "Gateway ($GW)" 30)
GOOGLE_LAT=$(latency_test "8.8.8.8" "Google DNS" 20)
CF_LAT=$(latency_test "1.1.1.1" "Cloudflare DNS" 20)

# === DNS RESOLUTION ===
header "DNS RESOLUTION"

dns_test() {
    local domain=$1
    local start=$(date +%s%N)
    local result=$(nslookup "$domain" 2>/dev/null | grep -oP 'Address: \K[\d.]+' | tail -1)
    local end=$(date +%s%N)
    local elapsed=$(( (end - start) / 1000000 ))
    
    if [[ -n "$result" ]]; then
        result "$domain" "${result} (${elapsed}ms)"
    else
        fail "$domain" "FAILED"
    fi
}

dns_test "google.com"
dns_test "cloudflare.com"
dns_test "github.com"
dns_test "amazon.com"

# === DOWNLOAD SPEED (multi-point) ===
header "DOWNLOAD SPEED"

download_test() {
    local url=$1
    local label=$2
    local size_mb=$3
    
    local tmpfile="${TMPDIR}/netbench_dl_$$"
    local start=$(date +%s%N)
    
    curl -s -o "$tmpfile" -w "%{speed_download}" "$url" --max-time 30 2>/dev/null
    local speed_bps=$(curl -s -o "$tmpfile" -w "%{speed_download}" "$url" --max-time 30 2>/dev/null)
    local end=$(date +%s%N)
    local elapsed_ms=$(( (end - start) / 1000000 ))
    
    if [[ -f "$tmpfile" ]]; then
        local actual_size=$(stat -c%s "$tmpfile" 2>/dev/null || stat -f%z "$tmpfile" 2>/dev/null || echo 0)
        rm -f "$tmpfile"
        
        if [[ "$actual_size" -gt 0 ]]; then
            local speed_mbps=$(echo "scale=2; $actual_size * 8 / $elapsed_ms / 1000" | bc 2>/dev/null || echo "?")
            local speed_mibs=$(echo "scale=2; $actual_size / $elapsed_ms / 1024" | bc 2>/dev/null || echo "?")
            result "$label" "${speed_mibs} MB/s (${speed_mbps} Mbps) — ${actual_size} bytes in ${elapsed_ms}ms"
            return 0
        fi
    fi
    fail "$label" "FAILED"
    return 1
}

# Tele2 (EU)
DL1=$(download_test "http://speedtest.tele2.net/100MB.zip" "Tele2 (EU, 100MB)" 100)
sleep 1

# OVH
DL2=$(download_test "http://proof.ovh.net/files/100Mb.dat" "OVH (EU, 100Mb)" 100)
sleep 1

# Hetzner
DL3=$(download_test "https://speed.hetzner.de/100MB.bin" "Hetzner (EU, 100MB)" 100)

# === UPLOAD TEST ===
header "UPLOAD SPEED"

upload_test() {
    local size_mb=$1
    local label=$2
    
    local tmpfile="${TMPDIR}/netbench_ul_${size_mb}mb_$$"
    dd if=/dev/urandom of="$tmpfile" bs=1M count="$size_mb" 2>/dev/null
    
    local start=$(date +%s%N)
    local speed=$(curl -s -o /dev/null -w "%{speed_upload}" --max-time 60 \
        -X POST -F "file=@$tmpfile" \
        "https://httpbin.org/post" 2>/dev/null || echo "0")
    local end=$(date +%s%N)
    local elapsed_ms=$(( (end - start) / 1000000 ))
    
    rm -f "$tmpfile"
    
    if [[ "$speed" != "0" && -n "$speed" ]]; then
        local speed_mbps=$(echo "scale=2; $speed * 8 / 1000000" | bc 2>/dev/null || echo "?")
        local speed_mibs=$(echo "scale=2; $speed / 1048576" | bc 2>/dev/null || echo "?")
        result "$label" "${speed_mibs} MB/s (${speed_mbps} Mbps)"
    else
        warn "$label" "Endpoint timeout — trying alternative..."
        
        # Alternative: POST to local echo
        local tmpfile2="${TMPDIR}/netbench_ul_alt_$$"
        dd if=/dev/urandom of="$tmpfile2" bs=1M count="$size_mb" 2>/dev/null
        start=$(date +%s%N)
        curl -s -o /dev/null -w "%{speed_upload}" --max-time 60 \
            -X POST --data-binary "@$tmpfile2" \
            "https://httpbin.org/post" 2>/dev/null
        end=$(date +%s%N)
        elapsed_ms=$(( (end - start) / 1000000 ))
        rm -f "$tmpfile2"
        
        warn "$label" "Upload test inconclusive (${elapsed_ms}ms)"
    fi
}

UL1=$(upload_test 5 "Upload (5MB)")
sleep 1
UL2=$(upload_test 10 "Upload (10MB)")

# === CONCURRENT CONNECTIONS TEST ===
header "CONCURRENT DOWNLOAD (4 streams)"

CONCURRENT_DL() {
    local url=$1
    local label=$2
    
    local tmpdir="${TMPDIR}/netbench_conc_$$"
    mkdir -p "$tmpdir"
    
    local start=$(date +%s%N)
    
    # 4 parallel downloads
    for i in 1 2 3 4; do
        curl -s -o "${tmpdir}/part${i}" "$url" --max-time 30 &
    done
    wait
    
    local end=$(date +%s%N)
    local elapsed_ms=$(( (end - start) / 1000000 ))
    
    local total_bytes=0
    for f in "${tmpdir}"/part*; do
        if [[ -f "$f" ]]; then
            local sz=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)
            total_bytes=$((total_bytes + sz))
        fi
    done
    
    rm -rf "$tmpdir"
    
    if [[ "$total_bytes" -gt 0 ]]; then
        local speed_mibs=$(echo "scale=2; $total_bytes / $elapsed_ms / 1024" | bc 2>/dev/null || echo "?")
        result "$label" "${speed_mibs} MB/s (${total_bytes} bytes in ${elapsed_ms}ms, 4 streams)"
    else
        fail "$label" "FAILED"
    fi
}

CONCURRENT_DL "http://speedtest.tele2.net/50MB.zip" "4×50MB Tele2"

# === TCP CONNECTION TIME ===
header "TCP CONNECTION TIME"

tcp_test() {
    local host=$1
    local port=$2
    local label=$3
    
    local start=$(date +%s%N)
    echo "" | ncat -w 3 "$host" "$port" 2>/dev/null
    local end=$(date +%s%N)
    local elapsed_ms=$(( (end - start) / 1000000 ))
    
    result "$label" "${elapsed_ms}ms"
}

tcp_test "1.1.1.1" 443 "Cloudflare 443"
tcp_test "8.8.8.8" 443 "Google 443"
tcp_test "github.com" 443 "GitHub 443"

# === TRACEROUTE ===
header "TRACEROUTE (first 8 hops)"

if command -v traceroute &>/dev/null; then
    traceroute -n -m 8 -w 2 8.8.8.8 2>/dev/null | tail -n +2
else
    warn "traceroute" "not installed — using mtr or fallback"
    if command -v mtr &>/dev/null; then
        mtr -n -c 1 -r 8.8.8.8 2>/dev/null | head -10
    else
        # Fallback: manual trace with ping
        for i in $(seq 1 8); do
            local hop_ip=$(ping -c 1 -W 1 -t "$i" 8.8.8.8 2>/dev/null | grep -oP 'from \K[\d.]+' | head -1)
            [[ -z "$hop_ip" ]] && hop_ip="*"
            printf "  %2d  %s\n" "$i" "$hop_ip"
        done
    fi
fi

# === FINAL REPORT ===
header "BENCHMARK COMPLETE"
log "Report: ${REPORT}"
log "Time: $(date)"

echo ""
printf "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"
printf "${BOLD}${CYAN}  TIANXIA NIMBUS² NETBENCH — COMPLETE${NC}\n"
printf "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"
echo ""
