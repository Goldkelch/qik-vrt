// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
use qikvrt_next::{
    compiler, mesh, server,
    store::{now, Command, Store},
    Result,
};
use serde_json::json;
use std::{
    env, fs,
    hint::black_box,
    io::{self, BufRead, Read, Write},
    path::Path,
    time::Instant,
};

fn output(v: &serde_json::Value) -> Result<()> {
    let mut out = io::stdout().lock();
    serde_json::to_writer(&mut out, v).map_err(|e| e.to_string())?;
    out.write_all(b"\n")
        .and_then(|_| out.flush())
        .map_err(|e| e.to_string())
}
fn error(reason: String) -> serde_json::Value {
    json!({"state":"HOLD","reason":reason,"done":false})
}
fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("{}", error(e));
            std::process::ExitCode::from(2)
        }
    }
}
fn run() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    let usage = "qikvrt-next — C90 transputer with durable higher layers\n\
init STORE ID | verify STORE | discover STORE | history STORE [AFTER]\n\
put STORE FILE | get STORE SHA256 | snapshot STORE | restore-store STORE SNAPSHOT NEW_DIRECTORY\n\
compile FILE | run STORE | serve STORE [127.0.0.1:8771]\n\
bus-config NEW_DIRECTORY BUS_ID SUBJECT_JSON PEER_ID...\n\
bus-repository-config NEW_DIRECTORY BUS_ID SUBJECT_JSON NODES_JSON\n\
bus-serve STORE PRIVATE_BUS_CONFIG IP:PORT [--supervised]\n\
bus-peer STORE PRIVATE_PEER_CREDENTIAL IP:PORT [--worker] [--terminal 127.0.0.1:PORT]\n\
subject-digest SUBJECT_JSON | packet FROM TO SUBJECT_SHA256 CODEC FILE\n\
unpack FROM TO SUBJECT_SHA256 [reverse] | exchange STORE FROM SUBJECT_SHA256\n\
mesh-serve STORE PEER SUBJECT_SHA256 [127.0.0.1:8772]\n\
mesh-send FROM TO SUBJECT_SHA256 CODEC FILE 127.0.0.1:PORT\n\
bench [COUNT] | vectors";
    let op = args.get(1).ok_or(usage)?;
    let arg = |n: usize| {
        args.get(n)
            .map(|s| s.as_str())
            .ok_or_else(|| usage.to_string())
    };
    match op.as_str() {
        "help" | "--help" | "-h" => {
            println!("{usage}");
            Ok(())
        }
        "bus-config" => {
            let subject = serde_json::from_slice(&fs::read(arg(4)?).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            qikvrt_next::bus::create_config(Path::new(arg(2)?), arg(3)?, subject, &args[5..])?;
            output(&json!({"state":"CREATED","credential_files":"owner-only","done":false}))
        }
        "bus-repository-config" => {
            let subject = serde_json::from_slice(&fs::read(arg(4)?).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            let nodes = serde_json::from_slice(&fs::read(arg(5)?).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            qikvrt_next::bus::create_repository_config(
                Path::new(arg(2)?),
                arg(3)?,
                subject,
                nodes,
            )?;
            output(&json!({"state":"CREATED","credential_files":"owner-only","done":false}))
        }
        "bus-serve" => qikvrt_next::bus::serve(
            Path::new(arg(2)?),
            Path::new(arg(3)?),
            arg(4)?,
            args.get(5).map(|s| s == "--supervised").unwrap_or(false),
        ),
        "bus-peer" => {
            let mut worker = false;
            let mut terminal = None;
            let mut options = args[5..].iter();
            while let Some(option) = options.next() {
                match option.as_str() {
                    "--worker" => worker = true,
                    "--terminal" => {
                        terminal = Some(options.next().ok_or("TERMINAL_ADDRESS_REQUIRED")?.as_str())
                    }
                    _ => return Err("UNKNOWN_PEER_OPTION".into()),
                }
            }
            qikvrt_next::bus::peer(
                Path::new(arg(2)?),
                Path::new(arg(3)?),
                arg(4)?,
                worker,
                terminal,
            )
        }
        "snapshot" => {
            let s = Store::open(Path::new(arg(2)?))?;
            let digest = s.export_snapshot()?;
            output(
                &json!({"snapshot":digest,"source_identity":s.identity(),"source_checkpoint":s.checkpoint(),"scope":"exact_committed_store_bytes"}),
            )
        }
        "restore-store" => {
            let s = Store::open(Path::new(arg(2)?))?;
            let checkpoint = s.restore_snapshot(arg(3)?, Path::new(arg(4)?))?;
            output(
                &json!({"state":"RESTORED","checkpoint":checkpoint,"reexecuted":false,"done":false}),
            )
        }
        "subject-digest" => {
            let subject = serde_json::from_slice(&fs::read(arg(2)?).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            println!("{}", mesh::subject_digest(&subject));
            Ok(())
        }
        "packet" | "mesh-send" => {
            let b = mesh::binding(arg(2)?, arg(3)?, arg(4)?)?;
            let codec = arg(5)?.parse::<u8>().map_err(|_| "CODEC_REQUIRED")?;
            let mut body = Vec::new();
            fs::File::open(arg(6)?)
                .map_err(|e| e.to_string())?
                .take(62785)
                .read_to_end(&mut body)
                .map_err(|e| e.to_string())?;
            if op == "packet" {
                mesh::write_frames(&mut io::stdout().lock(), mesh::packet(&b, codec, &body)?)
            } else {
                output(&mesh::send(&b, codec, &body, arg(7)?)?)
            }
        }
        "unpack" => {
            let b = mesh::binding(arg(2)?, arg(3)?, arg(4)?)?;
            let reverse = args.get(5).map(|x| x == "reverse").unwrap_or(false);
            let b = if reverse { b.reverse() } else { b };
            let t = mesh::receive(&mut io::stdin().lock(), &b, reverse)?;
            io::stdout().write_all(&t.body).map_err(|e| e.to_string())
        }
        "exchange" => {
            let mut store = Store::open(Path::new(arg(2)?))?;
            let b = mesh::binding(arg(3)?, store.identity(), arg(4)?)?;
            mesh::exchange(
                &mut store,
                &mut io::stdin().lock(),
                &mut io::stdout().lock(),
                &b,
            )
        }
        "mesh-serve" => mesh::serve(
            Path::new(arg(2)?),
            arg(3)?,
            arg(4)?,
            args.get(5).map(|s| s.as_str()).unwrap_or("127.0.0.1:8772"),
        ),
        "init" => {
            Store::init(Path::new(arg(2)?), arg(3)?)?;
            output(&json!({"state":"INITIALIZED","done":false}))
        }
        "compile" => {
            let p = compiler::compile(&fs::read_to_string(arg(2)?).map_err(|e| e.to_string())?)?;
            output(&serde_json::to_value(p).map_err(|e| e.to_string())?)
        }
        "put" => {
            let s = Store::open(Path::new(arg(2)?))?;
            let bytes = fs::read(arg(3)?).map_err(|e| e.to_string())?;
            let digest = s.put(&bytes)?;
            output(&json!({"sha256":digest,"bytes":bytes.len(),"scope":"object_readback"}))
        }
        "get" => {
            let s = Store::open(Path::new(arg(2)?))?;
            let bytes = s.get(arg(3)?)?;
            io::stdout().write_all(&bytes).map_err(|e| e.to_string())
        }
        "discover" => output(&Store::open(Path::new(arg(2)?))?.discover(now())),
        "history" => output(
            &Store::open(Path::new(arg(2)?))?.history(
                args.get(3)
                    .map(|s| s.parse::<u64>())
                    .transpose()
                    .map_err(|e| e.to_string())?
                    .unwrap_or(0),
            ),
        ),
        "verify" => {
            let s = Store::open(Path::new(arg(2)?))?;
            output(
                &json!({"state":"VERIFIED","scope":"local_store_history","checkpoint":s.checkpoint(),"done":false}),
            )
        }
        "run" => {
            let mut s = Store::open(Path::new(arg(2)?))?;
            let stdin = io::stdin();
            let mut input = stdin.lock();
            loop {
                let mut line = Vec::new();
                let n = input
                    .by_ref()
                    .take(65538)
                    .read_until(b'\n', &mut line)
                    .map_err(|e| e.to_string())?;
                if n == 0 {
                    break;
                }
                if n > 65536 || !line.ends_with(b"\n") {
                    output(&error("BOUNDED_NEWLINE_REQUIRED".into()))?;
                    if !line.ends_with(b"\n") {
                        loop {
                            let b = input.fill_buf().map_err(|e| e.to_string())?;
                            if b.is_empty() {
                                break;
                            }
                            let end = b.iter().position(|&x| x == b'\n');
                            let used = end.map(|x| x + 1).unwrap_or(b.len());
                            input.consume(used);
                            if end.is_some() {
                                break;
                            }
                        }
                    }
                    continue;
                }
                let result = serde_json::from_slice::<Command>(&line)
                    .map_err(|e| e.to_string())
                    .and_then(|c| s.append(c));
                output(&result.unwrap_or_else(error))?;
            }
            Ok(())
        }
        "serve" => server::serve(
            Path::new(arg(2)?),
            args.get(3).map(|s| s.as_str()).unwrap_or("127.0.0.1:8771"),
        ),
        "vectors" => {
            for lut in 0..16 {
                for a in 0..2 {
                    for b in 0..2 {
                        for requested in 0..4 {
                            for mask in 0..81 {
                                let mut x = mask;
                                let binding = x % 3;
                                x /= 3;
                                let authority = x % 3;
                                x /= 3;
                                let distinction = x % 3;
                                x /= 3;
                                let drift = x % 3;
                                let r =
                                    qikvrt_metatransistor::evaluate(qikvrt_metatransistor::Input {
                                        a,
                                        b,
                                        lut,
                                        requested,
                                        binding,
                                        authority,
                                        distinction,
                                        drift,
                                    });
                                println!("{lut} {a} {b} {requested} {binding} {authority} {distinction} {drift} {} {:08X} {}",r.state,r.value,r.value_valid);
                            }
                        }
                    }
                }
            }
            Ok(())
        }
        "bench" => {
            let n = args
                .get(2)
                .map(|s| s.parse::<u64>())
                .transpose()
                .map_err(|e| e.to_string())?
                .unwrap_or(2_000_000);
            if n == 0 || n > 1_000_000_000 {
                return Err("BENCH_COUNT_OUT_OF_RANGE".into());
            }
            let mut values = Vec::new();
            let mut checksum = 0u32;
            for _ in 0..5 {
                let start = Instant::now();
                for i in 0..n {
                    let r =
                        qikvrt_metatransistor::evaluate(black_box(qikvrt_metatransistor::Input {
                            a: i as u32,
                            b: (i as u32).rotate_left(7),
                            lut: (i % 16) as u8,
                            requested: 2,
                            binding: 1,
                            authority: 1,
                            distinction: 1,
                            drift: 0,
                        }));
                    checksum ^= black_box(r.value);
                }
                values.push(start.elapsed().as_nanos());
            }
            values.sort();
            let ns = values[2] as f64 / n as f64;
            output(
                &json!({"scope":"in_memory_32_lane_kernel_only","iterations_per_sample":n,
                "samples_ns":values,"median_ns_per_event":ns,"median_events_per_second":1e9/ns,
                "checksum":checksum,"disk_network_hardware_clock_included":false}),
            )
        }
        _ => Err(usage.into()),
    }
}
