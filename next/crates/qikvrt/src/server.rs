// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
use crate::{
    compiler,
    store::{now, Command, Store},
    Result,
};
use serde_json::json;
use std::{
    io::{BufReader, Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::Path,
    time::Duration,
};

pub fn serve(root: &Path, address: &str) -> Result<()> {
    let address: SocketAddr = address.parse().map_err(|_| "INVALID_LISTEN_ADDRESS")?;
    if address.ip().to_string() != "127.0.0.1" {
        return Err("LOOPBACK_ONLY".into());
    }
    let mut store = Store::open(root)?;
    let listener = TcpListener::bind(address).map_err(|e| e.to_string())?;
    let bound = listener.local_addr().map_err(|e| e.to_string())?;
    println!(
        "{}",
        json!({"state":"LISTENING","address":bound.to_string(),"checkpoint":store.checkpoint(),"done":false})
    );
    std::io::stdout().flush().map_err(|e| e.to_string())?;
    for client in listener.incoming() {
        let mut client = client.map_err(|e| e.to_string())?;
        let _ = client.set_read_timeout(Some(Duration::from_secs(3)));
        let _ = client.set_write_timeout(Some(Duration::from_secs(3)));
        if let Err(e) = handle_with(&mut client, bound.port(), |method, path, body| {
            dispatch(&mut store, method, path, body)
        }) {
            let _ = respond(
                &mut client,
                400,
                "application/json",
                json!({"state":"HOLD","reason":e,"done":false})
                    .to_string()
                    .as_bytes(),
            );
        }
        // Client disconnect and bad input end that request; the owner loop continues.
    }
    Ok(())
}
fn respond(stream: &mut TcpStream, code: u16, kind: &str, body: &[u8]) -> Result<()> {
    let reason = match code {
        200 => "OK",
        404 => "Not Found",
        403 => "Forbidden",
        _ => "Bad Request",
    };
    write!(stream,"HTTP/1.1 {code} {reason}\r\nContent-Type: {kind}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Security-Policy: default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'\r\n\r\n",body.len()).map_err(|e|e.to_string())?;
    stream
        .write_all(body)
        .and_then(|_| stream.flush())
        .map_err(|e| e.to_string())
}
pub(crate) fn handle_with(
    stream: &mut TcpStream,
    port: u16,
    mut route: impl FnMut(&str, &str, &[u8]) -> Result<Option<serde_json::Value>>,
) -> Result<()> {
    let mut reader = BufReader::new(stream.try_clone().map_err(|e| e.to_string())?);
    let mut head = Vec::new();
    // Read byte-bounded headers; do not allocate an unbounded request line.
    loop {
        let mut b = [0];
        reader.read_exact(&mut b).map_err(|e| e.to_string())?;
        head.push(b[0]);
        if head.ends_with(b"\r\n\r\n") {
            break;
        }
        if head.len() > 8192 {
            return Err("HEADERS_TOO_LARGE".into());
        }
    }
    let text = std::str::from_utf8(&head).map_err(|_| "INVALID_HEADERS")?;
    let mut lines = text.split("\r\n");
    let request = lines.next().ok_or("NO_REQUEST")?;
    let parts: Vec<_> = request.split_whitespace().collect();
    if parts.len() != 3 || parts[2] != "HTTP/1.1" {
        return Err("HTTP_1_1_REQUIRED".into());
    }
    let mut headers = std::collections::BTreeMap::new();
    for line in lines.filter(|s| !s.is_empty()) {
        let (k, v) = line.split_once(':').ok_or("INVALID_HEADER")?;
        if headers.insert(k.to_ascii_lowercase(), v.trim()).is_some() {
            return Err("DUPLICATE_HEADER".into());
        }
    }
    let host = headers.get("host").ok_or("HOST_REQUIRED")?;
    if *host != format!("127.0.0.1:{port}") && *host != format!("localhost:{port}") {
        return Err("LOOPBACK_HOST_REQUIRED".into());
    }
    if headers.contains_key("transfer-encoding") {
        return Err("TRANSFER_ENCODING_UNSUPPORTED".into());
    }
    let length = headers
        .get("content-length")
        .map(|s| s.parse::<usize>())
        .transpose()
        .map_err(|_| "INVALID_LENGTH")?
        .unwrap_or(0);
    if length > 65536 {
        return Err("BODY_TOO_LARGE".into());
    }
    let mut body = vec![0; length];
    reader.read_exact(&mut body).map_err(|e| e.to_string())?;
    // Consume the bounded, supported request before replying. Closing with an
    // unread body can reset TCP and truncate the rejection itself. Authorization
    // still precedes every parse, compilation and store mutation below.
    if headers
        .get("origin")
        .map(|o| *o != format!("http://{host}"))
        .unwrap_or(false)
    {
        return Err("SAME_ORIGIN_REQUIRED".into());
    }
    if parts[0] == "POST" {
        let expected = if parts[1] == "/api/compile" {
            "text/plain"
        } else {
            "application/json"
        };
        if headers.get("content-type") != Some(&expected) {
            return Err("CONTENT_TYPE_REQUIRED".into());
        }
    }
    if parts[0] == "GET" && matches!(parts[1], "/" | "/AI") {
        return respond(
            stream,
            200,
            "text/html; charset=utf-8",
            include_bytes!("../../../ui/index.html"),
        );
    }
    match route(parts[0], parts[1], &body) {
        Ok(Some(value)) => respond(
            stream,
            200,
            "application/json",
            &serde_json::to_vec(&value).map_err(|e| e.to_string())?,
        ),
        Ok(None) => respond(
            stream,
            404,
            "application/json",
            b"{\"state\":\"NOT_FOUND\"}",
        ),
        Err(reason) => respond(
            stream,
            400,
            "application/json",
            &serde_json::to_vec(&json!({"state":"HOLD","reason":reason,"done":false}))
                .map_err(|e| e.to_string())?,
        ),
    }
}
pub(crate) fn dispatch(
    store: &mut Store,
    method: &str,
    path: &str,
    body: &[u8],
) -> Result<Option<serde_json::Value>> {
    Ok(Some(match (method, path) {
        ("GET", "/api/directory") => store.discover(now()),
        ("GET", "/api/events") => store.history(0),
        ("GET", "/api/checkpoint") => {
            serde_json::to_value(store.checkpoint()).map_err(|e| e.to_string())?
        }
        ("POST", "/api/compile") => serde_json::to_value(compiler::compile(
            std::str::from_utf8(body).map_err(|_| "UTF8_REQUIRED")?,
        )?)
        .map_err(|e| e.to_string())?,
        ("POST", "/api/execute") => {
            store.append(serde_json::from_slice::<Command>(body).map_err(|e| e.to_string())?)?
        }
        _ => return Ok(None),
    }))
}
