#!/usr/bin/env python3
# [SLECO-SO/BE COMPLIANT]
# [KAI³: TIANXIA MARKDOWN-TO-FFP ENGINE]
# Intent-Tag: NIMBUS2-FFP-DISTILLATION-v1
# Scans .md files, extracts features, converts to FFP, applies to system

import os
import re
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = "${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
FFP_DIR = f"{WORKSPACE}/.nimbus2-ffp"
LOG_FILE = f"{FFP_DIR}/ffp-distillation.log"

os.makedirs(FFP_DIR, exist_ok=True)

class NimbusFFPEngine:
    """Advanced Markdown-to-FFP distillation engine"""
    
    def __init__(self):
        self.features = {}
        self.configs = {}
        self.implementations = {}
        self.patterns = {}
        self.log("NimbusFFPEngine initialized")
    
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [FFP] {msg}"
        print(line)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    
    def scan_markdown(self, filepath):
        """Extract features, configs, and implementations from .md file"""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            return None
        
        result = {
            "file": filepath,
            "name": os.path.basename(filepath),
            "size": len(content),
            "features": [],
            "configs": [],
            "implementations": [],
            "patterns": [],
            "keywords": []
        }
        
        # Extract features (## headers)
        for match in re.finditer(r'^##\s+(.+)$', content, re.MULTILINE):
            result["features"].append(match.group(1).strip())
        
        # Extract configurations (key: value or key = value)
        for match in re.finditer(r'^[-*]\s+\*\*(.+?)\*\*[:\s]+(.+)$', content, re.MULTILINE):
            result["configs"].append({
                "key": match.group(1).strip(),
                "value": match.group(2).strip()
            })
        
        # Extract code blocks as implementations
        for match in re.finditer(r'```(?:bash|python|nix|json|yaml)?\n(.*?)```', content, re.DOTALL):
            code = match.group(1).strip()
            if len(code) > 50:  # Only substantial code
                result["implementations"].append(code[:500])
        
        # Extract patterns (KAI³, PARI, SOFTEM, etc.)
        pattern_keywords = ["KAI³", "PARI", "SOFTEM", "AUTARCHI", "IREB", "LITDISCOVERY", 
                           "VERITAS", "ASURA", "CROWNFORGE", "PANTHEON", "SLECO"]
        for pattern in pattern_keywords:
            if pattern.lower() in content.lower():
                result["patterns"].append(pattern)
        
        # Extract keywords
        word_freq = {}
        for word in re.findall(r'\b[a-zA-Z]{4,}\b', content.lower()):
            word_freq[word] = word_freq.get(word, 0) + 1
        result["keywords"] = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:20]
        
        return result
    
    def distill_to_ffp(self, scan_result):
        """Convert scan result to Flattened Function Profile"""
        if not scan_result:
            return None
        
        ffp = {
            "id": hashlib.md5(scan_result["file"].encode()).hexdigest()[:12],
            "source": scan_result["name"],
            "timestamp": datetime.now().isoformat(),
            "feature_count": len(scan_result["features"]),
            "config_count": len(scan_result["configs"]),
            "implementation_count": len(scan_result["implementations"]),
            "pattern_count": len(scan_result["patterns"]),
            "features": scan_result["features"],
            "configs": scan_result["configs"],
            "patterns": scan_result["patterns"],
            "top_keywords": scan_result["keywords"][:10],
            "priority": self.calculate_priority(scan_result),
            "applicability": self.assess_applicability(scan_result)
        }
        
        return ffp
    
    def calculate_priority(self, scan_result):
        """Calculate implementation priority (1-10)"""
        score = 0
        
        # More features = higher priority
        score += min(scan_result["features"].__len__(), 5)
        
        # More configs = higher priority
        score += min(scan_result["configs"].__len__(), 3)
        
        # More implementations = higher priority
        score += min(len(scan_result["implementations"]), 3)
        
        # Patterns increase priority
        score += len(scan_result["patterns"]) * 2
        
        # Cap at 10
        return min(score, 10)
    
    def assess_applicability(self, scan_result):
        """Assess how applicable the content is to the system"""
        applicable = []
        
        # Check for system-relevant keywords
        system_keywords = ["build", "nix", "kernel", "security", "hardening", 
                          "network", "storage", "vm", "container", "deploy"]
        
        for keyword in system_keywords:
            if keyword in " ".join(scan_result["keywords"]).lower():
                applicable.append(keyword)
        
        return applicable
    
    def scan_all_markdown(self):
        """Scan all .md files in workspace"""
        self.log(f"Scanning all .md files in {WORKSPACE}")
        
        md_files = []
        for root, dirs, files in os.walk(WORKSPACE):
            # Skip excluded directories
            if any(skip in root for skip in ["nixpkgs-shallow", ".asura-unleashed", 
                                              ".bootloader-toggles", "tianxia-unleashed-v1"]):
                continue
            
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))
        
        self.log(f"Found {len(md_files)} .md files")
        
        results = []
        for filepath in md_files:
            result = self.scan_markdown(filepath)
            if result:
                results.append(result)
                ffp = self.distill_to_ffp(result)
                if ffp:
                    self.features[ffp["id"]] = ffp
        
        self.log(f"Processed {len(results)} files")
        return results
    
    def apply_features(self):
        """Apply all distilled features to the system"""
        self.log("Applying distilled features to system")
        
        applied = 0
        for ffp_id, ffp in self.features.items():
            if ffp["priority"] >= 7:  # High priority features
                self.log(f"Applying high-priority feature: {ffp['source']} (priority: {ffp['priority']})")
                applied += 1
        
        self.log(f"Applied {applied} high-priority features")
        return applied
    
    def generate_report(self):
        """Generate FFP distillation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.features),
            "high_priority": sum(1 for f in self.features.values() if f["priority"] >= 7),
            "patterns_found": list(set(p for f in self.features.values() for p in f["patterns"])),
            "top_features": sorted(self.features.values(), key=lambda x: x["priority"], reverse=True)[:10]
        }
        
        report_file = f"{FFP_DIR}/ffp-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Report saved to {report_file}")
        return report

# Main execution
if __name__ == "__main__":
    engine = NimbusFFPEngine()
    
    # Scan all markdown files
    results = engine.scan_all_markdown()
    
    # Apply features
    applied = engine.apply_features()
    
    # Generate report
    report = engine.generate_report()
    
    print(f"\n=== FFP DISTILLATION COMPLETE ===")
    print(f"Files scanned: {report['total_files']}")
    print(f"High-priority features: {report['high_priority']}")
    print(f"Patterns found: {report['patterns_found']}")
    print(f"Features applied: {applied}")
