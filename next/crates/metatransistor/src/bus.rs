// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
use crate::exchange::{Digest, Result, MAX_FRAME};
use alloc::alloc::{alloc_zeroed, dealloc};
use core::{
    alloc::Layout,
    ffi::{c_int, c_uint, c_void},
    ptr::NonNull,
};
extern "C" {
    fn qikvrt_bus_size() -> usize;
    fn qikvrt_bus_alignment() -> usize;
    fn qikvrt_bus_init(bus: *mut c_void);
    fn qikvrt_bus_bind(bus: *mut c_void, slot: c_uint, id: *const u8) -> c_int;
    fn qikvrt_bus_route(
        bus: *mut c_void,
        source: c_uint,
        frame: *const u8,
        length: c_uint,
        destination: *mut c_uint,
    ) -> c_int;
    fn qikvrt_bus_admission(authenticated: u8, policy_bound: u8) -> u8;
}
pub fn admission(authenticated: bool, policy_bound: bool) -> u8 {
    // SAFETY: by-value normalized predicates; existing C90 EAP core has no side effects.
    unsafe { qikvrt_bus_admission(u8::from(authenticated), u8::from(policy_bound)) }
}
pub struct Bus {
    state: NonNull<c_void>,
    layout: Layout,
}
impl Bus {
    pub fn new() -> Result<Self> {
        // SAFETY: C layout queries are pure and do not access caller memory.
        let (size, align) = unsafe { (qikvrt_bus_size(), qikvrt_bus_alignment()) };
        if size == 0 || size > 65536 {
            return Err("BUS_ABI_SIZE");
        }
        let layout = Layout::from_size_align(size, align).map_err(|_| "BUS_ABI_LAYOUT")?;
        // SAFETY: valid nonzero layout, uniquely owned and released once by Drop.
        let state = NonNull::new(unsafe { alloc_zeroed(layout) })
            .ok_or("ALLOCATION_FAILED")?
            .cast();
        let bus = Self { state, layout };
        // SAFETY: allocated size and alignment exactly match qikvrt_bus.
        unsafe {
            qikvrt_bus_init(bus.state.as_ptr());
        }
        Ok(bus)
    }
    pub fn bind(&mut self, slot: usize, id: &Digest) -> Result<()> {
        if slot >= 16 {
            return Err("BUS_PEER_BOUND");
        }
        // SAFETY: exclusive initialized bus, fixed digest and bounded index.
        if unsafe { qikvrt_bus_bind(self.state.as_ptr(), slot as c_uint, id.as_ptr()) } == 1 {
            Ok(())
        } else {
            Err("BUS_IDENTITY_BINDING")
        }
    }
    pub fn route(&mut self, source: usize, frame: &[u8]) -> Result<usize> {
        if source >= 16 || frame.len() < 88 || frame.len() > MAX_FRAME {
            return Err("BUS_FRAME_BOUND");
        }
        let mut destination = 0;
        // SAFETY: exclusive initialized bus, live bounded frame and writable output.
        if unsafe {
            qikvrt_bus_route(
                self.state.as_ptr(),
                source as c_uint,
                frame.as_ptr(),
                frame.len() as c_uint,
                &mut destination,
            )
        } == 1
        {
            Ok(destination as usize)
        } else {
            Err("BUS_ROUTE_OR_CORRELATION_HOLD")
        }
    }
}
impl Drop for Bus {
    fn drop(&mut self) {
        // SAFETY: this object uniquely owns its original allocation and exact layout.
        unsafe {
            dealloc(self.state.as_ptr().cast(), self.layout);
        }
    }
}
