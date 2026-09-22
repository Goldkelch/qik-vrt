// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
//! Hosted stream adapter above C90: one transfer per connection, durable receipt.
//! Loopback is an OS transport boundary, not remote authentication or authority.
use crate::{
    sha256,
    store::{Command, Store, Subject},
    Result,
};
use qikvrt_metatransistor::exchange::{self, Binding, Receiver};
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    net::{Shutdown, SocketAddr, TcpListener, TcpStream},
    path::Path,
    time::Duration,
};

pub fn digest(s: &str) -> Result<[u8; 32]> {
    if s.len() != 64
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("SHA256_REQUIRED".into());
    }
    let mut d = [0; 32];
    for (i, p) in s.as_bytes().chunks_exact(2).enumerate() {
        d[i] = u8::from_str_radix(std::str::from_utf8(p).unwrap(), 16).unwrap();
    }
    Ok(d)
}
pub fn subject_digest(s: &Subject) -> String {
    sha256(
        format!(
            "{}\n{}\n{}\n{}\n",
            s.repository, s.subject_id, s.head, s.tree
        )
        .as_bytes(),
    )
}
pub fn binding(from: &str, to: &str, subject: &str) -> Result<Binding> {
    if from.is_empty() || to.is_empty() || from.len() > 200 || to.len() > 200 {
        return Err("ENDPOINT_ID_REQUIRED".into());
    }
    Ok(Binding {
        source: digest(&sha256(from.as_bytes()))?,
        destination: digest(&sha256(to.as_bytes()))?,
        subject: digest(subject)?,
        source_layer: 1,
        destination_layer: 4,
    })
}
pub fn packet(b: &Binding, codec: u8, body: &[u8]) -> Result<Vec<Vec<u8>>> {
    let message = u32::from_be_bytes(digest(&sha256(body))?[..4].try_into().unwrap());
    exchange::frames(b, codec, body, 8, 9, message, false).map_err(str::to_owned)
}
pub fn write_frames(out: &mut impl Write, frames: Vec<Vec<u8>>) -> Result<()> {
    for f in frames {
        out.write_all(&f).map_err(|e| e.to_string())?;
    }
    out.flush().map_err(|e| e.to_string())
}
pub struct Transfer {
    pub codec: u8,
    pub body: Vec<u8>,
    pub session: u32,
    pub nonce: u32,
    pub message: u32,
    pub correlation: [u8; 32],
}
pub fn receive(input: &mut impl Read, b: &Binding, receipt: bool) -> Result<Transfer> {
    let mut receiver = Receiver::new(b).map_err(str::to_owned)?;
    let mut completed = None;
    for _ in 0..64 {
        let mut header = [0u8; 84];
        match input.read(&mut header[..1]) {
            Ok(0) => return completed.ok_or_else(|| "INCOMPLETE_TRANSFER".into()),
            Ok(_) => {}
            Err(e) => return Err(e.to_string()),
        }
        input
            .read_exact(&mut header[1..])
            .map_err(|_| "TRUNCATED_HEADER")?;
        let n = u32::from_be_bytes(header[44..48].try_into().unwrap()) as usize;
        if n > 4096 {
            return Err("FRAME_BOUND".into());
        }
        if (header[5], header[6]) != if receipt { (1, 3) } else { (0, 1) }
            || header[9] != u8::from(receipt)
        {
            return Err("DIRECTION_TYPE_OR_EFFECT_BOUNDARY".into());
        }
        let mut frame = header.to_vec();
        frame.resize(88 + n, 0);
        input
            .read_exact(&mut frame[84..])
            .map_err(|_| "TRUNCATED_PAYLOAD")?;
        if let Some((codec, body, correlation)) = receiver.feed(&frame).map_err(str::to_owned)? {
            completed = Some(Transfer {
                codec,
                body,
                correlation,
                session: u32::from_be_bytes(header[12..16].try_into().unwrap()),
                nonce: u32::from_be_bytes(header[16..20].try_into().unwrap()),
                message: u32::from_be_bytes(header[32..36].try_into().unwrap()),
            });
        }
    }
    Err("TRANSFER_FRAME_COUNT_BOUND".into())
}
pub(crate) fn apply(store: &mut Store, t: &Transfer, b: &Binding) -> Result<Value> {
    match t.codec {
        1 => {
            let command: Command = serde_json::from_slice(&t.body).map_err(|e| e.to_string())?;
            if command.node_id.starts_with("bus:")
                || matches!(
                    command.operation,
                    crate::store::Operation::RouteFrame { .. }
                )
            {
                return Err("INTERNAL_TRANSPORT_NAMESPACE".into());
            }
            if digest(&subject_digest(&command.subject))? != b.subject {
                return Err("PAYLOAD_SUBJECT_MISMATCH".into());
            }
            store.append(command)
        }
        2 => {
            let hash = store.put(&t.body)?;
            Ok(
                json!({"state":"OBJECT_STORED","sha256":hash,"bytes":t.body.len(),"scope":"durable_object_readback","done":false}),
            )
        }
        _ => Err("REQUEST_CODEC_NOT_EXECUTABLE".into()),
    }
}
pub fn exchange(
    store: &mut Store,
    input: &mut impl Read,
    out: &mut impl Write,
    b: &Binding,
) -> Result<()> {
    if digest(&sha256(store.identity().as_bytes()))? != b.destination {
        return Err("STORE_ENDPOINT_MISMATCH".into());
    }
    let t = receive(input, b, false)?;
    let result = apply(store, &t, b)
        .unwrap_or_else(|reason| json!({"state":"HOLD","reason":reason,"done":false}));
    let body = serde_json::to_vec(
        &json!({"result":result,"store":store.identity(),"checkpoint":store.checkpoint(),
        "scope":"local_durable_bytes_and_recorded_result","effect_ack_done":false}),
    )
    .map_err(|e| e.to_string())?;
    write_frames(
        out,
        exchange::frames_correlated(
            &b.reverse(),
            3,
            &body,
            t.session,
            t.nonce,
            t.message,
            true,
            Some(&t.correlation),
        )
        .map_err(str::to_owned)?,
    )
}
fn address(value: &str) -> Result<SocketAddr> {
    let addr: SocketAddr = value.parse().map_err(|_| "SOCKET_ADDRESS_REQUIRED")?;
    if !addr.ip().is_loopback() {
        return Err("AUTHENTICATED_REMOTE_ADAPTER_REQUIRED".into());
    }
    Ok(addr)
}
pub fn serve(root: &Path, peer: &str, subject: &str, addr: &str) -> Result<()> {
    let mut store = Store::open(root)?;
    let b = binding(peer, store.identity(), subject)?;
    let listener = TcpListener::bind(address(addr)?).map_err(|e| e.to_string())?;
    println!(
        "{}",
        json!({"state":"LISTENING","address":listener.local_addr().map_err(|e|e.to_string())?.to_string(),"store":store.identity(),"protocol":"QVRT1/QXT2"})
    );
    std::io::stdout().flush().map_err(|e| e.to_string())?;
    for connection in listener.incoming() {
        let mut connection = match connection {
            Ok(c) => c,
            Err(e) => {
                eprintln!("accept: {e}");
                continue;
            }
        };
        connection
            .set_read_timeout(Some(Duration::from_secs(3)))
            .map_err(|e| e.to_string())?;
        connection
            .set_write_timeout(Some(Duration::from_secs(3)))
            .map_err(|e| e.to_string())?;
        let mut reader = connection.try_clone().map_err(|e| e.to_string())?;
        if let Err(reason) = exchange(&mut store, &mut reader, &mut connection, &b) {
            eprintln!("{}", json!({"state":"HOLD","reason":reason}));
        }
        let _ = connection.shutdown(Shutdown::Both);
    }
    Ok(())
}
pub fn send(b: &Binding, codec: u8, body: &[u8], addr: &str) -> Result<Value> {
    let frames = packet(b, codec, body)?;
    let expected_message = u32::from_be_bytes(frames[0][32..36].try_into().unwrap());
    let mut connection = TcpStream::connect_timeout(&address(addr)?, Duration::from_secs(3))
        .map_err(|e| e.to_string())?;
    connection
        .set_read_timeout(Some(Duration::from_secs(5)))
        .map_err(|e| e.to_string())?;
    connection
        .set_write_timeout(Some(Duration::from_secs(5)))
        .map_err(|e| e.to_string())?;
    write_frames(&mut connection, frames)?;
    connection
        .shutdown(Shutdown::Write)
        .map_err(|e| e.to_string())?;
    let reply = receive(&mut connection, &b.reverse(), true)?;
    if reply.codec != 3
        || reply.correlation != digest(&sha256(body))?
        || (reply.session, reply.nonce, reply.message) != (8, 9, expected_message)
    {
        return Err("RECEIPT_REQUEST_BINDING".into());
    }
    serde_json::from_slice(&reply.body).map_err(|e| e.to_string())
}
