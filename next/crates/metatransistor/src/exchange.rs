// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
//! The only unsafe boundary. Allocation lives above the allocation-free C90 core.
use alloc::{
    alloc::{alloc_zeroed, dealloc},
    vec,
    vec::Vec,
};
use core::{
    alloc::Layout,
    ffi::{c_int, c_uint, c_void},
    ptr::NonNull,
};
pub const MAX_FRAME: usize = 4184;
pub const MAX_MESSAGE: usize = 62784;
pub const CHUNK: usize = 3924;
pub type Digest = [u8; 32];
pub type Result<T> = core::result::Result<T, &'static str>;
extern "C" {
    fn qikvrt_route(
        route: *mut u8,
        source: *const u8,
        destination: *const u8,
        subject: *const u8,
        sl: u8,
        dl: u8,
        codec: u8,
        body: *const u8,
        length: c_uint,
    ) -> c_int;
    fn qikvrt_pack_bytes(
        metadata: *const u8,
        payload: *const u8,
        length: c_uint,
        out: *mut u8,
        capacity: c_uint,
        written: *mut c_uint,
    ) -> c_int;
    fn qikvrt_unpack_bytes(
        frame: *const u8,
        length: c_uint,
        metadata: *mut u8,
        payload: *mut u8,
        capacity: c_uint,
    ) -> c_int;
    fn qikvrt_receiver_size() -> usize;
    fn qikvrt_receiver_alignment() -> usize;
    fn qikvrt_receiver_init(
        receiver: *mut c_void,
        storage: *mut u8,
        capacity: c_uint,
        source: *const u8,
        destination: *const u8,
        subject: *const u8,
        sl: u8,
        dl: u8,
    ) -> c_int;
    fn qikvrt_receive(receiver: *mut c_void, frame: *const u8, length: c_uint) -> c_int;
    fn qikvrt_receiver_length(receiver: *const c_void) -> c_uint;
    fn qikvrt_receiver_codec(receiver: *const c_void) -> u8;
    fn qikvrt_receiver_correlation(receiver: *const c_void, out: *mut u8);
}
#[derive(Clone, Debug)]
pub struct Binding {
    pub source: Digest,
    pub destination: Digest,
    pub subject: Digest,
    pub source_layer: u8,
    pub destination_layer: u8,
}
impl Binding {
    pub fn reverse(&self) -> Self {
        Self {
            source: self.destination,
            destination: self.source,
            subject: self.subject,
            source_layer: self.destination_layer,
            destination_layer: self.source_layer,
        }
    }
}
pub fn unpack(frame: &[u8]) -> Result<([u8; 48], Vec<u8>)> {
    if frame.len() < 88 || frame.len() > MAX_FRAME {
        return Err("FRAME_SIZE");
    }
    let mut meta = [0; 48];
    let mut payload = vec![0; 4096];
    // SAFETY: bounded frame, separate full-size metadata and payload; C validates all offsets.
    let ok = unsafe {
        qikvrt_unpack_bytes(
            frame.as_ptr(),
            frame.len() as c_uint,
            meta.as_mut_ptr(),
            payload.as_mut_ptr(),
            4096,
        )
    };
    if ok != 1 {
        return Err("FRAME_INTEGRITY");
    }
    let n = u32::from_be_bytes(meta[44..48].try_into().unwrap()) as usize;
    if n > 4096 {
        return Err("C_ABI_LENGTH");
    }
    payload.truncate(n);
    Ok((meta, payload))
}
pub fn pack(meta: &[u8; 48], payload: &[u8]) -> Result<Vec<u8>> {
    if payload.len() > 4096 {
        return Err("PAYLOAD_BOUND");
    }
    let mut out = vec![0; MAX_FRAME];
    let mut n = 0;
    // SAFETY: live disjoint buffers, bounded lengths and a valid output length pointer.
    let ok = unsafe {
        qikvrt_pack_bytes(
            meta.as_ptr(),
            payload.as_ptr(),
            payload.len() as c_uint,
            out.as_mut_ptr(),
            MAX_FRAME as c_uint,
            &mut n,
        )
    };
    if ok != 1 || n as usize > MAX_FRAME {
        return Err("FRAME_ENCODING");
    }
    out.truncate(n as usize);
    Ok(out)
}
pub fn frames(
    binding: &Binding,
    codec: u8,
    body: &[u8],
    session: u32,
    nonce: u32,
    message: u32,
    receipt: bool,
) -> Result<Vec<Vec<u8>>> {
    frames_correlated(binding, codec, body, session, nonce, message, receipt, None)
}
pub fn frames_correlated(
    binding: &Binding,
    codec: u8,
    body: &[u8],
    session: u32,
    nonce: u32,
    message: u32,
    receipt: bool,
    correlation: Option<&Digest>,
) -> Result<Vec<Vec<u8>>> {
    if body.len() > MAX_MESSAGE {
        return Err("MESSAGE_BOUND");
    }
    let mut route = [0u8; 172];
    // SAFETY: fixed-size route and digests; bounded body read only for this call.
    let ok = unsafe {
        qikvrt_route(
            route.as_mut_ptr(),
            binding.source.as_ptr(),
            binding.destination.as_ptr(),
            binding.subject.as_ptr(),
            binding.source_layer,
            binding.destination_layer,
            codec,
            body.as_ptr(),
            body.len() as c_uint,
        )
    };
    if ok != 1 {
        return Err("ROUTE_ENCODING");
    }
    if let Some(c) = correlation {
        route[140..172].copy_from_slice(c);
    }
    let chunks = body.len().max(1).div_ceil(CHUNK);
    let mut result = Vec::new();
    for index in 0..chunks {
        let start = index * CHUNK;
        let end = body.len().min(start + CHUNK);
        let mut payload = route.to_vec();
        payload.extend_from_slice(&body[start..end]);
        let mut m = [0u8; 48];
        m[..4].copy_from_slice(b"QVRT");
        m[4] = 1;
        m[5] = u8::from(receipt);
        m[6] = if receipt { 3 } else { 1 };
        m[7] = 1;
        // Transport receipt carries CONTINUE, never synthesizes D4 DONE.
        m[9] = u8::from(receipt);
        m[11] = 84;
        for (offset, value) in [
            (12, session),
            (16, nonce),
            (
                20,
                u32::from_be_bytes(binding.source[..4].try_into().unwrap()),
            ),
            (32, message),
            (36, index as u32),
            (40, chunks as u32),
        ] {
            m[offset..offset + 4].copy_from_slice(&value.to_be_bytes());
        }
        result.push(pack(&m, &payload)?);
    }
    Ok(result)
}
pub struct Receiver {
    state: NonNull<c_void>,
    layout: Layout,
    storage: Vec<u8>,
}
impl Receiver {
    pub fn new(b: &Binding) -> Result<Self> {
        // SAFETY: pure C sizeof/offsetof queries; no pointers are supplied.
        let (size, align) = unsafe { (qikvrt_receiver_size(), qikvrt_receiver_alignment()) };
        let layout = Layout::from_size_align(size, align).map_err(|_| "C_ABI_LAYOUT")?;
        if size == 0 || size > 16384 {
            return Err("C_ABI_SIZE");
        }
        // SAFETY: valid nonzero layout; matched by Drop, allocation ownership is unique.
        let state = NonNull::new(unsafe { alloc_zeroed(layout) })
            .ok_or("ALLOCATION_FAILED")?
            .cast();
        let mut this = Self {
            state,
            layout,
            storage: vec![0; MAX_MESSAGE],
        };
        // SAFETY: correctly aligned receiver allocation and stable Vec backing allocation.
        // C retains only storage's pointer. It cannot outlive this object or resize it.
        let ok = unsafe {
            qikvrt_receiver_init(
                this.state.as_ptr(),
                this.storage.as_mut_ptr(),
                MAX_MESSAGE as c_uint,
                b.source.as_ptr(),
                b.destination.as_ptr(),
                b.subject.as_ptr(),
                b.source_layer,
                b.destination_layer,
            )
        };
        if ok != 1 {
            return Err("RECEIVER_BINDING");
        }
        Ok(this)
    }
    pub fn feed(&mut self, frame: &[u8]) -> Result<Option<(u8, Vec<u8>, Digest)>> {
        if frame.len() < 88 || frame.len() > MAX_FRAME {
            return Err("FRAME_SIZE");
        }
        // SAFETY: initialized uniquely borrowed receiver; bounded frame lives through call.
        let status =
            unsafe { qikvrt_receive(self.state.as_ptr(), frame.as_ptr(), frame.len() as c_uint) };
        match status {
            1 | 3 => Ok(None),
            2 => {
                // SAFETY: valid complete receiver, getters do not retain or mutate Rust data.
                let (n, codec) = unsafe {
                    (
                        qikvrt_receiver_length(self.state.as_ptr()) as usize,
                        qikvrt_receiver_codec(self.state.as_ptr()),
                    )
                };
                if n > MAX_MESSAGE {
                    return Err("C_ABI_LENGTH");
                }
                let mut correlation = [0u8; 32];
                // SAFETY: live complete receiver and exact writable digest buffer.
                unsafe {
                    qikvrt_receiver_correlation(self.state.as_ptr(), correlation.as_mut_ptr());
                }
                Ok(Some((codec, self.storage[..n].to_vec(), correlation)))
            }
            _ => Err("TRANSFER_BINDING_OR_INTEGRITY"),
        }
    }
}
impl Drop for Receiver {
    fn drop(&mut self) {
        // SAFETY: exact original allocation/layout, freed once. C has no destructor/heap state.
        unsafe {
            dealloc(self.state.as_ptr().cast(), self.layout);
        }
    }
}
