// ffp: FFP-NIMBUS2-CLI-TEST concurrent-daemon go
package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestValidateConfig(t *testing.T) {
	good := ProxyConfig{
		ListenAddr:     "127.0.0.1:8080",
		MaxStreams:     225,
		TimeoutSeconds: 15,
		TargetCountry:  "EE",
		TLSMinVersion:  "1.3",
		Upstreams:      []string{"https://rasaxmachina.com"},
	}
	if errs := ValidateConfig(good); len(errs) != 0 {
		t.Fatalf("expected valid config, got: %v", errs)
	}

	bad := ProxyConfig{
		ListenAddr:     "bad-addr",
		MaxStreams:     0,
		TimeoutSeconds: 999,
		TLSMinVersion:  "1.0",
		Upstreams:      []string{"ftp://invalid"},
	}
	if errs := ValidateConfig(bad); len(errs) < 4 {
		t.Fatalf("expected multiple validation errors, got: %v", errs)
	}
}

func TestProxyForwardAndHealthAndBench(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("NIMBUS2_GO_UPSTREAM_OK"))
	}))
	defer upstream.Close()

	daemon := NewProxyDaemon("127.0.0.1:0", 32, 5*time.Second)
	proxySrv := httptest.NewServer(daemon)
	defer proxySrv.Close()

	proxyURL, err := url.Parse(proxySrv.URL)
	if err != nil {
		t.Fatal(err)
	}
	client := &http.Client{
		Transport: &http.Transport{Proxy: http.ProxyURL(proxyURL)},
		Timeout:   5 * time.Second,
	}
	resp, err := client.Get(upstream.URL + "/probe")
	if err != nil {
		t.Fatalf("proxy GET failed: %v", err)
	}
	body, _ := io.ReadAll(resp.Body)
	_ = resp.Body.Close()
	if string(body) != "NIMBUS2_GO_UPSTREAM_OK" {
		t.Fatalf("unexpected body %q", string(body))
	}

	probes := ProbeTargets([]string{proxySrv.URL + "/__nimbus2/health"}, 3*time.Second)
	if len(probes) != 1 || !probes[0].Healthy {
		t.Fatalf("expected healthy proxy endpoint, got %+v", probes)
	}

	bench := RunBenchmark(proxySrv.URL+"/__nimbus2/health", 4, 20, 3*time.Second)
	if bench.Succeeded != 20 || bench.Failed != 0 {
		t.Fatalf("unexpected benchmark summary: %+v", bench)
	}
}

func TestDetectVerifyISOAndTUI(t *testing.T) {
	dev := DetectDevice()
	if dev.CPUCores < 1 || dev.SOFTEMTier < 1 {
		t.Fatalf("invalid device profile: %+v", dev)
	}
	snap := renderTUISnapshot(dev, nil)
	if !strings.Contains(snap, "NIMBUS²") {
		t.Fatalf("missing header in TUI snapshot")
	}

	tmp := filepath.Join(t.TempDir(), "test.iso")
	buf := make([]byte, 1024)
	buf[510] = 0x55
	buf[511] = 0xAA
	if err := os.WriteFile(tmp, buf, 0o600); err != nil {
		t.Fatal(err)
	}
	info, err := VerifyISO(tmp)
	if err != nil {
		t.Fatal(err)
	}
	if ok, _ := info["boot_signature_ok"].(bool); !ok {
		t.Fatalf("expected MBR boot signature to be recognized: %+v", info)
	}
}

func TestBuildManagerDiffReviewCleanroomAndFCEstimator(t *testing.T) {
	cleanDiff := `--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Clean Project
+Deterministic engineering enabled.
`
	repOK := ReviewDiffText(cleanDiff, []string{"README.md"})
	if !repOK.CanAutoMerge || repOK.Verdict != "APPROVED_FOR_MERGE" || repOK.RiskTier != "LOW" {
		t.Fatalf("expected clean diff approval, got %+v", repOK)
	}

	// Verify Clean-Room blocks personal lead sheets, populated DBs, Cargo 0.x breaking bumps, and secrets
	synthTok := "sk_" + "live_" + "000000000000deadbeef"
	badDiff := "--- a/Cargo.toml\n+++ b/Cargo.toml\n@@ -4,1 +4,2 @@\n-rand = \"0.8.5\"\n+rand = \"0.9.0\"\n+api = \"" + synthTok + "\"\n"
	repBad := ReviewDiffText(badDiff, []string{"Cargo.toml", "leads_export.xlsx", "vault_data.sqlite3"})
	if repBad.CanAutoMerge || repBad.Verdict != "HOLD_REQUIRES_REMEDIATION" || repBad.RiskTier != "CRITICAL" {
		t.Fatalf("expected blocking verdict on secret + xlsx + sqlite3 + Cargo 0.x bump, got %+v", repBad)
	}
	if len(repBad.Findings) < 3 {
		t.Fatalf("expected >= 3 distinct findings, got %+v", repBad.Findings)
	}

	// Verify InitCleanSeedWorkspace creates a 100% Clean-Room compliant user workspace
	seedDir := filepath.Join(t.TempDir(), "fresh-user-workspace")
	initRep, err := InitCleanSeedWorkspace(seedDir)
	if err != nil || !initRep.OK || len(initRep.SeededArtifacts) < 3 {
		t.Fatalf("InitCleanSeedWorkspace failed: err=%v rep=%+v", err, initRep)
	}
	auditRep := AuditCleanroomDirectory(seedDir)
	if !auditRep.OK || len(auditRep.Violations) != 0 {
		t.Fatalf("expected freshly seeded workspace to pass Clean-Room audit, got %+v", auditRep)
	}

	// Verify FC Algebraic Estimator v4.2 calibration & 8-FFP decomposition
	est := ComputeFCEstimate(FCEstimateInput{
		FunctionCount:   250,
		ParallelAgents:  15,
		FileIOOps:       100,
		NetworkRequests: 20,
		BuildLawActive:  true,
	})
	if est.RecommendedServicesMax8FFP != 32 {
		t.Fatalf("expected ceil(250/8)=32 services, got %d", est.RecommendedServicesMax8FFP)
	}
	if est.TokenCompressionRatio != 8.8 || est.NetSavingsEUR <= 0 || est.AutonomousActiveSeconds <= 0 {
		t.Fatalf("unexpected FC estimate economics: %+v", est)
	}
}
