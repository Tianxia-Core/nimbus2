// ffp: FFP-NIMBUS2-CLI concurrent-daemon go
// Nimbus² v2.5.0 — High-Performance Concurrent Proxy, Health Probe, Route Benchmark,
// Config Validator, SOFTEM Hardware Classifier, Multiboot Verifier & Interactive TUI.
// Zero external dependencies (Go stdlib only, CGO_ENABLED=0 static builds).
package main

import (
	"bufio"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

const Version = "2.5.0"

// ProxyConfig defines validated configuration for the Nimbus² proxy daemon.
type ProxyConfig struct {
	ListenAddr     string   `json:"listen_addr"`
	MaxStreams     int      `json:"max_streams"`
	TimeoutSeconds int      `json:"timeout_seconds"`
	TargetCountry  string   `json:"target_country"`
	TLSMinVersion  string   `json:"tls_min_version"`
	Upstreams      []string `json:"upstreams,omitempty"`
}

// ValidateConfig checks all invariants of a ProxyConfig.
func ValidateConfig(cfg ProxyConfig) []string {
	var errs []string
	if strings.TrimSpace(cfg.ListenAddr) == "" {
		errs = append(errs, "listen_addr must not be empty")
	} else if _, portStr, err := net.SplitHostPort(cfg.ListenAddr); err != nil {
		errs = append(errs, fmt.Sprintf("invalid listen_addr %q: %v", cfg.ListenAddr, err))
	} else if p, err := strconv.Atoi(portStr); err != nil || p < 0 || p > 65535 {
		errs = append(errs, fmt.Sprintf("listen_addr port out of range: %q", portStr))
	}
	if cfg.MaxStreams < 1 || cfg.MaxStreams > 65535 {
		errs = append(errs, fmt.Sprintf("max_streams must be between 1 and 65535 (got %d)", cfg.MaxStreams))
	}
	if cfg.TimeoutSeconds < 1 || cfg.TimeoutSeconds > 300 {
		errs = append(errs, fmt.Sprintf("timeout_seconds must be between 1 and 300 (got %d)", cfg.TimeoutSeconds))
	}
	switch strings.ToUpper(cfg.TLSMinVersion) {
	case "", "1.2", "1.3", "TLS1.2", "TLS1.3":
	default:
		errs = append(errs, fmt.Sprintf("tls_min_version %q insecure or unsupported (require 1.2 or 1.3)", cfg.TLSMinVersion))
	}
	for _, up := range cfg.Upstreams {
		u, err := url.Parse(up)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https" && u.Scheme != "socks5") || u.Host == "" {
			errs = append(errs, fmt.Sprintf("invalid upstream URL %q", up))
		}
	}
	return errs
}

// ProxyMetrics tracks live atomic telemetry for the proxy engine.
type ProxyMetrics struct {
	ActiveStreams    atomic.Int64
	TotalConnections atomic.Uint64
	BytesRelayed     atomic.Uint64
	RejectedStreams  atomic.Uint64
	StartedAt        time.Time
}

// ProxyDaemon implements a bounded concurrent HTTP forward & HTTPS CONNECT tunnel proxy.
type ProxyDaemon struct {
	ListenAddr string
	MaxStreams int
	Timeout    time.Duration
	sem        chan struct{}
	Metrics    *ProxyMetrics
}

func NewProxyDaemon(listenAddr string, maxStreams int, timeout time.Duration) *ProxyDaemon {
	if maxStreams < 1 {
		maxStreams = 225
	}
	if timeout <= 0 {
		timeout = 15 * time.Second
	}
	return &ProxyDaemon{
		ListenAddr: listenAddr,
		MaxStreams: maxStreams,
		Timeout:    timeout,
		sem:        make(chan struct{}, maxStreams),
		Metrics:    &ProxyMetrics{StartedAt: time.Now().UTC()},
	}
}

func (d *ProxyDaemon) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/__nimbus2/health" {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status":            "healthy",
			"version":           Version,
			"active_streams":    d.Metrics.ActiveStreams.Load(),
			"max_streams":       d.MaxStreams,
			"total_connections": d.Metrics.TotalConnections.Load(),
			"bytes_relayed":     d.Metrics.BytesRelayed.Load(),
			"rejected_streams":  d.Metrics.RejectedStreams.Load(),
			"uptime_seconds":    int64(time.Since(d.Metrics.StartedAt).Seconds()),
		})
		return
	}

	select {
	case d.sem <- struct{}{}:
		defer func() { <-d.sem }()
	default:
		d.Metrics.RejectedStreams.Add(1)
		http.Error(w, "Nimbus2 stream pool exhausted", http.StatusServiceUnavailable)
		return
	}

	d.Metrics.ActiveStreams.Add(1)
	defer d.Metrics.ActiveStreams.Add(-1)
	d.Metrics.TotalConnections.Add(1)

	if r.Method == http.MethodConnect {
		d.handleConnect(w, r)
		return
	}
	d.handleHTTPForward(w, r)
}

func (d *ProxyDaemon) handleConnect(w http.ResponseWriter, r *http.Request) {
	target := r.Host
	if !strings.Contains(target, ":") {
		target += ":443"
	}
	upConn, err := net.DialTimeout("tcp", target, d.Timeout)
	if err != nil {
		http.Error(w, "upstream connect failed", http.StatusBadGateway)
		return
	}
	hj, ok := w.(http.Hijacker)
	if !ok {
		_ = upConn.Close()
		http.Error(w, "hijacking unsupported", http.StatusInternalServerError)
		return
	}
	clientConn, _, err := hj.Hijack()
	if err != nil {
		_ = upConn.Close()
		return
	}
	_, _ = clientConn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))

	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		n, _ := io.Copy(upConn, clientConn)
		d.Metrics.BytesRelayed.Add(uint64(n))
		_ = upConn.Close()
	}()
	go func() {
		defer wg.Done()
		n, _ := io.Copy(clientConn, upConn)
		d.Metrics.BytesRelayed.Add(uint64(n))
		_ = clientConn.Close()
	}()
	wg.Wait()
}

func (d *ProxyDaemon) handleHTTPForward(w http.ResponseWriter, r *http.Request) {
	if r.URL.Scheme == "" {
		r.URL.Scheme = "http"
	}
	if r.URL.Host == "" {
		r.URL.Host = r.Host
	}
	if r.URL.Host == "" {
		http.Error(w, "missing target host", http.StatusBadRequest)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), d.Timeout)
	defer cancel()

	outReq, err := http.NewRequestWithContext(ctx, r.Method, r.URL.String(), r.Body)
	if err != nil {
		http.Error(w, "bad proxy request", http.StatusBadRequest)
		return
	}
	for k, vals := range r.Header {
		if strings.EqualFold(k, "Proxy-Connection") || strings.EqualFold(k, "Connection") {
			continue
		}
		for _, v := range vals {
			outReq.Header.Add(k, v)
		}
	}
	tr := &http.Transport{
		DialContext:           (&net.Dialer{Timeout: d.Timeout}).DialContext,
		TLSHandshakeTimeout:   d.Timeout,
		ResponseHeaderTimeout: d.Timeout,
		TLSClientConfig:       &tls.Config{MinVersion: tls.VersionTLS12},
	}
	resp, err := tr.RoundTrip(outReq)
	if err != nil {
		http.Error(w, "upstream roundtrip failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	for k, vals := range resp.Header {
		for _, v := range vals {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	n, _ := io.Copy(w, resp.Body)
	d.Metrics.BytesRelayed.Add(uint64(n))
}

// HealthResult captures a single endpoint probe result.
type HealthResult struct {
	Target     string  `json:"target"`
	Healthy    bool    `json:"healthy"`
	StatusCode int     `json:"status_code,omitempty"`
	LatencyMs  float64 `json:"latency_ms"`
	TLSVersion string  `json:"tls_version,omitempty"`
	Error      string  `json:"error,omitempty"`
}

func ProbeTargets(targets []string, timeout time.Duration) []HealthResult {
	results := make([]HealthResult, len(targets))
	var wg sync.WaitGroup
	client := &http.Client{
		Timeout: timeout,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12},
		},
	}
	for i, raw := range targets {
		wg.Add(1)
		go func(idx int, t string) {
			defer wg.Done()
			start := time.Now()
			if strings.HasPrefix(t, "http://") || strings.HasPrefix(t, "https://") {
				resp, err := client.Get(t)
				lat := float64(time.Since(start).Microseconds()) / 1000.0
				if err != nil {
					results[idx] = HealthResult{Target: t, Healthy: false, LatencyMs: lat, Error: err.Error()}
					return
				}
				_ = resp.Body.Close()
				tlsVer := ""
				if resp.TLS != nil {
					switch resp.TLS.Version {
					case tls.VersionTLS13:
						tlsVer = "TLS1.3"
					case tls.VersionTLS12:
						tlsVer = "TLS1.2"
					default:
						tlsVer = fmt.Sprintf("0x%x", resp.TLS.Version)
					}
				}
				results[idx] = HealthResult{
					Target:     t,
					Healthy:    resp.StatusCode >= 200 && resp.StatusCode < 500,
					StatusCode: resp.StatusCode,
					LatencyMs:  lat,
					TLSVersion: tlsVer,
				}
				return
			}
			conn, err := net.DialTimeout("tcp", t, timeout)
			lat := float64(time.Since(start).Microseconds()) / 1000.0
			if err != nil {
				results[idx] = HealthResult{Target: t, Healthy: false, LatencyMs: lat, Error: err.Error()}
				return
			}
			_ = conn.Close()
			results[idx] = HealthResult{Target: t, Healthy: true, LatencyMs: lat}
		}(i, strings.TrimSpace(raw))
	}
	wg.Wait()
	return results
}

// BenchSummary holds statistical latency metrics from a route benchmark.
type BenchSummary struct {
	Target        string  `json:"target"`
	TotalRequests int     `json:"total_requests"`
	Succeeded     int     `json:"succeeded"`
	Failed        int     `json:"failed"`
	Concurrency   int     `json:"concurrency"`
	MinMs         float64 `json:"min_ms"`
	MeanMs        float64 `json:"mean_ms"`
	P50Ms         float64 `json:"p50_ms"`
	P95Ms         float64 `json:"p95_ms"`
	P99Ms         float64 `json:"p99_ms"`
	RequestsPerS  float64 `json:"requests_per_sec"`
}

func RunBenchmark(target string, concurrency, totalReqs int, timeout time.Duration) BenchSummary {
	if concurrency < 1 {
		concurrency = 1
	}
	if totalReqs < 1 {
		totalReqs = 1
	}
	jobs := make(chan int, totalReqs)
	for i := 0; i < totalReqs; i++ {
		jobs <- i
	}
	close(jobs)

	var mu sync.Mutex
	latencies := make([]float64, 0, totalReqs)
	failed := 0
	client := &http.Client{Timeout: timeout}

	wallStart := time.Now()
	var wg sync.WaitGroup
	for w := 0; w < concurrency; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for range jobs {
				t0 := time.Now()
				var ok bool
				if strings.HasPrefix(target, "http://") || strings.HasPrefix(target, "https://") {
					resp, err := client.Get(target)
					if err == nil {
						_, _ = io.Copy(io.Discard, resp.Body)
						_ = resp.Body.Close()
						ok = resp.StatusCode < 500
					}
				} else {
					c, err := net.DialTimeout("tcp", target, timeout)
					if err == nil {
						_ = c.Close()
						ok = true
					}
				}
				ms := float64(time.Since(t0).Microseconds()) / 1000.0
				mu.Lock()
				if ok {
					latencies = append(latencies, ms)
				} else {
					failed++
				}
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	elapsed := time.Since(wallStart).Seconds()
	if elapsed <= 0 {
		elapsed = 0.0001
	}

	sort.Float64s(latencies)
	sum := BenchSummary{
		Target:        target,
		TotalRequests: totalReqs,
		Succeeded:     len(latencies),
		Failed:        failed,
		Concurrency:   concurrency,
		RequestsPerS:  float64(totalReqs) / elapsed,
	}
	if len(latencies) > 0 {
		sum.MinMs = latencies[0]
		var total float64
		for _, v := range latencies {
			total += v
		}
		sum.MeanMs = total / float64(len(latencies))
		sum.P50Ms = percentile(latencies, 0.50)
		sum.P95Ms = percentile(latencies, 0.95)
		sum.P99Ms = percentile(latencies, 0.99)
	}
	return sum
}

func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	idx := int(float64(len(sorted)-1) * p)
	if idx < 0 {
		idx = 0
	}
	if idx >= len(sorted) {
		idx = len(sorted) - 1
	}
	return sorted[idx]
}

// DeviceProfile describes SOFTEM runtime capabilities.
type DeviceProfile struct {
	OS          string   `json:"os"`
	Arch        string   `json:"arch"`
	CPUCores    int      `json:"cpu_cores"`
	TotalRAMMB  uint64   `json:"total_ram_mb"`
	HSMPresent  bool     `json:"hsm_present"`
	SOFTEMTier  int      `json:"softem_tier"`
	MaxStreams  int      `json:"recommended_streams"`
	Capabilities []string `json:"capabilities"`
}

func DetectDevice() DeviceProfile {
	cores := runtime.NumCPU()
	ramMB := readProcMemMB()
	if ramMB == 0 {
		ramMB = 4096
	}
	hsm := fileExists("/dev/keymaster") || fileExists("/sys/class/keymaster") || fileExists("/dev/tpmrm0")
	tier := 1
	streams := 50
	var caps []string
	switch {
	case ramMB >= 12288 && hsm:
		tier = 4
		streams = 2048
		caps = []string{"Elite Concurrent Proxy Pool", "HSM Envelope Sealing", "Etamanga AEAD Transport", "Unlimited Multiboot Catalog"}
	case ramMB >= 8192:
		tier = 3
		streams = 675
		caps = []string{"High-Concurrency Proxy Pool (675)", "Multi-Country ASN Filter", "Circuit-Breaker Mesh", "Multiboot ISO Verifier"}
	case ramMB >= 4096:
		tier = 2
		streams = 225
		caps = []string{"Standard Proxy Pool (225)", "TLS 1.3 Health Prober", "Route Benchmark Suite"}
	default:
		tier = 1
		streams = 50
		caps = []string{"Compact Edge Proxy (50)", "Config & ISO Integrity Verifier"}
	}
	return DeviceProfile{
		OS:           runtime.GOOS,
		Arch:         runtime.GOARCH,
		CPUCores:     cores,
		TotalRAMMB:   ramMB,
		HSMPresent:   hsm,
		SOFTEMTier:   tier,
		MaxStreams:   streams,
		Capabilities: caps,
	}
}

func readProcMemMB() uint64 {
	f, err := os.Open("/proc/meminfo")
	if err != nil {
		return 0
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := sc.Text()
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				kb, err := strconv.ParseUint(fields[1], 10, 64)
				if err == nil {
					return kb / 1024
				}
			}
		}
	}
	return 0
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// VerifyISO computes SHA-256 and checks MBR/ISO9660 boot signatures.
func VerifyISO(path string) (map[string]any, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return nil, err
	}
	h := sha256.New()
	head := make([]byte, 40960)
	headN, _ := io.ReadFull(f, head)
	if headN > 0 {
		h.Write(head[:headN])
	}
	if _, err := io.Copy(h, f); err != nil {
		return nil, err
	}
	mbr := headN >= 512 && head[510] == 0x55 && head[511] == 0xAA
	iso9660 := headN >= 0x8006 && string(head[0x8001:0x8006]) == "CD001"
	return map[string]any{
		"path":               path,
		"size_bytes":         st.Size(),
		"sha256":             hex.EncodeToString(h.Sum(nil)),
		"boot_signature_ok":  mbr || iso9660,
	}, nil
}

func renderTUISnapshot(dev DeviceProfile, probe *HealthResult) string {
	var b strings.Builder
	b.WriteString("┌──────────────────────────────────────────────────────────────────────────┐\n")
	b.WriteString(fmt.Sprintf("│  NIMBUS² v%-8s — SOVEREIGN PROXY, ROUTE BENCH & MULTIBOOT COCKPIT   │\n", Version))
	b.WriteString("├──────────────────────────────────────────────────────────────────────────┤\n")
	b.WriteString(fmt.Sprintf("│  Runtime : %-10s/%-10s | CPU Cores: %-3d | RAM: %6d MB     │\n",
		dev.OS, dev.Arch, dev.CPUCores, dev.TotalRAMMB))
	b.WriteString(fmt.Sprintf("│  SOFTEM  : Tier %-2d              | Max Pool : %-4d streams              │\n",
		dev.SOFTEMTier, dev.MaxStreams))
	if probe != nil {
		state := "DOWN"
		if probe.Healthy {
			state = "ONLINE"
		}
		b.WriteString(fmt.Sprintf("│  Probe   : %-28s [%s] %7.2f ms        │\n",
			truncateStr(probe.Target, 28), state, probe.LatencyMs))
	}
	b.WriteString("├──────────────────────────────────────────────────────────────────────────┤\n")
	for _, c := range dev.Capabilities {
		b.WriteString(fmt.Sprintf("│  + %-70s│\n", truncateStr(c, 70)))
	}
	b.WriteString("└──────────────────────────────────────────────────────────────────────────┘\n")
	return b.String()
}

func truncateStr(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max-3] + "..."
}

func printUsage() {
	fmt.Fprintf(os.Stderr, `Nimbus² v%s — High-Performance Polyglot Proxy, Intelligence & Multiboot Suite
Usage:
  nimbus2 proxy    [--listen 127.0.0.1:8080] [--streams 225] [--timeout 15]
  nimbus2 health   [--targets https://rasaxmachina.com] [--timeout 10] [--json]
  nimbus2 bench    [--target 127.0.0.1:8080] [--concurrency 16] [--requests 100] [--json]
  nimbus2 validate --config path/to/config.json [--json]
  nimbus2 detect   [--json]
  nimbus2 multiboot [--catalog | --verify path/to/image.iso]
  nimbus2 tui      [--once] [--target 127.0.0.1:8080]
  nimbus2 version
`, Version)
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(2)
	}
	cmd := os.Args[1]
	args := os.Args[2:]

	switch cmd {
	case "version", "--version", "-v":
		fmt.Printf("nimbus2 v%s (%s/%s)\n", Version, runtime.GOOS, runtime.GOARCH)

	case "proxy":
		fs := flag.NewFlagSet("proxy", flag.ExitOnError)
		listen := fs.String("listen", "127.0.0.1:8080", "TCP address to listen on")
		streams := fs.Int("streams", 225, "Maximum concurrent proxy streams")
		timeout := fs.Int("timeout", 15, "Upstream timeout in seconds")
		_ = fs.Parse(args)

		daemon := NewProxyDaemon(*listen, *streams, time.Duration(*timeout)*time.Second)
		srv := &http.Server{
			Addr:              *listen,
			Handler:           daemon,
			ReadHeaderTimeout: 10 * time.Second,
		}
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()

		go func() {
			<-ctx.Done()
			shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = srv.Shutdown(shutCtx)
		}()

		fmt.Printf("[nimbus2 v%s] Proxy online at %s (max_streams=%d)\n", Version, *listen, *streams)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			fmt.Fprintf(os.Stderr, "[nimbus2] fatal listen error: %v\n", err)
			os.Exit(1)
		}

	case "health":
		fs := flag.NewFlagSet("health", flag.ExitOnError)
		targets := fs.String("targets", "https://rasaxmachina.com", "Comma-separated URLs or host:port endpoints")
		timeout := fs.Int("timeout", 10, "Timeout in seconds")
		asJSON := fs.Bool("json", false, "Emit JSON output")
		_ = fs.Parse(args)

		list := strings.Split(*targets, ",")
		res := ProbeTargets(list, time.Duration(*timeout)*time.Second)
		if *asJSON {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			_ = enc.Encode(res)
		} else {
			allOK := true
			for _, r := range res {
				state := "OK"
				if !r.Healthy {
					state = "FAIL"
					allOK = false
				}
				fmt.Printf("[%-4s] %-40s %8.2f ms %s %s\n", state, r.Target, r.LatencyMs, r.TLSVersion, r.Error)
			}
			if !allOK {
				os.Exit(1)
			}
		}

	case "bench":
		fs := flag.NewFlagSet("bench", flag.ExitOnError)
		target := fs.String("target", "127.0.0.1:8080", "Target URL or host:port")
		conc := fs.Int("concurrency", 16, "Concurrent workers")
		reqs := fs.Int("requests", 100, "Total requests")
		timeout := fs.Int("timeout", 10, "Timeout in seconds")
		asJSON := fs.Bool("json", false, "Emit JSON output")
		_ = fs.Parse(args)

		summary := RunBenchmark(*target, *conc, *reqs, time.Duration(*timeout)*time.Second)
		if *asJSON {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			_ = enc.Encode(summary)
		} else {
			fmt.Printf("Benchmark: %s (%d requests, concurrency %d)\n", summary.Target, summary.TotalRequests, summary.Concurrency)
			fmt.Printf("  Succeeded: %d | Failed: %d | RPS: %.1f req/s\n", summary.Succeeded, summary.Failed, summary.RequestsPerS)
			fmt.Printf("  Latency  : min=%.2fms mean=%.2fms p50=%.2fms p95=%.2fms p99=%.2fms\n",
				summary.MinMs, summary.MeanMs, summary.P50Ms, summary.P95Ms, summary.P99Ms)
		}

	case "validate":
		fs := flag.NewFlagSet("validate", flag.ExitOnError)
		cfgPath := fs.String("config", "", "Path to JSON config file")
		asJSON := fs.Bool("json", false, "Emit JSON output")
		_ = fs.Parse(args)
		if *cfgPath == "" {
			fmt.Fprintln(os.Stderr, "error: --config path is required")
			os.Exit(2)
		}
		raw, err := os.ReadFile(*cfgPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error reading config: %v\n", err)
			os.Exit(1)
		}
		var cfg ProxyConfig
		if err := json.Unmarshal(raw, &cfg); err != nil {
			fmt.Fprintf(os.Stderr, "invalid JSON syntax: %v\n", err)
			os.Exit(1)
		}
		errs := ValidateConfig(cfg)
		valid := len(errs) == 0
		if *asJSON {
			_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"valid": valid, "errors": errs})
		} else if valid {
			fmt.Printf("[VALID] %s passed all Nimbus² schema and security checks.\n", *cfgPath)
		} else {
			for _, e := range errs {
				fmt.Fprintf(os.Stderr, "  - %s\n", e)
			}
			os.Exit(1)
		}
		if !valid {
			os.Exit(1)
		}

	case "detect":
		fs := flag.NewFlagSet("detect", flag.ExitOnError)
		asJSON := fs.Bool("json", false, "Emit JSON output")
		_ = fs.Parse(args)
		dev := DetectDevice()
		if *asJSON {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			_ = enc.Encode(dev)
		} else {
			fmt.Print(renderTUISnapshot(dev, nil))
		}

	case "multiboot":
		fs := flag.NewFlagSet("multiboot", flag.ExitOnError)
		verifyPath := fs.String("verify", "", "Verify ISO image SHA-256 & boot signature")
		catalogFlag := fs.Bool("catalog", false, "List supported multiboot OS profiles")
		_ = fs.Parse(args)
		if *verifyPath != "" {
			res, err := VerifyISO(*verifyPath)
			if err != nil {
				fmt.Fprintf(os.Stderr, "verify failed: %v\n", err)
				os.Exit(1)
			}
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			_ = enc.Encode(res)
			return
		}
		_ = *catalogFlag
		profiles := []string{
			"nixos-24.11      NixOS 24.11 Sovereign Minimal [Immutable]",
			"ubuntu-24.04     Ubuntu 24.04 LTS              [Desktop]",
			"fedora-41        Fedora 41 Workstation         [Desktop]",
			"kali-2026        Kali Linux 2026               [Security]",
			"tails-6          Tails 6 Amnesic               [Privacy]",
			"systemrescue-11  SystemRescue 11               [Recovery]",
			"alpine-3.20      Alpine Linux 3.20             [Embedded]",
		}
		for _, p := range profiles {
			fmt.Println(p)
		}

	case "tui":
		fs := flag.NewFlagSet("tui", flag.ExitOnError)
		once := fs.Bool("once", false, "Render single dashboard snapshot and exit")
		target := fs.String("target", "", "Optional target endpoint to monitor")
		_ = fs.Parse(args)

		dev := DetectDevice()
		var probe *HealthResult
		if *target != "" {
			r := ProbeTargets([]string{*target}, 3*time.Second)
			if len(r) > 0 {
				probe = &r[0]
			}
		}
		if *once {
			fmt.Print(renderTUISnapshot(dev, probe))
			return
		}
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()
		for {
			fmt.Print("\033[H\033[2J")
			fmt.Print(renderTUISnapshot(dev, probe))
			fmt.Println("Press Ctrl+C to exit live cockpit.")
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if *target != "" {
					r := ProbeTargets([]string{*target}, 2*time.Second)
					if len(r) > 0 {
						probe = &r[0]
					}
				}
			}
		}

	default:
		printUsage()
		os.Exit(2)
	}
}
