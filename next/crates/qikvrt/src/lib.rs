// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
#![forbid(unsafe_code)]
pub mod bus;
pub mod compiler;
pub mod mesh;
pub mod server;
pub mod store;
pub mod temdd_main_loop;

pub type Result<T> = std::result::Result<T, String>;
pub fn sha256(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(bytes))
}
