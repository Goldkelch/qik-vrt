// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
use std::{env, path::PathBuf, process::Command};
fn run(command: &mut Command) {
    let status = command.status().expect("C90 tool unavailable");
    assert!(status.success(), "C90 build failed");
}
fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("../../core");
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let host = env::var("HOST").unwrap();
    let target = env::var("TARGET").unwrap();
    if host != target && (env::var_os("CC").is_none() || env::var_os("AR").is_none()) {
        panic!("Cross builds require explicit target CC and AR; no guessed host compiler");
    }
    let cc = env::var_os("CC").unwrap_or_else(|| "cc".into());
    let ar = env::var_os("AR").unwrap_or_else(|| "ar".into());
    let mut objects = Vec::new();
    for name in [
        "qikvrt_kernel",
        "qikvrt_wire_v1",
        "qikvrt_sha256_v1",
        "qikvrt_exchange",
        "qikvrt_bus",
        "effect_ack_core",
    ] {
        let source = if name == "effect_ack_core" {
            root.join("../../src/effect_ack_core.c")
        } else {
            root.join(format!("src/{name}.c"))
        };
        let object = out.join(format!("{name}.o"));
        run(Command::new(&cc)
            .args([
                "-std=c90",
                "-pedantic-errors",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                "-fPIC",
                "-I",
            ])
            .arg(root.join("include"))
            .arg("-I")
            .arg(root.join("../../include"))
            .arg("-c")
            .arg(&source)
            .arg("-o")
            .arg(&object));
        println!("cargo:rerun-if-changed={}", source.display());
        objects.push(object);
    }
    run(Command::new(ar)
        .arg("crs")
        .arg(out.join("libqikvrt_c90.a"))
        .args(objects));
    println!("cargo:rerun-if-changed={}", root.join("include").display());
    println!(
        "cargo:rerun-if-changed={}",
        root.join("../../include/qikvrt/effect_ack.h").display()
    );
    println!("cargo:rerun-if-env-changed=CC");
    println!("cargo:rerun-if-env-changed=AR");
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=qikvrt_c90");
}
