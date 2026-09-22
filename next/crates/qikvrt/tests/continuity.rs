// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
use qikvrt_next::{
    compiler,
    store::{now, Command, Operation, Store, Subject},
};
use std::{
    fs,
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Space(PathBuf);
impl Space {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "qikvrt-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
        Self(p)
    }
    fn init(&self) {
        Store::init(&self.0, "test-transputer").unwrap();
    }
}
impl Drop for Space {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn subject(n: char) -> Subject {
    Subject {
        repository: "ingolf-lohmann/qik-vrt".into(),
        subject_id: "transputer".into(),
        head: n.to_string().repeat(40),
        tree: "b".repeat(40),
    }
}
fn cmd(id: &str, operation: Operation) -> Command {
    Command {
        event_id: id.into(),
        node_id: "universal-transputer".into(),
        subject: subject('a'),
        cause_event_ids: vec![],
        operation,
    }
}
fn register(s: &mut Store, id: &str) -> Command {
    let hash = s.put(b"preserved implementation capsule").unwrap();
    let c = cmd(
        id,
        Operation::Register {
            artifact: hash,
            entrypoint: "AI".into(),
        },
    );
    s.append(c.clone()).unwrap();
    c
}
fn reach(id: &str, on: bool) -> Command {
    cmd(
        id,
        Operation::Reachability {
            reachable: on,
            ttl_seconds: 60,
        },
    )
}

#[test]
fn restart_and_offline_never_remove_identity() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    s.append(reach("offline", false)).unwrap();
    let anchor = s.checkpoint();
    drop(s);
    for _ in 0..32 {
        let s = Store::open(&p.0).unwrap();
        s.check_anchor(&anchor).unwrap();
        let d = s.discover(now() + 10000);
        assert_eq!(d["node_count"], 1);
        assert_eq!(d["nodes"][0]["liveness"], "OFFLINE");
    }
}
#[test]
fn expired_observation_preserves_last_version() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    s.append(reach("alive", true)).unwrap();
    let d = s.discover(now() + 120);
    assert_eq!(d["nodes"][0]["liveness"], "UNVERIFIED");
    assert_eq!(d["node_count"], 1);
}
#[test]
fn successor_keeps_history_but_cannot_borrow_liveness() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    let old = register(&mut s, "register");
    s.append(reach("alive", true)).unwrap();
    let mut next = old.clone();
    next.event_id = "new-subject".into();
    next.subject = subject('c');
    next.cause_event_ids = vec!["register".into()];
    s.append(next).unwrap();
    assert_eq!(
        s.append(reach("old-evidence", true)).unwrap_err(),
        "EXACT_SUBJECT_MISMATCH"
    );
    let d = s.discover(now());
    assert_eq!(d["nodes"][0]["liveness"], "UNVERIFIED");
    assert_eq!(
        d["nodes"][0]["registered_versions"]
            .as_array()
            .unwrap()
            .len(),
        2
    );
    assert_eq!(s.checkpoint().sequence, 3);
}
#[test]
fn replay_is_idempotent_and_conflict_fails_closed() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    let old = register(&mut s, "register");
    assert_eq!(s.append(old.clone()).unwrap()["replayed"], true);
    let mut conflict = old;
    conflict.subject = subject('c');
    assert_eq!(s.append(conflict).unwrap_err(), "CONFLICTING_REPLAY");
    assert_eq!(s.checkpoint().sequence, 1);
}
#[test]
fn chronology_does_not_create_causal_edges() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    s.append(reach("unrelated", false)).unwrap();
    assert_eq!(
        s.history(1)[0]["record"]["command"]["cause_event_ids"],
        serde_json::json!([])
    );
    let mut orphan = reach("orphan", false);
    orphan.cause_event_ids = vec!["not-observed".into()];
    assert_eq!(
        s.append(orphan).unwrap_err(),
        "CAUSE_NOT_BOUND_TO_EXISTING_EVENT"
    );
}
#[test]
fn deleted_history_is_not_an_empty_success() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    drop(s);
    fs::remove_file(p.0.join("events/00000000000000000001.json")).unwrap();
    assert!(matches!(Store::open(&p.0),Err(e) if e=="PREVIOUSLY_USED_STORE_IS_EMPTY"));
    assert!(Store::init(&p.0, "replacement").is_err());
    assert!(p.0.join("anchors/00000000000000000001.json").exists());
}

#[test]
fn empty_reconstruction_and_identity_substitution_are_detected() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    drop(s);
    let meta = p.0.join("meta.json");
    let original = fs::read(&meta).unwrap();
    fs::write(
        &meta,
        b"{\"schema\":\"qikvrt-store-v1\",\"identity\":\"replacement\"}",
    )
    .unwrap();
    assert!(matches!(Store::open(&p.0),Err(e) if e=="HISTORY_BINDING_MISMATCH"));
    fs::write(&meta, original).unwrap();
    for dir in ["events", "anchors"] {
        for entry in fs::read_dir(p.0.join(dir)).unwrap() {
            fs::remove_file(entry.unwrap().path()).unwrap();
        }
    }
    assert!(matches!(Store::open(&p.0),Err(e) if e=="PREVIOUSLY_USED_STORE_IS_EMPTY"));
}
#[test]
fn partial_record_and_missing_object_preserve_all_original_bytes() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    drop(s);
    let file = p.0.join("events/00000000000000000001.json");
    fs::write(&file, b"{\"interrupted\":").unwrap();
    assert!(Store::open(&p.0).is_err());
    assert_eq!(fs::read(&file).unwrap(), b"{\"interrupted\":");
}
#[test]
fn crash_between_commit_and_anchor_recovers_without_reexecution() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    let c = register(&mut s, "register");
    let anchor = s.checkpoint();
    drop(s);
    fs::remove_file(p.0.join("anchors/00000000000000000001.json")).unwrap();
    let mut s = Store::open(&p.0).unwrap();
    s.check_anchor(&anchor).unwrap();
    assert_eq!(s.append(c).unwrap()["replayed"], true);
    assert_eq!(s.checkpoint().sequence, 1);
}
#[test]
fn writer_lock_releases_after_owner_drops() {
    let p = Space::new();
    p.init();
    let s = Store::open(&p.0).unwrap();
    assert!(matches!(Store::open(&p.0),Err(e) if e=="ACTIVE_WRITER"));
    drop(s);
    assert!(Store::open(&p.0).is_ok());
}
#[test]
fn object_tampering_is_rejected() {
    let p = Space::new();
    p.init();
    let s = Store::open(&p.0).unwrap();
    let digest = s.put(b"original").unwrap();
    fs::write(p.0.join("objects").join(&digest), b"tampered").unwrap();
    assert_eq!(s.get(&digest).unwrap_err(), "OBJECT_DIGEST_MISMATCH");
}
#[test]
fn symlink_store_is_rejected() {
    let p = Space::new();
    p.init();
    let other = Space::new();
    std::os::unix::fs::symlink(&p.0, &other.0).unwrap();
    assert!(matches!(Store::open(&other.0),Err(e) if e=="REAL_DIRECTORY_REQUIRED"));
}
const PROGRAM:&str="temdd 0.1; authority owner = \"Ingolf Lohmann\"; subject transputer { repository = \"ingolf-lohmann/qik-vrt\"; binding = exact; } request r { target = CONTINUITY; } on event { follow exact; classify causal; } until { IDENTITY_RETAINED; }";
#[test]
fn compiler_consumes_whole_program_and_rejects_executable_junk() {
    assert!(compiler::compile(PROGRAM).is_ok());
    for junk in [
        " shell run;",
        " on event { follow exact; }",
        " authority another = \"X\";",
        " garbage",
    ] {
        assert!(compiler::compile(&format!("{PROGRAM}{junk}")).is_err());
    }
    assert!(compiler::compile(&PROGRAM.replace("follow exact", "execute shell")).is_err());
}
#[test]
fn program_requests_are_bound_and_persisted() {
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    let source = s.put(PROGRAM.as_bytes()).unwrap();
    let r = s
        .append(cmd(
            "follow",
            Operation::Program {
                source,
                event: "event".into(),
                input: None,
            },
        ))
        .unwrap();
    assert_eq!(
        r["record"]["result"]["requests"],
        serde_json::json!(["follow exact", "classify causal"])
    );
    assert_eq!(r["record"]["result"]["external_effect"], false);
    assert_eq!(r["done"], false);
}

#[test]
fn temdd_program_drives_native_lut_then_durable_readback() {
    use qikvrt_next::store::NativeInput;
    let p = Space::new();
    p.init();
    let mut s = Store::open(&p.0).unwrap();
    register(&mut s, "register");
    let program=PROGRAM.replace("classify causal;","classify causal; effect boolean_lut { require authority; require validation; commit; readback; }");
    let source = s.put(program.as_bytes()).unwrap();
    let input = NativeInput {
        a: 13,
        b: 9,
        lut: 6,
        requested: 2,
        binding: 1,
        authority: 1,
        distinction: 1,
        drift: 0,
    };
    let result = s
        .append(cmd(
            "compute",
            Operation::Program {
                source: source.clone(),
                event: "event".into(),
                input: Some(input.clone()),
            },
        ))
        .unwrap();
    assert_eq!(result["record"]["result"]["native_effect"]["value"], 4);
    assert_eq!(
        result["record"]["result"]["native_effect"]["value_valid"],
        true
    );
    let mut withheld = input;
    withheld.authority = 2;
    let result = s
        .append(cmd(
            "withheld",
            Operation::Program {
                source,
                event: "event".into(),
                input: Some(withheld),
            },
        ))
        .unwrap();
    assert_eq!(result["record"]["result"]["state"], "HOLD");
    assert_eq!(
        result["record"]["result"]["native_effect"]["value_valid"],
        false
    );
    let anchor = s.checkpoint();
    drop(s);
    Store::open(&p.0).unwrap().check_anchor(&anchor).unwrap();
}
