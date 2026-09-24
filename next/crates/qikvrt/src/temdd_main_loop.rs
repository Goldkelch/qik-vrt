// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
// Canonical TEMDD outer main-loop semantics.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StageEvidence {
    pub compile: bool,
    pub bind: bool,
    pub resolve: bool,
    pub execute: bool,
    pub test: bool,
    pub observe: bool,
    pub readback: bool,
    pub accept: bool,
}

impl StageEvidence {
    pub fn effect_ack_done(self) -> bool {
        self.compile
            && self.bind
            && self.resolve
            && self.execute
            && self.test
            && self.observe
            && self.readback
            && self.accept
    }
}

pub trait Runtime {
    type Subject: Clone;

    fn compile(&mut self, subject: &Self::Subject) -> bool;
    fn bind(&mut self, subject: &Self::Subject) -> bool;
    fn resolve(&mut self, subject: &Self::Subject) -> bool;
    fn execute(&mut self, subject: &Self::Subject) -> bool;
    fn test(&mut self, subject: &Self::Subject) -> bool;
    fn observe(&mut self, subject: &Self::Subject) -> (bool, Self::Subject);
    fn readback(&mut self, successor: &Self::Subject) -> bool;
    fn accept(&mut self, successor: &Self::Subject) -> bool;
    fn bind_successor(&mut self, predecessor: &Self::Subject, successor: Self::Subject)
        -> Self::Subject;
}

pub fn run_one<R: Runtime>(runtime: &mut R, subject: R::Subject) -> (bool, R::Subject) {
    let compile = runtime.compile(&subject);
    let bind = runtime.bind(&subject);
    let resolve = runtime.resolve(&subject);
    let execute = runtime.execute(&subject);
    let test = runtime.test(&subject);
    let (observe, successor) = runtime.observe(&subject);
    let readback = runtime.readback(&successor);
    let accept = runtime.accept(&successor);
    let evidence = StageEvidence {
        compile,
        bind,
        resolve,
        execute,
        test,
        observe,
        readback,
        accept,
    };
    if evidence.effect_ack_done() {
        let rebound = runtime.bind_successor(&subject, successor);
        (true, rebound)
    } else {
        (false, subject)
    }
}

pub fn main_loop<R: Runtime>(runtime: &mut R, subject: R::Subject) -> ! {
    let mut current = subject;
    loop {
        let (done, next) = run_one(runtime, current);
        if done {
            current = next;
        } else {
            current = next;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn done_requires_all_eight_stage_results() {
        let full = StageEvidence {
            compile: true, bind: true, resolve: true, execute: true,
            test: true, observe: true, readback: true, accept: true,
        };
        assert!(full.effect_ack_done());
        let mut partial = full;
        partial.readback = false;
        assert!(!partial.effect_ack_done());
    }
}
