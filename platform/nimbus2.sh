#!/bin/bash
# ffp: FFP-NIMBUS2-NIMBUS2 content-pipeline bash
# ═══════════════════════════════════════════════════════════════════════════════
# NIMBUS² UNIFIED ENTRY POINT
# Merged from 50+ scripts — all features preserved
# Version: 3.0.0 — Agentic Swarm Edition
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║   ██████╗ ██╗██╗██╗     ███╗   ██╗███████╗██████╗ ███████╗  ║"
    echo "║  ██╔════╝██║██║██║     ████╗  ██║██╔════╝██╔══██╗██╔════╝  ║"
    echo "║  ██║     ██║██║██║     ██╔██╗ ██║█████╗  ██████╔╝███████╗  ║"
    echo "║  ██║     ╚███╔╝██║     ██║╚██╗██║██╔══╝  ██╔══██╗╚════██║  ║"
    echo "║  ╚██████╗██╔╝ ██║     ██║ ╚████║███████╗██║  ██║███████║  ║"
    echo "║   ╚═════╝╚═╝  ╚═╝     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚══════╝  ║"
    echo "║                                                              ║"
    echo "║              v3.0.0 — Agentic Swarm Edition                  ║"
    echo "║         All features preserved. Additive merge.              ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    echo "Usage: nimbus2.sh [command] [options]"
    echo ""
    echo "CORE COMMANDS:"
    echo "  engine          Run core engine (225 streams, Asura mode)"
    echo "  transport       Run transport layer (upload/download/chunk)"
    echo "  compress        Run smart compression"
    echo ""
    echo "SECURITY COMMANDS:"
    echo "  etamanga        Run ETAMANGA features"
    echo "  hsm             Run Titan M2 HSM"
    echo "  provision       Run tiered provisioning"
    echo ""
    echo "INTELLIGENCE COMMANDS:"
    echo "  miner           Run deep/fast mining"
    echo "  extractor       Run peak extraction"
    echo "  ffp             Run FFP analysis"
    echo "  learner         Run learning engine"
    echo "  softhem         Run device detection"
    echo ""
    echo "INFRASTRUCTURE COMMANDS:"
    echo "  asura           Run Asura mode (7 engines parallel)"
    echo "  router          Run polymorphic routing"
    echo "  netbench        Run network benchmark"
    echo "  browser         Run browser engine"
    echo "  backup          Run device backup"
    echo ""
    echo "MONITORING COMMANDS:"
    echo "  monitor         Run live monitoring"
    echo "  budget          Run budget tracking"
    echo ""
    echo "UTILITY COMMANDS:"
    echo "  scanner         Run archive scanner"
    echo "  extract         Run extraction"
    echo "  intelligent     Run intelligent upload"
    echo "  plugin          Run plugin system"
    echo "  urlfinder       Run URL finder"
    echo ""
    echo "INFO COMMANDS:"
    echo "  status          Show system status"
    echo "  version         Show version"
    echo "  modules         List all modules"
    echo "  help            Show this help"
    echo ""
}

show_status() {
    echo -e "${GREEN}Nimbus² Unified v3.0.0 — All Systems Operational${NC}"
    echo ""
    echo "Modules loaded:"
    for module in core security intelligence infrastructure monitoring utility; do
        count=$(ls "$SCRIPT_DIR/$module/" 2>/dev/null | wc -l)
        echo "  ✓ $module ($count files)"
    done
    echo ""
    echo "Total modules: $(find "$SCRIPT_DIR" -type f | wc -l)"
    echo "Total size: $(du -sh "$SCRIPT_DIR" | cut -f1)"
}

list_modules() {
    echo "Nimbus² Unified Modules:"
    echo ""
    for module in core security intelligence infrastructure monitoring utility business; do
        echo -e "${CYAN}[$module]${NC}"
        ls "$SCRIPT_DIR/$module/" 2>/dev/null | while read f; do
            echo "  - $f"
        done
        echo ""
    done
}

# Main command handler
case "${1:-help}" in
    engine)
        echo -e "${YELLOW}Starting Nimbus² Engine...${NC}"
        source "$SCRIPT_DIR/core/nimbus2-engine.sh"
        ;;
    transport)
        echo -e "${YELLOW}Starting Nimbus² Transport...${NC}"
        source "$SCRIPT_DIR/core/nimbus2-transport.sh"
        ;;
    compress)
        echo -e "${YELLOW}Starting Nimbus² Compression...${NC}"
        python3 "$SCRIPT_DIR/core/nimbus2-smart-compress.py" "${@:2}"
        ;;
    etamanga)
        echo -e "${YELLOW}Starting ETAMANGA Features...${NC}"
        python3 "$SCRIPT_DIR/security/nimbus2-etamanga.py" "${@:2}"
        ;;
    hsm)
        echo -e "${YELLOW}Starting Titan M2 HSM...${NC}"
        python3 "$SCRIPT_DIR/security/nimbus2-hsm.py" "${@:2}"
        ;;
    provision)
        echo -e "${YELLOW}Starting Tiered Provisioning...${NC}"
        python3 "$SCRIPT_DIR/security/nimbus2-provisioning.py" "${@:2}"
        ;;
    miner)
        echo -e "${YELLOW}Starting Mining Engine...${NC}"
        python3 "$SCRIPT_DIR/intelligence/nimbus2-miner.py" "${@:2}"
        ;;
    extractor)
        echo -e "${YELLOW}Starting Peak Extraction...${NC}"
        python3 "$SCRIPT_DIR/intelligence/nimbus2-extractor.py" "${@:2}"
        ;;
    ffp)
        echo -e "${YELLOW}Starting FFP Analysis...${NC}"
        python3 "$SCRIPT_DIR/intelligence/nimbus2-ffp.py" "${@:2}"
        ;;
    learner)
        echo -e "${YELLOW}Starting Learning Engine...${NC}"
        source "$SCRIPT_DIR/intelligence/nimbus2-learner.sh" "${@:2}"
        ;;
    softhem)
        echo -e "${YELLOW}Starting SOFTEM Device Detection...${NC}"
        python3 "$SCRIPT_DIR/intelligence/nimbus2-softhem.py" "${@:2}"
        ;;
    asura)
        echo -e "${YELLOW}Starting Asura Mode (7 Engines Parallel)...${NC}"
        source "$SCRIPT_DIR/infrastructure/nimbus2-asura.sh" "${@:2}"
        ;;
    router)
        echo -e "${YELLOW}Starting Polymorphic Router...${NC}"
        source "$SCRIPT_DIR/infrastructure/nimbus2-router.sh" "${@:2}"
        ;;
    netbench)
        echo -e "${YELLOW}Starting Network Benchmark...${NC}"
        source "$SCRIPT_DIR/infrastructure/nimbus2-netbench.sh" "${@:2}"
        ;;
    browser)
        echo -e "${YELLOW}Starting Browser Engine...${NC}"
        source "$SCRIPT_DIR/infrastructure/nimbus2-browser.sh" "${@:2}"
        ;;
    backup)
        echo -e "${YELLOW}Starting Device Backup...${NC}"
        source "$SCRIPT_DIR/infrastructure/nimbus2-backup.sh" "${@:2}"
        ;;
    monitor)
        echo -e "${YELLOW}Starting Live Monitoring...${NC}"
        source "$SCRIPT_DIR/monitoring/nimbus2-monitor.sh" "${@:2}"
        ;;
    budget)
        echo -e "${YELLOW}Starting Budget Tracking...${NC}"
        source "$SCRIPT_DIR/monitoring/nimbus2-budget.sh" "${@:2}"
        ;;
    scanner)
        echo -e "${YELLOW}Starting Archive Scanner...${NC}"
        python3 "$SCRIPT_DIR/utility/nimbus2-scanner.py" "${@:2}"
        ;;
    extract)
        echo -e "${YELLOW}Starting Extraction...${NC}"
        source "$SCRIPT_DIR/utility/nimbus2-extract.sh" "${@:2}"
        ;;
    intelligent)
        echo -e "${YELLOW}Starting Intelligent Upload...${NC}"
        source "$SCRIPT_DIR/utility/nimbus2-intelligent.sh" "${@:2}"
        ;;
    plugin)
        echo -e "${YELLOW}Starting Plugin System...${NC}"
        source "$SCRIPT_DIR/utility/nimbus2-pluginus.sh" "${@:2}"
        ;;
    urlfinder)
        echo -e "${YELLOW}Starting URL Finder...${NC}"
        python3 "$SCRIPT_DIR/utility/nimbus2-urlfinder.py" "${@:2}"
        ;;
    status)
        show_status
        ;;
    version)
        echo "Nimbus² v3.0.0 — Unified Agentic Edition"
        ;;
    modules)
        list_modules
        ;;
    help|--help|-h)
        print_banner
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run 'nimbus2.sh help' for usage"
        exit 1
        ;;
esac
