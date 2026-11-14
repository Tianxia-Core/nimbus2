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
