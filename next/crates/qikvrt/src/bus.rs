// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
//! Full duplex IP/TCP carrier for the C90 bus. Keys authenticate participants;
//! EAP participation is CONTINUE, separate from any application effect approval.
use crate::{
    mesh, sha256,
    store::{Command, Operation, Store, Subject},
    Result,
};
use hmac::{Hmac, Mac};
use qikvrt_metatransistor::{
    bus::{admission, Bus},
    exchange::{self, Binding, Receiver},
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::Sha256;
use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    fs::{self, File, OpenOptions},
    io::{BufRead, Read, Write},
    net::{Shutdown, SocketAddr, TcpListener, TcpStream},
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::Path,
    sync::mpsc::{self, SyncSender},
    thread,
    time::Duration,
};
type Tag = Hmac<Sha256>;
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PeerKey {
    id: String,
    key: String,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    schema: String,
    identity: String,
    subject: Subject,
    peers: Vec<PeerKey>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Credential {
    schema: String,
    bus: String,
    subject: Subject,
    id: String,
    key: String,
}
fn id(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 64
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_".contains(&b))
}
fn io<T>(v: std::io::Result<T>) -> Result<T> {
    v.map_err(|e| e.to_string())
}
fn bytes(v: &impl Serialize) -> Result<Vec<u8>> {
    serde_json::to_vec(v).map_err(|e| e.to_string())
}
fn hex(data: &[u8]) -> String {
    data.iter().map(|b| format!("{b:02x}")).collect()
}
fn unhex(s: &str) -> Result<Vec<u8>> {
    if s.len() % 2 != 0
        || s.len() > 2 * exchange::MAX_MESSAGE
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("BOUNDED_HEX_REQUIRED".into());
    }
    s.as_bytes()
        .chunks_exact(2)
        .map(|p| u8::from_str_radix(std::str::from_utf8(p).unwrap(), 16).map_err(|e| e.to_string()))
        .collect()
}
fn random() -> Result<[u8; 32]> {
    let mut d = [0; 32];
    io(File::open("/dev/urandom"))?
        .read_exact(&mut d)
        .map_err(|e| e.to_string())?;
    Ok(d)
}
fn sign(key: &[u8; 32], parts: &[&[u8]]) -> [u8; 32] {
    let mut h = Tag::new_from_slice(key).expect("fixed HMAC key");
    for p in parts {
        h.update(p);
    }
    h.finalize().into_bytes().into()
}
fn verify(key: &[u8; 32], parts: &[&[u8]], tag: &[u8]) -> Result<()> {
    let mut h = Tag::new_from_slice(key).expect("fixed HMAC key");
    for p in parts {
        h.update(p);
    }
    h.verify_slice(tag)
        .map_err(|_| "AUTHENTICATION_FAILED".into())
}
fn private_json<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    let m = io(fs::symlink_metadata(path))?;
    if !m.is_file()
        || m.file_type().is_symlink()
        || m.permissions().mode() & 0o077 != 0
        || m.len() > 16384
    {
        return Err("PRIVATE_CONFIG_REQUIRED".into());
    }
    serde_json::from_slice(&io(fs::read(path))?).map_err(|e| e.to_string())
}
fn write_private(path: &Path, value: &impl Serialize) -> Result<()> {
    let mut f = io(OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path))?;
    io(f.write_all(&bytes(value)?))?;
    io(f.sync_all())
}
pub fn create_config(
    directory: &Path,
    identity: &str,
    subject: Subject,
    peers: &[String],
) -> Result<()> {
    subject.validate()?;
    if !id(identity)
        || peers.is_empty()
        || peers.len() > 16
        || peers.iter().any(|p| !id(p) || p == identity)
        || peers.iter().collect::<BTreeSet<_>>().len() != peers.len()
    {
        return Err("BUS_CONFIG_IDENTITIES".into());
    }
    io(fs::create_dir(directory))?;
    io(fs::set_permissions(
        directory,
        fs::Permissions::from_mode(0o700),
    ))?;
    let mut config = Config {
        schema: "qikvrt-bus-config-v1".into(),
        identity: identity.into(),
        subject: subject.clone(),
        peers: Vec::new(),
    };
    for peer in peers {
        let key = hex(&random()?);
        config.peers.push(PeerKey {
            id: peer.clone(),
            key: key.clone(),
        });
        write_private(
            &directory.join(format!("{peer}.json")),
            &Credential {
                schema: "qikvrt-bus-peer-v1".into(),
                bus: identity.into(),
                subject: subject.clone(),
                id: peer.clone(),
                key,
            },
        )?;
    }
    write_private(&directory.join("bus.json"), &config)?;
    io(File::open(directory))?
        .sync_all()
        .map_err(|e| e.to_string())
}
fn read_json(stream: &mut TcpStream) -> Result<Value> {
    let mut data = Vec::new();
    let mut b = [0u8];
    for _ in 0..4096 {
        io(stream.read_exact(&mut b))?;
        if b[0] == b'\n' {
            return serde_json::from_slice(&data).map_err(|e| e.to_string());
        }
        data.push(b[0]);
    }
    Err("HANDSHAKE_BOUND".into())
}
fn write_json(out: &mut impl Write, v: &Value) -> Result<()> {
    io(out.write_all(&bytes(v)?))?;
    io(out.write_all(b"\n"))?;
    io(out.flush())
}
fn output(v: Value) {
    let _ = write_json(&mut std::io::stdout().lock(), &v);
}
fn socket(addr: &str) -> Result<SocketAddr> {
    addr.parse()
        .map_err(|_| "IP_SOCKET_ADDRESS_REQUIRED".into())
}
struct Writer {
    stream: TcpStream,
    key: [u8; 32],
    nonce: [u8; 32],
    sequence: u64,
    label: &'static [u8],
}
impl Writer {
    fn send(&mut self, frame: &[u8]) -> Result<()> {
        if frame.len() < 88 || frame.len() > exchange::MAX_FRAME {
            return Err("FRAME_BOUND".into());
        }
        let seq = self.sequence.to_be_bytes();
        let len = (frame.len() as u32).to_be_bytes();
        let mac = sign(&self.key, &[self.label, &self.nonce, &seq, &len, frame]);
        io(self.stream.write_all(&seq))?;
        io(self.stream.write_all(&len))?;
        io(self.stream.write_all(frame))?;
        io(self.stream.write_all(&mac))?;
        self.sequence = self
            .sequence
            .checked_add(1)
            .ok_or("SESSION_SEQUENCE_EXHAUSTED")?;
        Ok(())
    }
}
enum Event {
    Frame(usize, u64, Vec<u8>),
    Offline(usize, u64),
    Input(Value),
    Stop,
}
fn reader(
    mut stream: TcpStream,
    key: [u8; 32],
    nonce: [u8; 32],
    label: &'static [u8],
    slot: usize,
    generation: u64,
    send: SyncSender<Event>,
) {
    thread::spawn(move || {
        let result = (|| -> Result<()> {
            let mut expected = 0u64;
            loop {
                let mut header = [0u8; 12];
                io(stream.read_exact(&mut header))?;
                let seq = u64::from_be_bytes(header[..8].try_into().unwrap());
                let n = u32::from_be_bytes(header[8..].try_into().unwrap()) as usize;
                if seq != expected || n < 88 || n > exchange::MAX_FRAME {
                    return Err("CHANNEL_SEQUENCE_OR_BOUND".into());
                }
                let mut frame = vec![0; n];
                let mut tag = [0u8; 32];
                io(stream.read_exact(&mut frame))?;
                io(stream.read_exact(&mut tag))?;
                verify(
                    &key,
                    &[label, &nonce, &header[..8], &header[8..], &frame],
                    &tag,
                )?;
                expected = expected
                    .checked_add(1)
                    .ok_or("SESSION_SEQUENCE_EXHAUSTED")?;
                send.send(Event::Frame(slot, generation, frame))
                    .map_err(|_| "BUS_OWNER_STOPPED")?;
            }
        })();
        let _ = result;
        let _ = stream.shutdown(Shutdown::Both);
        let _ = send.send(Event::Offline(slot, generation));
    });
}
fn public(config: &Config) -> Value {
    json!({"schema":config.schema,"identity":config.identity,"subject":config.subject,
    "peers":config.peers.iter().map(|p|json!({"id":p.id,"key_fingerprint":sha256(p.key.as_bytes())})).collect::<Vec<_>>()})
}
fn register(store: &mut Store, subject: &Subject, value: Value) -> Result<String> {
    let artifact = store.put(&bytes(&value)?)?;
    let node = format!("bus:{}", store.identity());
    store.append(Command {
        event_id: format!("bus-config:{artifact}"),
        node_id: node.clone(),
        subject: subject.clone(),
        cause_event_ids: vec![],
        operation: Operation::Register {
            artifact,
            entrypoint: "next/AI".into(),
        },
    })?;
    Ok(node)
}

struct Delivery {
    from: String,
    to: String,
    binding: Binding,
    transfer: mesh::Transfer,
    kind: u8,
    d4: u8,
}
#[derive(Default)]
struct Assembly {
    pending: BTreeMap<String, Receiver>,
    seen: BTreeSet<String>,
    rejected: BTreeSet<String>,
}
impl Assembly {
    fn feed(
        &mut self,
        raw: &[u8],
        self_id: &str,
        names: &BTreeMap<[u8; 32], String>,
    ) -> Result<Option<Delivery>> {
        let digest = sha256(raw);
        if self.seen.contains(&digest) {
            return Ok(None);
        }
        let (m, p) = exchange::unpack(raw).map_err(str::to_owned)?;
        if p.len() < 172 || &p[..4] != b"QXT2" {
            return Err("BUS_ROUTE_PROFILE".into());
        }
        let source: [u8; 32] = p[8..40].try_into().unwrap();
        let destination: [u8; 32] = p[40..72].try_into().unwrap();
        let from = names.get(&source).ok_or("UNKNOWN_BUS_SOURCE")?.clone();
        if destination != mesh::digest(&sha256(self_id.as_bytes()))? {
            return Err("BUS_DESTINATION_MISMATCH".into());
        }
        let b = Binding {
            source,
            destination,
            subject: p[72..104].try_into().unwrap(),
            source_layer: p[4],
            destination_layer: p[5],
        };
        let key = format!(
            "{}:{}:{}:{}:{}",
            hex(&source),
            hex(&m[12..20]),
            hex(&m[32..36]),
            hex(&b.subject),
            m[5]
        );
        if self.rejected.contains(&key) {
            return Err("REJECTED_TRANSFER_ID".into());
        }
        if !self.pending.contains_key(&key) {
            if self.pending.len() >= 32 {
                return Err("RECEIVER_BACKPRESSURE".into());
            }
            self.pending
                .insert(key.clone(), Receiver::new(&b).map_err(str::to_owned)?);
        }
        let result = self.pending.get_mut(&key).unwrap().feed(raw);
        match result {
            Err(reason) => {
                self.pending.remove(&key);
                self.rejected.insert(key);
                Err(reason.into())
            }
            Ok(None) => {
                self.seen.insert(digest);
                Ok(None)
            }
            Ok(Some((codec, body, correlation))) => {
                self.pending.remove(&key);
                self.seen.insert(digest);
                Ok(Some(Delivery {
                    from,
                    to: self_id.into(),
                    binding: b,
                    kind: m[6],
                    d4: m[9],
                    transfer: mesh::Transfer {
                        codec,
                        body,
                        correlation,
                        session: u32::from_be_bytes(m[12..16].try_into().unwrap()),
                        nonce: u32::from_be_bytes(m[16..20].try_into().unwrap()),
                        message: u32::from_be_bytes(m[32..36].try_into().unwrap()),
                    },
                }))
            }
        }
    }
}
fn request_key(frame: &[u8]) -> Result<String> {
    let (m, p) = exchange::unpack(frame).map_err(str::to_owned)?;
    if p.len() < 172 {
        return Err("ROUTE_PROFILE".into());
    }
    let (source, destination) = if m[5] == 0 {
        (&p[8..40], &p[40..72])
    } else {
        (&p[40..72], &p[8..40])
    };
    Ok(format!(
        "{}:{}:{}:{}:{}:{}",
        hex(source),
        hex(destination),
        hex(&m[12..20]),
        hex(&m[32..36]),
        hex(&p[72..104]),
        hex(&p[140..172])
    ))
}
fn reply(
    store: &mut Store,
    subject: &Subject,
    node: &str,
    delivery: &Delivery,
) -> Result<Vec<Vec<u8>>> {
    let t = &delivery.transfer;
    let result = mesh::apply(store, t, &delivery.binding)
        .unwrap_or_else(|reason| json!({"state":"HOLD","reason":reason,"done":false}));
    let body = bytes(
        &json!({"result":result,"store":store.identity(),"checkpoint":store.checkpoint(),"effect_ack_done":false}),
    )?;
    let frames = exchange::frames_correlated(
        &delivery.binding.reverse(),
        3,
        &body,
        t.session,
        t.nonce,
        t.message,
        true,
        Some(&t.correlation),
    )
    .map_err(str::to_owned)?;
    for frame in &frames {
        record(store, subject, node, &delivery.to, &delivery.from, frame)?;
    }
    Ok(frames)
}
pub fn peer(root: &Path, credential_path: &Path, address: &str, worker: bool) -> Result<()> {
    let credential: Credential = private_json(credential_path)?;
    credential.subject.validate()?;
    if credential.schema != "qikvrt-bus-peer-v1" || !id(&credential.bus) || !id(&credential.id) {
        return Err("PEER_CREDENTIAL_SCHEMA".into());
    }
    let key = mesh::digest(&credential.key)?;
    let mut store = Store::open(root)?;
    if store.identity() != credential.id {
        return Err("PEER_STORE_IDENTITY".into());
    }
    let node = register(
        &mut store,
        &credential.subject,
        json!({"peer":credential.id,"bus":credential.bus,"subject":credential.subject,"key_fingerprint":sha256(credential.key.as_bytes())}),
    )?;
    let mut stream = io(TcpStream::connect_timeout(
        &socket(address)?,
        Duration::from_secs(3),
    ))?;
    io(stream.set_read_timeout(Some(Duration::from_secs(3))))?;
    io(stream.set_write_timeout(Some(Duration::from_secs(3))))?;
    let challenge = read_json(&mut stream)?;
    if challenge["protocol"] != "qikvrt-bus-auth-v1" || challenge["bus"] != credential.bus {
        return Err("BUS_CHALLENGE_IDENTITY".into());
    }
    let nonce = mesh::digest(challenge["challenge"].as_str().ok_or("BUS_CHALLENGE")?)?;
    let proof = sign(
        &key,
        &[
            format!("JOIN\n{}\n{}\n", credential.bus, credential.id).as_bytes(),
            &nonce,
        ],
    );
    write_json(
        &mut stream,
        &json!({"id":credential.id,"proof":hex(&proof)}),
    )?;
    let mut accepted = read_json(&mut stream)?;
    let proof = mesh::digest(accepted["proof"].as_str().ok_or("BUS_ACCEPT_PROOF")?)?;
    accepted
        .as_object_mut()
        .ok_or("BUS_ACCEPT_SHAPE")?
        .remove("proof");
    verify(&key, &[b"ACCEPT\n", &nonce, &bytes(&accepted)?], &proof)?;
    if accepted["id"] != credential.id
        || accepted["bus"] != credential.bus
        || accepted["wire_d4"] != 1
        || accepted["ordinary_release"] != false
    {
        return Err("EAP_JOIN_NOT_CONTINUE".into());
    }
    let mut names = BTreeMap::new();
    for name in accepted["peers"].as_array().ok_or("BUS_DIRECTORY")? {
        let name = name.as_str().ok_or("BUS_DIRECTORY_ID")?;
        if !id(name) {
            return Err("BUS_DIRECTORY_ID".into());
        }
        names.insert(mesh::digest(&sha256(name.as_bytes()))?, name.to_owned());
    }
    names.insert(
        mesh::digest(&sha256(credential.bus.as_bytes()))?,
        credential.bus.clone(),
    );
    let retained = history(&store)?;
    let mut assembly = Assembly::default();
    let mut completed = Vec::new();
    let mut replied = BTreeSet::new();
    for (from, to, _, raw) in &retained {
        if from == &credential.id && raw[5] == 1 {
            replied.insert(request_key(raw)?);
        }
        if to == &credential.id {
            match assembly.feed(raw, &credential.id, &names) {
                Ok(Some(d)) => completed.push(d),
                Ok(None) => {}
                Err(_) => {}
            }
        }
    }
    let mut outgoing: Vec<Vec<u8>> = retained
        .into_iter()
        .filter(|r| r.0 == credential.id)
        .map(|r| r.3)
        .collect();
    if worker {
        for delivery in completed {
            let t = &delivery.transfer;
            let key = format!(
                "{}:{}:{}{}:{}:{}:{}",
                hex(&delivery.binding.source),
                hex(&delivery.binding.destination),
                hex(&t.session.to_be_bytes()),
                hex(&t.nonce.to_be_bytes()),
                hex(&t.message.to_be_bytes()),
                hex(&delivery.binding.subject),
                hex(&t.correlation)
            );
            if delivery.kind == 1 && !replied.contains(&key) {
                outgoing.extend(reply(&mut store, &credential.subject, &node, &delivery)?);
            }
        }
    }
    io(stream.set_read_timeout(None))?;
    let (tx, rx) = mpsc::sync_channel(64);
    reader(
        io(stream.try_clone())?,
        key,
        nonce,
        b"B2P",
        0,
        0,
        tx.clone(),
    );
    let mut writer = Writer {
        stream,
        key,
        nonce,
        sequence: 0,
        label: b"P2B",
    };
    let mut outgoing: VecDeque<Vec<u8>> = outgoing.into();
    let input_tx = tx.clone();
    thread::spawn(move || {
        let stdin = std::io::stdin();
        let mut input = stdin.lock();
        loop {
            let mut line = Vec::new();
            let n = match input.by_ref().take(131074).read_until(b'\n', &mut line) {
                Ok(n) => n,
                Err(_) => break,
            };
            if n == 0 {
                break;
            }
            if n > 131072 || !line.ends_with(b"\n") {
                let _ = input_tx.send(Event::Stop);
                return;
            }
            match serde_json::from_slice(&line) {
                Ok(v) => {
                    if input_tx.send(Event::Input(v)).is_err() {
                        return;
                    }
                }
                Err(_) => output(json!({"state":"HOLD","reason":"COMMAND_JSON"})),
            }
        }
        let _ = input_tx.send(Event::Stop);
    });
    output(accepted);
    let mut serial = 0u32;
    let session = u32::from_be_bytes(nonce[..4].try_into().unwrap());
    loop {
        match rx.recv_timeout(Duration::from_millis(1)) {
            Ok(Event::Input(value)) => {
                let result = (|| -> Result<Value> {
                    let op = value["op"].as_str().ok_or("BUS_COMMAND")?;
                    let destination = value["destination"].as_str().ok_or("BUS_DESTINATION")?;
                    if !names.values().any(|n| n == destination) || destination == credential.id {
                        return Err("BUS_DESTINATION".into());
                    }
                    let subject = value["subject"].as_str().ok_or("BUS_SUBJECT")?;
                    let body = unhex(value["payload_hex"].as_str().ok_or("BUS_PAYLOAD_HEX")?)?;
                    let codec = value["codec"]
                        .as_u64()
                        .filter(|n| (1..=3).contains(n))
                        .ok_or("BUS_CODEC")? as u8;
                    let b = mesh::binding(&credential.id, destination, subject)?;
                    let frames = if op == "send" {
                        serial = serial.checked_add(1).ok_or("PEER_SEQUENCE_EXHAUSTED")?;
                        exchange::frames(&b, codec, &body, session, serial, serial, false)
                            .map_err(str::to_owned)?
                    } else if op == "reply" {
                        let correlation = mesh::digest(
                            value["correlation"].as_str().ok_or("REPLY_CORRELATION")?,
                        )?;
                        let number = |key: &str| {
                            value[key]
                                .as_u64()
                                .filter(|n| *n <= u32::MAX as u64)
                                .map(|n| n as u32)
                                .ok_or_else(|| "REPLY_REQUEST_ID".to_string())
                        };
                        let mut b = b;
                        b.source_layer = 4;
                        b.destination_layer = 1;
                        exchange::frames_correlated(
                            &b,
                            codec,
                            &body,
                            number("session")?,
                            number("nonce")?,
                            number("message_id")?,
                            true,
                            Some(&correlation),
                        )
                        .map_err(str::to_owned)?
                    } else {
                        return Err("BUS_COMMAND".into());
                    };
                    for frame in &frames {
                        record(
                            &mut store,
                            &credential.subject,
                            &node,
                            &credential.id,
                            destination,
                            frame,
                        )?;
                    }
                    outgoing.extend(frames.iter().cloned());
                    let (header, route) = exchange::unpack(&frames[0]).map_err(str::to_owned)?;
                    Ok(
                        json!({"state":"SENT","destination":destination,"correlation":hex(&route[140..172]),
                    "session":u32::from_be_bytes(header[12..16].try_into().unwrap()),"nonce":u32::from_be_bytes(header[16..20].try_into().unwrap()),
                    "message_id":u32::from_be_bytes(header[32..36].try_into().unwrap()),"frames":frames.len(),"ordinary_release":false}),
                    )
                })();
                output(result.unwrap_or_else(
                    |reason| json!({"state":"HOLD","reason":reason,"ordinary_release":false}),
                ));
            }
            Ok(Event::Frame(_, _, raw)) => {
                let (m, p) = exchange::unpack(&raw).map_err(str::to_owned)?;
                if p.len() < 172 {
                    return Err("BUS_ROUTE_PROFILE".into());
                }
                let source: [u8; 32] = p[8..40].try_into().unwrap();
                let from = names.get(&source).ok_or("UNKNOWN_BUS_SOURCE")?.clone();
                record(
                    &mut store,
                    &credential.subject,
                    &node,
                    &from,
                    &credential.id,
                    &raw,
                )?;
                match assembly.feed(&raw, &credential.id, &names) {
                    Ok(Some(delivery)) => {
                        let t = &delivery.transfer;
                        output(
                            json!({"state":"RECEIVED","source":delivery.from,"destination":delivery.to,"subject":hex(&delivery.binding.subject),
                        "kind":delivery.kind,"wire_d4":delivery.d4,"session":t.session,"nonce":t.nonce,"message_id":t.message,
                        "correlation":hex(&t.correlation),"codec":t.codec,"payload_hex":hex(&t.body),"ordinary_release":false}),
                        );
                        if worker && m[6] == 1 {
                            outgoing.extend(reply(
                                &mut store,
                                &credential.subject,
                                &node,
                                &delivery,
                            )?);
                        }
                    }
                    Ok(None) => {}
                    Err(reason) => {
                        output(json!({"state":"HOLD","reason":reason,"ordinary_release":false}))
                    }
                }
            }
            Ok(Event::Offline(_, _)) => return Err("BUS_DISCONNECTED_HISTORY_RETAINED".into()),
            Ok(Event::Stop) => {
                let _ = writer.stream.shutdown(Shutdown::Both);
                return Ok(());
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => return Err("PEER_CHANNEL_CLOSED".into()),
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        if let Some(frame) = outgoing.pop_front() {
            writer.send(&frame)?;
        }
    }
}
fn record(
    store: &mut Store,
    subject: &Subject,
    node: &str,
    source: &str,
    destination: &str,
    frame: &[u8],
) -> Result<String> {
    let digest = store.put(frame)?;
    store.append(Command {
        event_id: format!("bus-frame:{digest}"),
        node_id: node.into(),
        subject: subject.clone(),
        cause_event_ids: vec![],
        operation: Operation::RouteFrame {
            source: source.into(),
            destination: destination.into(),
            frame: digest.clone(),
        },
    })?;
    Ok(digest)
}
fn history(store: &Store) -> Result<Vec<(String, String, String, Vec<u8>)>> {
    let mut frames = Vec::new();
    let mut after = 0;
    loop {
        let page = store.history(after);
        let rows = page.as_array().ok_or("HISTORY_SHAPE")?;
        if rows.is_empty() {
            break;
        }
        for row in rows {
            after = row["record"]["sequence"]
                .as_u64()
                .ok_or("HISTORY_SEQUENCE")?;
            let c: Command = serde_json::from_value(row["record"]["command"].clone())
                .map_err(|e| e.to_string())?;
            if let Operation::RouteFrame {
                source,
                destination,
                frame,
            } = c.operation
            {
                frames.push((source, destination, frame.clone(), store.get(&frame)?));
            }
        }
    }
    Ok(frames)
}
fn nack(identity: &str, peer: &str, raw: &[u8], reason: &str) -> Result<Vec<Vec<u8>>> {
    let (m, p) = exchange::unpack(raw).map_err(str::to_owned)?;
    if p.len() < 172 {
        return Err("UNBOUND_NACK".into());
    }
    let binding = Binding {
        source: mesh::digest(&sha256(identity.as_bytes()))?,
        destination: mesh::digest(&sha256(peer.as_bytes()))?,
        subject: p[72..104].try_into().unwrap(),
        source_layer: 4,
        destination_layer: p[4],
    };
    let correlation = p[140..172].try_into().unwrap();
    let body = bytes(
        &json!({"state":"HOLD","effect_ack":"EFFECT_NACK","reason":reason,"ordinary_release":false}),
    )?;
    let frames = exchange::frames_correlated(
        &binding,
        3,
        &body,
        u32::from_be_bytes(m[12..16].try_into().unwrap()),
        u32::from_be_bytes(m[16..20].try_into().unwrap()),
        u32::from_be_bytes(m[32..36].try_into().unwrap()),
        true,
        Some(&correlation),
    )
    .map_err(str::to_owned)?;
    frames
        .iter()
        .map(|f| {
            let (mut m, p) = exchange::unpack(f).map_err(str::to_owned)?;
            m[8] = 1;
            m[9] = 0;
            exchange::pack(&m, &p).map_err(str::to_owned)
        })
        .collect()
}
fn route_retained(
    core: &mut Bus,
    indices: &BTreeMap<String, usize>,
    retained: &[(String, String, String, Vec<u8>)],
    source: usize,
    raw: &[u8],
) -> Result<usize> {
    let mut result = core.route(source, raw);
    if result.is_err() && raw.get(5) == Some(&1) {
        if let Ok(key) = request_key(raw) {
            for (from, _, _, old) in retained {
                if old[5] == 0 && request_key(old).ok().as_ref() == Some(&key) {
                    if let Some(&origin) = indices.get(from) {
                        let _ = core.route(origin, old);
                    }
                }
            }
            result = core.route(source, raw);
        }
    }
    result.map_err(str::to_owned)
}
pub fn serve(root: &Path, config_path: &Path, address: &str) -> Result<()> {
    let config: Config = private_json(config_path)?;
    config.subject.validate()?;
    if config.schema != "qikvrt-bus-config-v1"
        || !id(&config.identity)
        || config.peers.is_empty()
        || config.peers.len() > 16
    {
        return Err("BUS_CONFIG_SCHEMA".into());
    }
    let mut indices = BTreeMap::new();
    let mut core = Bus::new().map_err(str::to_owned)?;
    for (i, p) in config.peers.iter().enumerate() {
        if !id(&p.id) || indices.insert(p.id.clone(), i).is_some() {
            return Err("BUS_PEER_IDENTITY".into());
        }
        mesh::digest(&p.key)?;
        core.bind(i, &mesh::digest(&sha256(p.id.as_bytes()))?)
            .map_err(str::to_owned)?;
    }
    let mut store = Store::open(root)?;
    if store.identity() != config.identity {
        return Err("BUS_STORE_IDENTITY".into());
    }
    let node = register(&mut store, &config.subject, public(&config))?;
    let mut retained = history(&store)?;
    let mut known = BTreeMap::new();
    for (index, (from, to, digest, raw)) in retained.iter().enumerate() {
        if let (Some(&source), Some(&destination)) = (indices.get(from), indices.get(to)) {
            let target = route_retained(&mut core, &indices, &retained[..index], source, raw)
                .map_err(|e| format!("PRESERVED_ROUTING_REQUIRES_MIGRATION: {e}"))?;
            if target != destination {
                return Err("PRESERVED_ROUTE_MISMATCH".into());
            }
            known.insert(digest.clone(), (source, destination));
        }
    }
    let listener = io(TcpListener::bind(socket(address)?))?;
    io(listener.set_nonblocking(true))?;
    let (tx, rx) = mpsc::sync_channel(64);
    let mut writers: BTreeMap<usize, (u64, Writer, usize)> = BTreeMap::new();
    let mut generation = 0u64;
    output(
        json!({"state":"LISTENING","address":io(listener.local_addr())?.to_string(),"identity":config.identity,"protocol":"QVRT1/QXT2","mode":"full_duplex_bus","checkpoint":store.checkpoint()}),
    );
    loop {
        match listener.accept() {
            Ok((mut stream, _)) => {
                let joined = (|| -> Result<(usize, Writer, TcpStream)> {
                    io(stream.set_read_timeout(Some(Duration::from_secs(3))))?;
                    io(stream.set_write_timeout(Some(Duration::from_secs(3))))?;
                    let nonce = random()?;
                    write_json(
                        &mut stream,
                        &json!({"protocol":"qikvrt-bus-auth-v1","bus":config.identity,"challenge":hex(&nonce)}),
                    )?;
                    let hello = read_json(&mut stream)?;
                    let name = hello["id"].as_str().ok_or("JOIN_ID")?;
                    let &slot = indices.get(name).ok_or("UNREGISTERED_PARTICIPANT")?;
                    if writers.contains_key(&slot) {
                        return Err("PARTICIPANT_ALREADY_CONNECTED".into());
                    }
                    let key = mesh::digest(&config.peers[slot].key)?;
                    let proof = mesh::digest(hello["proof"].as_str().ok_or("JOIN_PROOF")?)?;
                    verify(
                        &key,
                        &[
                            format!("JOIN\n{}\n{name}\n", config.identity).as_bytes(),
                            &nonce,
                        ],
                        &proof,
                    )?;
                    let state = admission(true, true);
                    if state != 1 {
                        return Err("EAP_PARTICIPATION_REFUSED".into());
                    }
                    let mut accepted = json!({"state":"JOINED","effect_ack":"EFFECT_ACK_CONTINUE","wire_d4":state,"ordinary_release":false,
                        "id":name,"bus":config.identity,"peers":config.peers.iter().map(|p|p.id.clone()).collect::<Vec<_>>()});
                    let proof = sign(&key, &[b"ACCEPT\n", &nonce, &bytes(&accepted)?]);
                    accepted["proof"] = json!(hex(&proof));
                    write_json(&mut stream, &accepted)?;
                    io(stream.set_read_timeout(None))?;
                    let reading = io(stream.try_clone())?;
                    Ok((
                        slot,
                        Writer {
                            stream: io(stream.try_clone())?,
                            key,
                            nonce,
                            sequence: 0,
                            label: b"B2P",
                        },
                        reading,
                    ))
                })();
                match joined {
                    Ok((slot, writer, reading)) => {
                        generation = generation.checked_add(1).ok_or("GENERATION_EXHAUSTED")?;
                        reader(
                            reading,
                            writer.key,
                            writer.nonce,
                            b"P2B",
                            slot,
                            generation,
                            tx.clone(),
                        );
                        // Replay advances alongside incoming traffic: no full-duplex
                        // deadlock while both sides restore large retained outboxes.
                        writers.insert(slot, (generation, writer, 0));
                    }
                    Err(reason) => {
                        let _ = write_json(
                            &mut stream,
                            &json!({"state":"HOLD","reason":reason,"ordinary_release":false}),
                        );
                        let _ = stream.shutdown(Shutdown::Both);
                    }
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {}
            Err(e) => return Err(e.to_string()),
        }
        match rx.recv_timeout(Duration::from_millis(5)) {
            Ok(Event::Frame(source, g, raw)) if writers.get(&source).map(|p| p.0) == Some(g) => {
                let digest = sha256(&raw);
                let target = if let Some(&(old_source, target)) = known.get(&digest) {
                    if old_source != source {
                        continue;
                    }
                    if let Some(index) = retained.iter().position(|r| r.2 == digest) {
                        if let Some(writer) = writers.get_mut(&target) {
                            writer.2 = writer.2.min(index);
                        }
                    }
                    target
                } else {
                    let routed = route_retained(&mut core, &indices, &retained, source, &raw);
                    match routed {
                        Ok(target) => {
                            record(
                                &mut store,
                                &config.subject,
                                &node,
                                &config.peers[source].id,
                                &config.peers[target].id,
                                &raw,
                            )?;
                            output(
                                json!({"state":"QUEUED","source":config.peers[source].id,"destination":config.peers[target].id,"frame":digest,"checkpoint":store.checkpoint(),"ordinary_release":false}),
                            );
                            known.insert(digest.clone(), (source, target));
                            retained.push((
                                config.peers[source].id.clone(),
                                config.peers[target].id.clone(),
                                digest,
                                raw.clone(),
                            ));
                            target
                        }
                        Err(reason) => {
                            output(
                                json!({"state":"HOLD","peer":config.peers[source].id,"reason":reason}),
                            );
                            if let Ok(replies) =
                                nack(&config.identity, &config.peers[source].id, &raw, &reason)
                            {
                                for response in replies {
                                    let hash = record(
                                        &mut store,
                                        &config.subject,
                                        &node,
                                        &config.identity,
                                        &config.peers[source].id,
                                        &response,
                                    )?;
                                    if !retained.iter().any(|r| r.2 == hash) {
                                        retained.push((
                                            config.identity.clone(),
                                            config.peers[source].id.clone(),
                                            hash,
                                            response.clone(),
                                        ));
                                    }
                                }
                            } else if let Some((_, writer, _)) = writers.remove(&source) {
                                let _ = writer.stream.shutdown(Shutdown::Both);
                            }
                            continue;
                        }
                    }
                };
                let _ = target; // durable per-destination replay cursor dispatches below
            }
            Ok(Event::Offline(slot, g)) if writers.get(&slot).map(|p| p.0) == Some(g) => {
                writers.remove(&slot);
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => return Err("BUS_CHANNEL_CLOSED".into()),
            _ => {}
        }
        let mut offline = Vec::new();
        for (&slot, (_, writer, cursor)) in &mut writers {
            while *cursor < retained.len() && retained[*cursor].1 != config.peers[slot].id {
                *cursor += 1;
            }
            if let Some(item) = retained.get(*cursor) {
                if writer.send(&item.3).is_ok() {
                    *cursor += 1;
                } else {
                    let _ = writer.stream.shutdown(Shutdown::Both);
                    offline.push(slot);
                }
            }
        }
        for slot in offline {
            writers.remove(&slot);
        }
    }
}
