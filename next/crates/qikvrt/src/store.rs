// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
//! Durable node identity and content-addressed history. Reachability is a
//! projection; it never deletes a registered node or its previous subjects.
use crate::{compiler, sha256, Result};
use fs2::FileExt;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

const ZERO: &str = "0000000000000000000000000000000000000000000000000000000000000000";
const MAX_OBJECT: u64 = 16 * 1024 * 1024;
const MAX_RECORD: u64 = 1024 * 1024;
fn io<T>(v: std::io::Result<T>) -> Result<T> {
    v.map_err(|e| e.to_string())
}
pub fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
fn hex(s: &str, n: usize) -> bool {
    s.len() == n
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn identifier(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 200
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_:.".contains(&b))
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Subject {
    pub repository: String,
    pub subject_id: String,
    pub head: String,
    pub tree: String,
}
impl Subject {
    pub fn validate(&self) -> Result<()> {
        let r: Vec<_> = self.repository.split('/').collect();
        if r.len() != 2
            || r.iter().any(|p| {
                p.is_empty()
                    || !p
                        .bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
            })
            || !identifier(&self.subject_id)
            || !hex(&self.head, 40)
            || !hex(&self.tree, 40)
        {
            return Err("EXACT_SUBJECT_REQUIRED".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct NativeInput {
    pub a: u32,
    pub b: u32,
    pub lut: u8,
    pub requested: u8,
    pub binding: u8,
    pub authority: u8,
    pub distinction: u8,
    pub drift: u8,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Operation {
    Register {
        artifact: String,
        entrypoint: String,
    },
    Reachability {
        reachable: bool,
        ttl_seconds: u32,
    },
    Evaluate {
        a: u32,
        b: u32,
        lut: u8,
        requested: u8,
        binding: u8,
        authority: u8,
        distinction: u8,
        drift: u8,
    },
    Program {
        source: String,
        event: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        input: Option<NativeInput>,
    },
    PreserveStore {
        snapshot: String,
    },
    RouteFrame {
        source: String,
        destination: String,
        frame: String,
    },
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Command {
    pub event_id: String,
    pub node_id: String,
    pub subject: Subject,
    pub cause_event_ids: Vec<String>,
    pub operation: Operation,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub schema: String,
    pub sequence: u64,
    pub previous: String,
    pub recorded_at: u64,
    pub implementation_sha256: String,
    pub store_identity: String,
    pub command: Command,
    pub result: Value,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Anchor {
    pub sequence: u64,
    pub digest: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Meta {
    schema: String,
    identity: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct SnapshotFile {
    path: String,
    sha256: String,
    bytes: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Snapshot {
    schema: String,
    identity: String,
    checkpoint: Anchor,
    files: Vec<SnapshotFile>,
}

fn safe_dir(p: &Path) -> Result<()> {
    let m = io(fs::symlink_metadata(p))?;
    if !m.is_dir() || m.file_type().is_symlink() {
        return Err("REAL_DIRECTORY_REQUIRED".into());
    }
    Ok(())
}
fn bounded_read(p: &Path, max: u64) -> Result<Vec<u8>> {
    let m = io(fs::symlink_metadata(p))?;
    if !m.is_file() || m.file_type().is_symlink() || m.len() > max {
        return Err("UNSAFE_OR_OVERSIZED_FILE".into());
    }
    let mut b = Vec::new();
    io(io(File::open(p))?.take(max + 1).read_to_end(&mut b))?;
    if b.len() as u64 > max {
        return Err("FILE_GREW_BEYOND_BOUND".into());
    }
    Ok(b)
}
/// Same-filesystem create-only publication. The caller holds the process lock.
/// A crash leaves an ignored temporary file or a complete immutable final file.
fn publish(p: &Path, bytes: &[u8]) -> Result<()> {
    let parent = p.parent().ok_or("NO_PARENT")?;
    safe_dir(parent)?;
    if p.try_exists().map_err(|e| e.to_string())? {
        if bounded_read(p, MAX_OBJECT)? == bytes {
            return Ok(());
        }
        return Err("IMMUTABLE_FILE_CONFLICT".into());
    }
    let mut n = 0u64;
    let (tmp, mut f) = loop {
        let t = parent.join(format!(".pending-{}-{n}", std::process::id()));
        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&t)
        {
            Ok(f) => break (t, f),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => n += 1,
            Err(e) => return Err(e.to_string()),
        }
        if n > 10000 {
            return Err("TOO_MANY_PENDING_WRITES".into());
        }
    };
    io(f.write_all(bytes))?;
    io(f.sync_all())?;
    drop(f);
    io(fs::hard_link(&tmp, p))?;
    io(File::open(parent))?
        .sync_all()
        .map_err(|e| e.to_string())?;
    io(fs::remove_file(tmp))?;
    if bounded_read(p, MAX_OBJECT)? != bytes {
        return Err("DURABLE_READBACK_MISMATCH".into());
    }
    Ok(())
}
fn json_bytes<T: Serialize>(v: &T) -> Result<Vec<u8>> {
    serde_json::to_vec(v).map_err(|e| e.to_string())
}
fn indexed_files(path: &Path) -> Result<BTreeMap<u64, PathBuf>> {
    let mut result = BTreeMap::new();
    for item in io(fs::read_dir(path))? {
        let item = io(item)?;
        let name = item.file_name();
        let name = name.to_str().ok_or("NON_UTF8_RECORD_NAME")?;
        if name.starts_with(".pending-") {
            continue;
        }
        if name.len() != 25
            || !name.ends_with(".json")
            || !name.as_bytes()[..20]
                .iter()
                .copied()
                .all(|b| b.is_ascii_digit())
        {
            return Err("UNEXPECTED_LEDGER_FILE".into());
        }
        let n = name[..20].parse::<u64>().map_err(|_| "INVALID_SEQUENCE")?;
        if n == 0 {
            return Err("INVALID_SEQUENCE".into());
        }
        result.insert(n, item.path());
    }
    Ok(result)
}

pub struct Store {
    root: PathBuf,
    _lock: File,
    identity: String,
    implementation_sha256: String,
    records: Vec<(Record, String)>,
    ids: BTreeMap<String, usize>,
}
impl Store {
    pub fn identity(&self) -> &str {
        &self.identity
    }
    pub fn init(root: &Path, identity: &str) -> Result<()> {
        if !identifier(identity) {
            return Err("STORE_IDENTITY_REQUIRED".into());
        }
        // Never initialize an existing directory: especially not after state loss.
        io(fs::create_dir(root))?;
        io(fs::set_permissions(root, fs::Permissions::from_mode(0o700)))?;
        for d in ["objects", "events", "anchors"] {
            io(fs::create_dir(root.join(d)))?;
        }
        publish(
            &root.join("meta.json"),
            &json_bytes(&Meta {
                schema: "qikvrt-store-v1".into(),
                identity: identity.into(),
            })?,
        )?;
        if let Some(parent) = root.parent() {
            io(File::open(parent))?
                .sync_all()
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }
    pub fn open(root: &Path) -> Result<Self> {
        safe_dir(root)?;
        if io(fs::metadata(root))?.permissions().mode() & 0o077 != 0 {
            return Err("STORE_MUST_BE_OWNER_ONLY".into());
        }
        for d in ["objects", "events", "anchors"] {
            safe_dir(&root.join(d))?;
        }
        let lock_path = root.join("writer.lock");
        if fs::symlink_metadata(&lock_path)
            .map(|m| m.file_type().is_symlink())
            .unwrap_or(false)
        {
            return Err("UNSAFE_LOCK".into());
        }
        let lock = io(OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .mode(0o600)
            .open(lock_path))?;
        lock.try_lock_exclusive()
            .map_err(|_| "ACTIVE_WRITER".to_string())?;
        let meta: Meta = serde_json::from_slice(&bounded_read(&root.join("meta.json"), 4096)?)
            .map_err(|e| e.to_string())?;
        if meta.schema != "qikvrt-store-v1" || !identifier(&meta.identity) {
            return Err("UNKNOWN_STORE_SCHEMA".into());
        }
        let implementation_sha256 = sha256(&io(fs::read(io(std::env::current_exe())?))?);
        let mut s = Store {
            root: root.into(),
            _lock: lock,
            identity: meta.identity,
            implementation_sha256,
            records: Vec::new(),
            ids: BTreeMap::new(),
        };
        let files = indexed_files(&root.join("events"))?;
        let anchors = indexed_files(&root.join("anchors"))?;
        let started = root.join("history.started");
        if started.exists() && files.is_empty() {
            return Err("PREVIOUSLY_USED_STORE_IS_EMPTY".into());
        }
        if anchors.keys().any(|n| !files.contains_key(n)) {
            return Err("ACKNOWLEDGED_HISTORY_MISSING".into());
        }
        let last = files.len() as u64;
        for (n, p) in files {
            if n != s.records.len() as u64 + 1 {
                return Err("HISTORY_GAP".into());
            }
            let bytes = bounded_read(&p, MAX_RECORD)?;
            let digest = sha256(&bytes);
            let record: Record =
                serde_json::from_slice(&bytes).map_err(|e| format!("CORRUPT_RECORD: {e}"))?;
            if record.schema != "qikvrt-event-v1"
                || record.sequence != n
                || record.previous != s.checkpoint().digest
                || !hex(&record.implementation_sha256, 64)
                || record.store_identity != s.identity
            {
                return Err("HISTORY_BINDING_MISMATCH".into());
            }
            // Preserve historical outputs of their recorded implementation.
            // Reopening must not recompile/reexecute the past with a successor.
            s.validate_history(&record.command)?;
            if s.ids.contains_key(&record.command.event_id) {
                return Err("DUPLICATE_HISTORY_EVENT".into());
            }
            let anchor = Anchor {
                sequence: n,
                digest: digest.clone(),
            };
            if let Some(a) = anchors.get(&n) {
                let old: Anchor =
                    serde_json::from_slice(&bounded_read(a, 4096)?).map_err(|e| e.to_string())?;
                if old.sequence != n || old.digest != digest {
                    return Err("CHECKPOINT_MISMATCH".into());
                }
            } else if n != last {
                return Err("CHECKPOINT_GAP".into());
            }
            // Complete a commit interrupted before its acknowledgement. Never erase.
            publish(&s.anchor_path(n), &json_bytes(&anchor)?)?;
            if n == 1 {
                publish(&started, &json_bytes(&anchor)?)?;
            }
            s.ids
                .insert(record.command.event_id.clone(), s.records.len());
            s.records.push((record, digest));
        }
        Ok(s)
    }
    fn anchor_path(&self, n: u64) -> PathBuf {
        self.root.join("anchors").join(format!("{n:020}.json"))
    }
    pub fn checkpoint(&self) -> Anchor {
        Anchor {
            sequence: self.records.len() as u64,
            digest: self
                .records
                .last()
                .map(|r| r.1.clone())
                .unwrap_or_else(|| ZERO.into()),
        }
    }
    /// Preserve every committed byte, including original event outputs. The source
    /// writer lock is held for the whole snapshot; pending, unacknowledged files
    /// are excluded. Existing objects precede newly added snapshot bookkeeping.
    pub fn export_snapshot(&self) -> Result<String> {
        let mut paths = vec!["meta.json".to_string()];
        if !self.records.is_empty() {
            paths.push("history.started".into());
        }
        for n in 1..=self.records.len() {
            for dir in ["events", "anchors"] {
                paths.push(format!("{dir}/{n:020}.json"));
            }
        }
        for entry in io(fs::read_dir(self.root.join("objects")))? {
            let name = io(entry)?
                .file_name()
                .into_string()
                .map_err(|_| "OBJECT_FILENAME")?;
            if name.starts_with(".pending-") {
                continue;
            }
            if !hex(&name, 64) {
                return Err("OBJECT_FILENAME".into());
            }
            paths.push(format!("objects/{name}"));
        }
        paths.sort();
        let mut files = Vec::new();
        for path in paths {
            let bytes = bounded_read(&self.root.join(&path), MAX_OBJECT)?;
            let digest = self.put(&bytes)?;
            if path.starts_with("objects/") && path[8..] != digest {
                return Err("OBJECT_DIGEST_MISMATCH".into());
            }
            files.push(SnapshotFile {
                path,
                sha256: digest,
                bytes: bytes.len() as u64,
            });
        }
        self.put(&json_bytes(&Snapshot {
            schema: "qikvrt-store-snapshot-v1".into(),
            identity: self.identity.clone(),
            checkpoint: self.checkpoint(),
            files,
        })?)
    }
    fn snapshot(&self, digest: &str) -> Result<Snapshot> {
        let s: Snapshot = serde_json::from_slice(&self.get(digest)?).map_err(|e| e.to_string())?;
        if s.schema != "qikvrt-store-snapshot-v1"
            || !identifier(&s.identity)
            || !hex(&s.checkpoint.digest, 64)
            || s.files.len() > 100000
        {
            return Err("SNAPSHOT_SCHEMA_OR_BOUND".into());
        }
        let mut paths = std::collections::BTreeSet::new();
        for entry in &s.files {
            let path = &entry.path;
            let allowed = path == "meta.json"
                || path == "history.started"
                || path
                    .strip_prefix("objects/")
                    .map(|p| hex(p, 64))
                    .unwrap_or(false)
                || ["events/", "anchors/"].iter().any(|prefix| {
                    path.strip_prefix(prefix)
                        .map(|p| {
                            p.len() == 25
                                && p.ends_with(".json")
                                && p.as_bytes()[..20]
                                    .iter()
                                    .copied()
                                    .all(|b| b.is_ascii_digit())
                        })
                        .unwrap_or(false)
                });
            if !allowed || !paths.insert(path) {
                return Err("SNAPSHOT_PATH".into());
            }
            let bytes = self.get(&entry.sha256)?;
            if bytes.len() as u64 != entry.bytes
                || path.starts_with("objects/") && path[8..] != entry.sha256
            {
                return Err("SNAPSHOT_BYTE_BINDING".into());
            }
        }
        if !paths.contains(&"meta.json".to_string()) {
            return Err("SNAPSHOT_METADATA_MISSING".into());
        }
        Ok(s)
    }
    pub fn restore_snapshot(&self, digest: &str, destination: &Path) -> Result<Anchor> {
        let snapshot = self.snapshot(digest)?;
        io(fs::create_dir(destination))?;
        io(fs::set_permissions(
            destination,
            fs::Permissions::from_mode(0o700),
        ))?;
        for dir in ["objects", "events", "anchors"] {
            io(fs::create_dir(destination.join(dir)))?;
        }
        for entry in &snapshot.files {
            publish(&destination.join(&entry.path), &self.get(&entry.sha256)?)?;
        }
        let restored = Self::open(destination)?;
        if restored.identity != snapshot.identity {
            return Err("SNAPSHOT_IDENTITY_MISMATCH".into());
        }
        restored.check_anchor(&snapshot.checkpoint)?;
        if restored.checkpoint().sequence != snapshot.checkpoint.sequence {
            return Err("SNAPSHOT_TAIL_MISMATCH".into());
        }
        if let Some(parent) = destination.parent() {
            io(File::open(parent))?
                .sync_all()
                .map_err(|e| e.to_string())?;
        }
        Ok(restored.checkpoint())
    }
    pub fn check_anchor(&self, a: &Anchor) -> Result<()> {
        let expected = if a.sequence == 0 {
            Some(ZERO)
        } else {
            self.records
                .get((a.sequence - 1) as usize)
                .map(|r| r.1.as_str())
        };
        if expected != Some(a.digest.as_str()) {
            return Err("EXTERNAL_CHECKPOINT_MISMATCH".into());
        }
        Ok(())
    }
    pub fn put(&self, bytes: &[u8]) -> Result<String> {
        if bytes.len() as u64 > MAX_OBJECT {
            return Err("OBJECT_TOO_LARGE".into());
        }
        let digest = sha256(bytes);
        publish(&self.root.join("objects").join(&digest), bytes)?;
        Ok(digest)
    }
    pub fn get(&self, digest: &str) -> Result<Vec<u8>> {
        if !hex(digest, 64) {
            return Err("SHA256_REQUIRED".into());
        }
        let bytes = bounded_read(&self.root.join("objects").join(digest), MAX_OBJECT)?;
        if sha256(&bytes) != digest {
            return Err("OBJECT_DIGEST_MISMATCH".into());
        }
        Ok(bytes)
    }
    fn current(&self, node: &str) -> Option<&Record> {
        self.records.iter().rev().map(|x| &x.0).find(|r| {
            r.command.node_id == node && matches!(r.command.operation, Operation::Register { .. })
        })
    }
    fn validate_history(&self, c: &Command) -> Result<()> {
        c.subject.validate()?;
        if !identifier(&c.event_id) || !identifier(&c.node_id) || c.cause_event_ids.len() > 16 {
            return Err("INVALID_EVENT_ID_OR_CAUSES".into());
        }
        let mut causes = std::collections::BTreeSet::new();
        for cause in &c.cause_event_ids {
            if !causes.insert(cause) || !self.ids.contains_key(cause) {
                return Err("CAUSE_NOT_BOUND_TO_EXISTING_EVENT".into());
            }
        }
        if !matches!(c.operation, Operation::Register { .. }) {
            let current = self.current(&c.node_id).ok_or("NODE_NOT_REGISTERED")?;
            if current.command.subject != c.subject {
                return Err("EXACT_SUBJECT_MISMATCH".into());
            }
        }
        match &c.operation {
            Operation::Register { artifact, .. } => {
                self.get(artifact)?;
            }
            Operation::Program { source, .. } => {
                self.get(source)?;
            }
            Operation::PreserveStore { snapshot } => {
                self.snapshot(snapshot)?;
            }
            Operation::RouteFrame { frame, .. } => {
                self.get(frame)?;
            }
            _ => {}
        }
        Ok(())
    }
    fn validate(&self, c: &Command) -> Result<Value> {
        self.validate_history(c)?;
        match &c.operation {
            Operation::RouteFrame {
                source,
                destination,
                frame,
            } => {
                if !identifier(source) || !identifier(destination) {
                    return Err("BUS_ENDPOINT_ID".into());
                }
                let raw = self.get(frame)?;
                let (_, payload) =
                    qikvrt_metatransistor::exchange::unpack(&raw).map_err(str::to_owned)?;
                if payload.len() < 172
                    || &payload[..4] != b"QXT2"
                    || payload[8..40] != crate::mesh::digest(&sha256(source.as_bytes()))?
                    || payload[40..72] != crate::mesh::digest(&sha256(destination.as_bytes()))?
                {
                    return Err("BUS_FRAME_ENDPOINT_BINDING".into());
                }
                Ok(
                    json!({"state":"FRAME_QUEUED","frame":frame,"scope":"durable_bus_bytes","effect_ack_done":false}),
                )
            }
            Operation::PreserveStore { snapshot } => {
                let snap = self.snapshot(snapshot)?;
                Ok(
                    json!({"state":"SNAPSHOT_RETAINED","snapshot":snapshot,"source_identity":snap.identity,
                    "source_checkpoint":snap.checkpoint,"source_results_reexecuted":false,"authority_transferred":false}),
                )
            }
            Operation::Register {
                artifact,
                entrypoint,
            } => {
                self.get(artifact)?;
                if entrypoint.is_empty()
                    || entrypoint.len() > 256
                    || Path::new(entrypoint).is_absolute()
                    || entrypoint
                        .split('/')
                        .any(|p| p.is_empty() || p == "." || p == "..")
                {
                    return Err("RELATIVE_ENTRYPOINT_REQUIRED".into());
                }
                Ok(json!({"state":"REGISTERED","artifact":artifact,"evidence_transfer":false}))
            }
            Operation::Reachability {
                reachable,
                ttl_seconds,
            } => {
                if *ttl_seconds == 0 || *ttl_seconds > 86400 {
                    return Err("TTL_OUT_OF_RANGE".into());
                }
                Ok(
                    json!({"state":if *reachable {"OBSERVED_REACHABLE"} else {"OFFLINE"},"identity_retained":true}),
                )
            }
            Operation::Evaluate {
                a,
                b,
                lut,
                requested,
                binding,
                authority,
                distinction,
                drift,
            } => {
                let r = qikvrt_metatransistor::evaluate(qikvrt_metatransistor::Input {
                    a: *a,
                    b: *b,
                    lut: *lut,
                    requested: *requested,
                    binding: *binding,
                    authority: *authority,
                    distinction: *distinction,
                    drift: *drift,
                });
                Ok(
                    json!({"state":r.state,"value":r.value,"value_valid":r.value_valid==1,
                    "scope":"boolean_model_operation","external_effect":false,"done":false}),
                )
            }
            Operation::Program {
                source,
                event,
                input,
            } => {
                let bytes = self.get(source)?;
                let text = std::str::from_utf8(&bytes).map_err(|_| "UTF8_SOURCE_REQUIRED")?;
                let program = compiler::compile(text)?;
                if program.subject.repository != c.subject.repository
                    || program.subject.name != c.subject.subject_id
                {
                    return Err("PROGRAM_SUBJECT_MISMATCH".into());
                }
                let handler = program
                    .handlers
                    .iter()
                    .find(|h| &h.event == event)
                    .ok_or("HANDLER_NOT_DECLARED")?;
                let effects: Vec<_> = handler
                    .statements
                    .iter()
                    .filter(|s| s.starts_with("effect "))
                    .collect();
                let native_effect = if effects.is_empty() {
                    if input.is_some() {
                        return Err("NATIVE_INPUT_WITHOUT_EFFECT_BINDING".into());
                    }
                    Value::Null
                } else {
                    if effects.len()!=1 || effects[0]!="effect boolean_lut { require authority; require validation; commit; readback; }" {
                        return Err("NATIVE_EFFECT_NOT_BOUND".into());
                    }
                    let i = input.as_ref().ok_or("NATIVE_INPUT_REQUIRED")?;
                    let r = qikvrt_metatransistor::evaluate(qikvrt_metatransistor::Input {
                        a: i.a,
                        b: i.b,
                        lut: i.lut,
                        requested: i.requested,
                        binding: i.binding,
                        authority: i.authority,
                        distinction: i.distinction,
                        drift: i.drift,
                    });
                    json!({"state":r.state,"value":r.value,"value_valid":r.value_valid==1,
                        "scope":"boolean_model_operation"})
                };
                // Produce explicit requests for an outer authorized executor. Source
                // text cannot grant authority or perform Git/network mutations.
                let successor = handler.statements.iter().any(|s| s == "execute successor");
                Ok(
                    json!({"state":if native_effect["state"]==1 {"HOLD"} else if successor {"SUCCESSOR_REQUIRED"} else {"CONTINUE"},
                    "requests":handler.statements,"source_digest":source,
                    "native_effect":native_effect,"dod_predicates":program.dod,"external_effect":false,"done":false}),
                )
            }
        }
    }
    pub fn append(&mut self, c: Command) -> Result<Value> {
        if let Some(&i) = self.ids.get(&c.event_id) {
            if self.records[i].0.command != c {
                return Err("CONFLICTING_REPLAY".into());
            }
            let (r, digest) = &self.records[i];
            let bytes = bounded_read(
                &self
                    .root
                    .join("events")
                    .join(format!("{:020}.json", r.sequence)),
                MAX_RECORD,
            )?;
            if sha256(&bytes) != *digest {
                return Err("REPLAY_READBACK_MISMATCH".into());
            }
            return Ok(
                json!({"state":"PERSISTED","replayed":true,"record":r,"digest":digest,"done":false}),
            );
        }
        let result = self.validate(&c)?;
        let old = self.checkpoint();
        let record = Record {
            schema: "qikvrt-event-v1".into(),
            sequence: old.sequence + 1,
            previous: old.digest,
            recorded_at: now(),
            implementation_sha256: self.implementation_sha256.clone(),
            store_identity: self.identity.clone(),
            command: c,
            result,
        };
        let bytes = json_bytes(&record)?;
        if bytes.len() as u64 > MAX_RECORD {
            return Err("RECORD_TOO_LARGE".into());
        }
        let digest = sha256(&bytes);
        publish(
            &self
                .root
                .join("events")
                .join(format!("{:020}.json", record.sequence)),
            &bytes,
        )?;
        publish(
            &self.anchor_path(record.sequence),
            &json_bytes(&Anchor {
                sequence: record.sequence,
                digest: digest.clone(),
            })?,
        )?;
        if record.sequence == 1 {
            publish(
                &self.root.join("history.started"),
                &json_bytes(&Anchor {
                    sequence: 1,
                    digest: digest.clone(),
                })?,
            )?;
        }
        self.ids
            .insert(record.command.event_id.clone(), self.records.len());
        self.records.push((record.clone(), digest.clone()));
        Ok(
            json!({"state":"PERSISTED","replayed":false,"record":record,"digest":digest,"done":false}),
        )
    }
    pub fn history(&self, after: u64) -> Value {
        json!(self
            .records
            .iter()
            .filter(|(r, _)| r.sequence > after)
            .take(128)
            .map(|(r, d)| json!({"record":r,"digest":d}))
            .collect::<Vec<_>>())
    }
    pub fn discover(&self, at: u64) -> Value {
        let mut nodes: BTreeMap<String, Vec<&Record>> = BTreeMap::new();
        for (r, _) in &self.records {
            if matches!(r.command.operation, Operation::Register { .. }) {
                nodes.entry(r.command.node_id.clone()).or_default().push(r);
            }
        }
        let entries:Vec<_>=nodes.into_iter().map(|(id,versions)|{
            let current=versions.last().unwrap();
            let observation=self.records.iter().rev().map(|r|&r.0).find(|r|
                r.sequence>current.sequence && r.command.node_id==id
                && r.command.subject==current.command.subject
                && matches!(r.command.operation,Operation::Reachability{..}));
            let liveness=match observation {
                Some(r)=>match r.command.operation {
                    Operation::Reachability{reachable:false,..}=>"OFFLINE",
                    Operation::Reachability{reachable:true,ttl_seconds} if at>=r.recorded_at
                        && at-r.recorded_at<u64::from(ttl_seconds)=>"OBSERVED_REACHABLE",
                    _=>"UNVERIFIED",
                },None=>"UNVERIFIED",
            };
            let (artifact,entrypoint)=match &current.command.operation {
                Operation::Register{artifact,entrypoint}=>(artifact,entrypoint),_=>unreachable!()};
            json!({"node_id":id,"subject":current.command.subject,"artifact":artifact,
                "entrypoint":entrypoint,"liveness":liveness,"history_retained":true,
                "registered_versions":versions.iter().map(|r|json!({"subject":r.command.subject,
                    "sequence":r.sequence,"operation":r.command.operation})).collect::<Vec<_>>(),
                "last_observation_sequence":observation.map(|r|r.sequence),"validation":"UNVERIFIED"})
        }).collect();
        json!({"schema":"qikvrt-directory-v1","identity":self.identity,"checkpoint":self.checkpoint(),
            "nodes":entries,"node_count":entries.len(),"done":false})
    }
}
