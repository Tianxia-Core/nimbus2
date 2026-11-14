#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-NIMBUS2-MINER io-edge python
# [SLECO-SO/BE COMPLIANT]
# [KAI³: TIANXIA RECURSIVE DEEP MINER]
# Intent-Tag: NIMBUS2-DEEP-MINER-v1
# Recursively mines all .md files until patterns and FFPs exhausted

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

WORKSPACE = "${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
MINER_DIR = f"{WORKSPACE}/.nimbus2-miner"
LOG_FILE = f"{MINER_DIR}/deep-miner.log"

os.makedirs(MINER_DIR, exist_ok=True)

class DeepMiner:
    """Recursive deep miner for markdown files"""
    
    def __init__(self):
        self.patterns = defaultdict(list)
        self.ffps = {}
        self.configs = {}
        self.implementations = {}
        self.keywords = Counter()
        self.code_blocks = []
        self.headers = []
        self.links = []
        self.tables = []
        self.lists = []
        self.errors = []
        self.warnings = []
        self.successes = []
        self.log("DeepMiner initialized")
    
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [MINER] {msg}"
        print(line, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    
    def mine_file(self, filepath):
        """Deep mine a single .md file"""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            self.errors.append({"file": filepath, "error": str(e)})
            return None
        
        result = {
            "file": filepath,
            "name": os.path.basename(filepath),
            "size": len(content),
            "lines": content.count("\n"),
            "headers": [],
            "code_blocks": [],
            "configs": [],
            "implementations": [],
            "patterns": [],
            "keywords": [],
            "links": [],
            "tables": [],
            "lists": [],
            "errors_found": [],
            "warnings_found": [],
            "successes_found": []
        }
        
        # Extract all headers
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
            result["headers"].append({
                "level": len(match.group(1)),
                "text": match.group(2).strip()
            })
        
        # Extract all code blocks
        for match in re.finditer(r'```(\w*)\n(.*?)```', content, re.DOTALL):
            lang = match.group(1) or "unknown"
            code = match.group(2).strip()
            if len(code) > 20:
                result["code_blocks"].append({
                    "language": lang,
                    "content": code[:1000],
                    "lines": code.count("\n")
                })
                self.code_blocks.append(code)
        
        # Extract configurations (key-value patterns)
        config_patterns = [
            r'\*\*(.+?)\*\*[:\s]+(.+?)(?:\n|$)',
            r'[-*]\s+\*\*(.+?)\*\*[:\s]+(.+?)(?:\n|$)',
            r'[-*]\s+(.+?)[:\s]+(.+?)(?:\n|$)',
            r'(.+?)\s*=\s*(.+?)(?:\n|$)',
            r'(.+?)\s*:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in config_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                key = match.group(1).strip()
                value = match.group(2).strip()
                if len(key) > 3 and len(value) > 3:
                    result["configs"].append({"key": key, "value": value})
        
        # Extract implementations from code blocks
        for block in result["code_blocks"]:
            if block["language"] in ["bash", "python", "nix", "json", "yaml", "javascript", "typescript"]:
                result["implementations"].append(block)
        
        # Extract patterns
        pattern_keywords = [
            "KAI³", "KAI3", "PARI", "SOFTEM", "AUTARCHI", "IREB", "LITDISCOVERY",
            "VERITAS", "ASURA", "CROWNFORGE", "PANTHEON", "SLECO", "EISRA", "AEEP",
            "FFP", "nimbus", "tianxia", "sovereignty", "autarchy", "hardening",
            "security", "kernel", "build", "deploy", "monitor", "audit"
        ]
        
        for pattern in pattern_keywords:
            if pattern.lower() in content.lower():
                result["patterns"].append(pattern)
                self.patterns[pattern].append(filepath)
        
        # Extract keywords
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        word_freq = Counter(words)
        result["keywords"] = word_freq.most_common(30)
        self.keywords.update(word_freq)
        
        # Extract links
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
            result["links"].append({
                "text": match.group(1),
                "url": match.group(2)
            })
            self.links.append(match.group(2))
        
        # Extract tables
        table_rows = re.findall(r'\|(.+)\|', content)
        if table_rows:
            result["tables"].append({"rows": len(table_rows)})
            self.tables.append({"file": filepath, "rows": len(table_rows)})
        
        # Extract lists
        list_items = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)
        if list_items:
            result["lists"].append({"items": len(list_items)})
            self.lists.append({"file": filepath, "items": len(list_items)})
        
        # Extract errors
        error_patterns = [
            r'error[:\s]+(.+?)(?:\n|$)',
            r'ERROR[:\s]+(.+?)(?:\n|$)',
            r'failed[:\s]+(.+?)(?:\n|$)',
            r'FAILED[:\s]+(.+?)(?:\n|$)'
        ]
        for pattern in error_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                result["errors_found"].append(match.group(1).strip())
                self.errors.append({"file": filepath, "error": match.group(1).strip()})
        
        # Extract warnings
        warning_patterns = [
            r'warning[:\s]+(.+?)(?:\n|$)',
            r'WARNING[:\s]+(.+?)(?:\n|$)',
            r'caution[:\s]+(.+?)(?:\n|$)',
            r'CAUTION[:\s]+(.+?)(?:\n|$)'
        ]
        for pattern in warning_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                result["warnings_found"].append(match.group(1).strip())
                self.warnings.append({"file": filepath, "warning": match.group(1).strip()})
        
        # Extract successes
        success_patterns = [
            r'success[:\s]+(.+?)(?:\n|$)',
            r'SUCCESS[:\s]+(.+?)(?:\n|$)',
            r'completed[:\s]+(.+?)(?:\n|$)',
            r'COMPLETED[:\s]+(.+?)(?:\n|$)'
        ]
        for pattern in success_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                result["successes_found"].append(match.group(1).strip())
                self.successes.append({"file": filepath, "success": match.group(1).strip()})
        
        return result
    
    def mine_all_files(self):
        """Recursively mine all .md files"""
        self.log("Starting recursive deep mining of all .md files")
        
        md_files = []
        for root, dirs, files in os.walk(WORKSPACE):
            # Skip excluded directories
            if any(skip in root for skip in ["nixpkgs-shallow", ".asura-unleashed", 
                                              ".bootloader-toggles", "tianxia-unleashed-v1",
                                              ".nimbus2-ffp", ".nimbus2-miner"]):
                continue
            
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))
        
        self.log(f"Found {len(md_files)} .md files to mine")
        
        results = []
        for i, filepath in enumerate(md_files):
            if i % 100 == 0:
                self.log(f"Mining file {i+1}/{len(md_files)}: {os.path.basename(filepath)}")
            
            result = self.mine_file(filepath)
            if result:
                results.append(result)
        
        self.log(f"Deep mining complete: {len(results)} files processed")
        return results
    
    def extract_all_patterns(self):
        """Extract and categorize all patterns"""
        self.log("Extracting all patterns")
        
        pattern_summary = {}
        for pattern, files in self.patterns.items():
            pattern_summary[pattern] = {
                "count": len(files),
                "files": files[:10],  # First 10 files
                "unique_files": len(set(files))
            }
        
        return pattern_summary
    
    def extract_all_ffps(self):
        """Extract all Flattened Function Profiles"""
        self.log("Extracting all FFPs")
        
        ffps = []
        for result in self.mined_files:
            if result and len(result["code_blocks"]) > 0:
                ffp = {
                    "id": hashlib.md5(result["file"].encode()).hexdigest()[:12],
                    "source": result["name"],
                    "code_blocks": len(result["code_blocks"]),
                    "configs": len(result["configs"]),
                    "implementations": len(result["implementations"]),
                    "patterns": result["patterns"],
                    "keywords": [k for k, v in result["keywords"][:10]],
                    "priority": min(len(result["patterns"]) * 2 + len(result["code_blocks"]), 10)
                }
                ffps.append(ffp)
        
        return ffps
    
    def generate_report(self):
        """Generate comprehensive extraction report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "files_mined": len(self.mined_files),
            "total_patterns": len(self.patterns),
            "total_ffps": len(self.ffps),
            "total_code_blocks": len(self.code_blocks),
            "total_configs": sum(len(r["configs"]) for r in self.mined_files if r),
            "total_implementations": sum(len(r["implementations"]) for r in self.mined_files if r),
            "total_links": len(self.links),
            "total_tables": len(self.tables),
            "total_lists": len(self.lists),
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "total_successes": len(self.successes),
            "pattern_summary": self.extract_all_patterns(),
            "top_keywords": self.keywords.most_common(50),
            "error_summary": Counter(e["error"][:50] for e in self.errors).most_common(20),
            "warning_summary": Counter(w["warning"][:50] for w in self.warnings).most_common(20),
            "success_summary": Counter(s["success"][:50] for s in self.successes).most_common(20)
        }
        
        report_file = f"{MINER_DIR}/deep-miner-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        self.log(f"Report saved to {report_file}")
        return report

# Main execution
if __name__ == "__main__":
    miner = DeepMiner()
    
    # Recursive deep mining
    miner.mined_files = miner.mine_all_files()
    
    # Extract all patterns
    patterns = miner.extract_all_patterns()
    
    # Extract all FFPs
    ffps = miner.extract_all_ffps()
    
    # Generate report
    report = miner.generate_report()
    
    print(f"\n=== DEEP MINING COMPLETE ===")
    print(f"Files mined: {report['files_mined']}")
    print(f"Patterns found: {report['total_patterns']}")
    print(f"FFPs extracted: {report['total_ffps']}")
    print(f"Code blocks: {report['total_code_blocks']}")
    print(f"Configurations: {report['total_configs']}")
    print(f"Implementations: {report['total_implementations']}")
    print(f"Links: {report['total_links']}")
    print(f"Errors found: {report['total_errors']}")
    print(f"Warnings found: {report['total_warnings']}")
    print(f"Successes found: {report['total_successes']}")
    print(f"\nTop patterns:")
    for pattern, info in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
        print(f"  {pattern}: {info['count']} files")
#!/usr/bin/env python3
# [SLECO-SO/BE COMPLIANT]
# [KAI³: TIANXIA FAST DEEP MINER]
# Intent-Tag: NIMBUS2-FAST-MINER-v1
# Fast recursive mining with batch processing

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

WORKSPACE = "${TX_WORKSPACE:-/var/lib/tianxia}/tianxia_build/tianxia_active_working_set"
MINER_DIR = f"{WORKSPACE}/.nimbus2-miner"
LOG_FILE = f"{MINER_DIR}/fast-miner.log"

os.makedirs(MINER_DIR, exist_ok=True)

class FastMiner:
    """Fast recursive miner for markdown files"""
    
    def __init__(self):
        self.patterns = defaultdict(list)
        self.code_blocks = []
        self.keywords = Counter()
        self.errors = []
        self.warnings = []
        self.successes = []
        self.files_processed = 0
        self.log("FastMiner initialized")
    
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [MINER] {msg}"
        print(line, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    
    def mine_file_fast(self, filepath):
        """Fast mine a single .md file"""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            return None
        
        result = {
            "file": filepath,
            "name": os.path.basename(filepath),
            "size": len(content),
            "headers": len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE)),
            "code_blocks": len(re.findall(r'```\w*\n', content)),
            "links": len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)),
            "patterns": [],
            "keywords": []
        }
        
        # Extract patterns
        pattern_keywords = [
            "KAI³", "KAI3", "PARI", "SOFTEM", "AUTARCHI", "IREB", "LITDISCOVERY",
            "VERITAS", "ASURA", "CROWNFORGE", "PANTHEON", "SLECO", "EISRA", "AEEP",
            "FFP", "nimbus", "tianxia", "sovereignty", "autarchy", "hardening",
            "security", "kernel", "build", "deploy", "monitor", "audit"
        ]
        
        for pattern in pattern_keywords:
            if pattern.lower() in content.lower():
                result["patterns"].append(pattern)
                self.patterns[pattern].append(filepath)
        
        # Extract keywords
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        self.keywords.update(words)
        
        # Extract errors
        for match in re.finditer(r'(?:error|failed|FAILED)[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE):
            self.errors.append({"file": filepath, "error": match.group(1).strip()[:100]})
        
        # Extract warnings
        for match in re.finditer(r'(?:warning|caution)[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE):
            self.warnings.append({"file": filepath, "warning": match.group(1).strip()[:100]})
        
        # Extract successes
        for match in re.finditer(r'(?:success|completed|COMPLETED)[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE):
            self.successes.append({"file": filepath, "success": match.group(1).strip()[:100]})
        
        return result
    
    def mine_all_fast(self):
        """Fast mine all .md files"""
        self.log("Starting fast recursive mining")
        
        md_files = []
        for root, dirs, files in os.walk(WORKSPACE):
            if any(skip in root for skip in ["nixpkgs-shallow", ".asura-unleashed", 
                                              ".bootloader-toggles", "tianxia-unleashed-v1",
                                              ".nimbus2-ffp", ".nimbus2-miner"]):
                continue
            
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))
        
        self.log(f"Found {len(md_files)} .md files")
        
        results = []
        batch_size = 100
        
        for i in range(0, len(md_files), batch_size):
            batch = md_files[i:i+batch_size]
            for filepath in batch:
                result = self.mine_file_fast(filepath)
                if result:
                    results.append(result)
                    self.files_processed += 1
            
            self.log(f"Processed batch {i//batch_size + 1}/{(len(md_files)-1)//batch_size + 1}")
        
        self.log(f"Fast mining complete: {self.files_processed} files")
        return results
    
    def generate_report(self):
        """Generate fast mining report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "files_mined": self.files_processed,
            "total_patterns": len(self.patterns),
            "total_code_blocks": len(self.code_blocks),
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "total_successes": len(self.successes),
            "pattern_summary": {p: len(f) for p, f in self.patterns.items()},
            "top_keywords": self.keywords.most_common(50),
            "error_summary": Counter(e["error"][:50] for e in self.errors).most_common(20),
            "warning_summary": Counter(w["warning"][:50] for w in self.warnings).most_common(20),
            "success_summary": Counter(s["success"][:50] for s in self.successes).most_common(20)
        }
        
        report_file = f"{MINER_DIR}/fast-miner-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        self.log(f"Report saved to {report_file}")
        return report

# Main execution
if __name__ == "__main__":
    miner = FastMiner()
    
    # Fast mining
    results = miner.mine_all_fast()
    
    # Generate report
    report = miner.generate_report()
    
    print(f"\n=== FAST MINING COMPLETE ===")
    print(f"Files mined: {report['files_mined']}")
    print(f"Patterns found: {report['total_patterns']}")
    print(f"Code blocks: {report['total_code_blocks']}")
    print(f"Errors found: {report['total_errors']}")
    print(f"Warnings found: {report['total_warnings']}")
    print(f"Successes found: {report['total_successes']}")
    print(f"\nTop patterns:")
    for pattern, count in sorted(report['pattern_summary'].items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {pattern}: {count} files")
