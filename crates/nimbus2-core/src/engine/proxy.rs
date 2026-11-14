// ffp: FFP-NIMBUS2-PROXY-RS concurrent-daemon rust
//! Bounded Concurrent HTTP & HTTPS CONNECT Proxy Engine.

use std::io::{self, BufRead, BufReader, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream, ToSocketAddrs};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

#[derive(Default)]
pub struct ProxyStats {
    pub active_streams: AtomicUsize,
    pub total_connections: AtomicU64,
    pub bytes_relayed: AtomicU64,
    pub rejected_over_cap: AtomicU64,
}

pub struct ProxyServer {
    listener: TcpListener,
    max_streams: usize,
    shutdown: Arc<AtomicBool>,
    stats: Arc<ProxyStats>,
}

impl ProxyServer {
    pub fn bind(listen_addr: &str, max_streams: usize) -> io::Result<Self> {
        let listener = TcpListener::bind(listen_addr)?;
        Ok(Self {
            listener,
            max_streams: max_streams.max(1),
            shutdown: Arc::new(AtomicBool::new(false)),
            stats: Arc::new(ProxyStats::default()),
        })
    }

    pub fn local_addr(&self) -> io::Result<SocketAddr> {
        self.listener.local_addr()
    }

    pub fn stats(&self) -> Arc<ProxyStats> {
        Arc::clone(&self.stats)
    }

    pub fn shutdown_handle(&self) -> Arc<AtomicBool> {
        Arc::clone(&self.shutdown)
    }

    pub fn serve_max_connections(&self, limit: usize) -> io::Result<()> {
        let mut handled = 0usize;
        let mut workers = Vec::new();
        while handled < limit && !self.shutdown.load(Ordering::Relaxed) {
            let (client, _) = self.listener.accept()?;
            handled += 1;
            let stats = Arc::clone(&self.stats);
            let max_streams = self.max_streams;
            workers.push(thread::spawn(move || {
                let _ = handle_client(client, max_streams, stats);
            }));
        }
        for w in workers {
            let _ = w.join();
        }
        Ok(())
    }

    pub fn serve_until_shutdown(&self) -> io::Result<()> {
        self.listener.set_nonblocking(true)?;
        while !self.shutdown.load(Ordering::Relaxed) {
            match self.listener.accept() {
                Ok((client, _)) => {
                    let stats = Arc::clone(&self.stats);
                    let max_streams = self.max_streams;
                    thread::spawn(move || {
                        let _ = handle_client(client, max_streams, stats);
                    });
                }
                Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                    thread::sleep(Duration::from_millis(20));
                }
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
}

fn handle_client(mut client: TcpStream, max_streams: usize, stats: Arc<ProxyStats>) -> io::Result<()> {
    let prev = stats.active_streams.fetch_add(1, Ordering::AcqRel);
    if prev >= max_streams {
        stats.active_streams.fetch_sub(1, Ordering::AcqRel);
        stats.rejected_over_cap.fetch_add(1, Ordering::Relaxed);
        let _ = client.write_all(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n");
        return Ok(());
    }
    stats.total_connections.fetch_add(1, Ordering::Relaxed);
    let res = process_http_or_connect(&mut client, &stats);
    stats.active_streams.fetch_sub(1, Ordering::AcqRel);
    res
}

fn process_http_or_connect(client: &mut TcpStream, stats: &Arc<ProxyStats>) -> io::Result<()> {
    let _ = client.set_read_timeout(Some(Duration::from_secs(15)));
    let _ = client.set_write_timeout(Some(Duration::from_secs(15)));

    let mut reader = BufReader::new(client.try_clone()?);
    let mut request_line = String::new();
    if reader.read_line(&mut request_line)? == 0 {
        return Ok(());
    }
    let parts: Vec<&str> = request_line.trim_end().split_whitespace().collect();
    if parts.len() < 3 {
        let _ = client.write_all(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n");
        return Ok(());
    }
    let method = parts[0];
    let target = parts[1];
    let version = parts[2];

    let mut headers = Vec::new();
    let mut host_header = String::new();
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line)? == 0 || line == "\r\n" || line == "\n" {
            break;
        }
        if let Some((k, v)) = line.split_once(':') {
            if k.eq_ignore_ascii_case("host") {
                host_header = v.trim().to_string();
            }
            if !k.eq_ignore_ascii_case("proxy-connection") && !k.eq_ignore_ascii_case("connection") {
                headers.push(line);
            }
        }
    }

    if method.eq_ignore_ascii_case("CONNECT") {
        let addr_str = if target.contains(':') {
            target.to_string()
        } else {
            format!("{}:443", target)
        };
        let sock_addr = resolve_first(&addr_str)?;
        let upstream = TcpStream::connect_timeout(&sock_addr, Duration::from_secs(10))?;
        client.write_all(b"HTTP/1.1 200 Connection Established\r\n\r\n")?;
        let relayed = relay_bidirectional(client.try_clone()?, upstream)?;
        stats.bytes_relayed.fetch_add(relayed, Ordering::Relaxed);
        return Ok(());
    }

    let (upstream_host, path) = parse_http_target(target, &host_header)?;
    let sock_addr = resolve_first(&upstream_host)?;
    let mut upstream = TcpStream::connect_timeout(&sock_addr, Duration::from_secs(10))?;
    let _ = upstream.set_read_timeout(Some(Duration::from_secs(15)));
    let _ = upstream.set_write_timeout(Some(Duration::from_secs(15)));

    let mut out_head = format!("{} {} {}\r\n", method, path, version);
    for h in headers {
        out_head.push_str(&h);
    }
    out_head.push_str("Connection: close\r\n\r\n");
    upstream.write_all(out_head.as_bytes())?;

    let buffered = reader.buffer();
    if !buffered.is_empty() {
        upstream.write_all(buffered)?;
    }
    drop(reader);
    let copied = io::copy(&mut upstream, client)?;
    let _ = client.shutdown(Shutdown::Write);
    stats.bytes_relayed.fetch_add(copied, Ordering::Relaxed);
    Ok(())
}

fn parse_http_target(target: &str, host_header: &str) -> io::Result<(String, String)> {
    if let Some(rest) = target.strip_prefix("http://") {
        let (host_port, path) = match rest.find('/') {
            Some(idx) => (&rest[..idx], &rest[idx..]),
            None => (rest, "/"),
        };
        let addr = if host_port.contains(':') {
            host_port.to_string()
        } else {
            format!("{}:80", host_port)
        };
        return Ok((addr, path.to_string()));
    }
    if host_header.is_empty() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "missing Host header"));
    }
    let addr = if host_header.contains(':') {
        host_header.to_string()
    } else {
        format!("{}:80", host_header)
    };
    Ok((addr, target.to_string()))
}

fn resolve_first(addr: &str) -> io::Result<SocketAddr> {
    addr.to_socket_addrs()?
        .next()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "unable to resolve upstream"))
}

fn relay_bidirectional(mut a: TcpStream, mut b: TcpStream) -> io::Result<u64> {
    let mut a_clone = a.try_clone()?;
    let mut b_clone = b.try_clone()?;
    let t = thread::spawn(move || -> u64 {
        let n = io::copy(&mut a_clone, &mut b_clone).unwrap_or(0);
        let _ = b_clone.shutdown(Shutdown::Write);
        n
    });
    let n2 = io::copy(&mut b, &mut a).unwrap_or(0);
    let _ = a.shutdown(Shutdown::Write);
    let n1 = t.join().unwrap_or(0);
    Ok(n1 + n2)
}
