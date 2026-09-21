// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
//! Safe Rust adapter over the portable C90 reference. Only octets cross the ABI.
#![no_std]
#![deny(unsafe_op_in_unsafe_fn)]
extern crate alloc;
pub mod bus;
pub mod exchange;

pub const OBSERVE: u8 = 0;
pub const HOLD: u8 = 1;
pub const CONTINUE: u8 = 2;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Input {
    pub a: u32,
    pub b: u32,
    pub lut: u8,
    pub requested: u8,
    pub binding: u8,
    pub authority: u8,
    pub distinction: u8,
    pub drift: u8,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Output {
    pub value: u32,
    pub state: u8,
    pub value_valid: u8,
}
extern "C" {
    fn qikvrt_evaluate_bytes(input: *const u8, output: *mut u8);
}
pub fn evaluate(i: Input) -> Output {
    let mut input = [0u8; 14];
    let mut output = [0u8; 6];
    input[..4].copy_from_slice(&i.a.to_be_bytes());
    input[4..8].copy_from_slice(&i.b.to_be_bytes());
    input[8..].copy_from_slice(&[
        i.lut,
        i.requested,
        i.binding,
        i.authority,
        i.distinction,
        i.drift,
    ]);
    // SAFETY: disjoint live arrays of the exact 14/6-byte C contract; no retained pointers.
    unsafe {
        qikvrt_evaluate_bytes(input.as_ptr(), output.as_mut_ptr());
    }
    Output {
        value: u32::from_be_bytes(output[..4].try_into().unwrap()),
        state: output[4],
        value_valid: output[5],
    }
}
pub fn boolean_lut(a: u32, b: u32, lut: u8) -> u32 {
    evaluate(Input {
        a,
        b,
        lut,
        requested: CONTINUE,
        binding: 1,
        authority: 1,
        distinction: 1,
        drift: 0,
    })
    .value
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn all_boolean_functions_and_lane_positions() {
        for lut in 0..16 {
            for a in 0..2 {
                for b in 0..2 {
                    for bit in 0..32 {
                        let got = (boolean_lut(a << bit, b << bit, lut) >> bit) & 1;
                        assert_eq!(got, ((lut >> (2 * a + b)) & 1) as u32);
                    }
                }
            }
        }
    }
    #[test]
    fn all_three_valued_guards_fail_closed() {
        for binding in 0..3 {
            for authority in 0..3 {
                for distinction in 0..3 {
                    for drift in 0..3 {
                        for requested in 0..4 {
                            let o = evaluate(Input {
                                a: 7,
                                b: 3,
                                lut: 6,
                                requested,
                                binding,
                                authority,
                                distinction,
                                drift,
                            });
                            let expected = if binding == 1
                                && authority == 1
                                && distinction == 1
                                && drift == 0
                                && requested < 3
                            {
                                requested
                            } else {
                                HOLD
                            };
                            assert_eq!(o.state, expected);
                            assert_eq!(o.value_valid, u8::from(expected == CONTINUE));
                        }
                    }
                }
            }
        }
    }
    #[test]
    fn nand_composition_full_adder() {
        fn nand(a: u32, b: u32) -> u32 {
            boolean_lut(a, b, 7) & 1
        }
        fn xor(a: u32, b: u32) -> u32 {
            let n = nand(a, b);
            nand(nand(a, n), nand(b, n))
        }
        for a in 0..2 {
            for b in 0..2 {
                for carry in 0..2 {
                    let ab = xor(a, b);
                    let sum = xor(ab, carry);
                    let out = nand(nand(a, b), nand(ab, carry));
                    assert_eq!(sum + 2 * out, a + b + carry);
                }
            }
        }
    }
}
