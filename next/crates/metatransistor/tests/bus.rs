// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
use qikvrt_metatransistor::{
    bus::{admission, Bus},
    exchange::{frames, frames_correlated, unpack, Binding},
};
#[test]
fn c90_eap_participation_does_not_release_effects() {
    assert_eq!(admission(true, true), 1);
    for (a, p) in [(false, false), (false, true), (true, false)] {
        assert_eq!(admission(a, p), 3);
    }
}
#[test]
fn c90_bus_routes_simultaneously_in_both_directions_and_binds_replies() {
    let mut bus = Bus::new().unwrap();
    bus.bind(0, &[1; 32]).unwrap();
    bus.bind(1, &[2; 32]).unwrap();
    bus.bind(2, &[3; 32]).unwrap();
    let b = Binding {
        source: [1; 32],
        destination: [2; 32],
        subject: [4; 32],
        source_layer: 1,
        destination_layer: 4,
    };
    let a = frames(&b, 2, b"A to B", 1, 2, 3, false).unwrap();
    let reverse = frames(&b.reverse(), 2, b"B to A", 1, 2, 3, false).unwrap();
    assert_eq!(bus.route(0, &a[0]).unwrap(), 1);
    assert_eq!(bus.route(1, &reverse[0]).unwrap(), 0);
    let correlation: [u8; 32] = unpack(&a[0]).unwrap().1[140..172].try_into().unwrap();
    let reply = frames_correlated(
        &b.reverse(),
        3,
        b"result",
        1,
        2,
        3,
        true,
        Some(&correlation),
    )
    .unwrap();
    assert!(bus.route(2, &reply[0]).is_err());
    assert_eq!(bus.route(1, &reply[0]).unwrap(), 0);
    let wrong =
        frames_correlated(&b.reverse(), 3, b"wrong", 1, 2, 3, true, Some(&[0; 32])).unwrap();
    assert!(bus.route(1, &wrong[0]).is_err());
    let later = frames_correlated(
        &b.reverse(),
        3,
        b"later observation",
        1,
        2,
        3,
        true,
        Some(&correlation),
    )
    .unwrap();
    assert_eq!(bus.route(1, &later[0]).unwrap(), 0);
}
#[test]
fn outstanding_calls_apply_backpressure_without_evicting_requests() {
    let mut bus = Bus::new().unwrap();
    bus.bind(0, &[1; 32]).unwrap();
    bus.bind(1, &[2; 32]).unwrap();
    let b = Binding {
        source: [1; 32],
        destination: [2; 32],
        subject: [4; 32],
        source_layer: 1,
        destination_layer: 4,
    };
    for i in 0..32 {
        assert_eq!(
            bus.route(0, &frames(&b, 2, &[i], 1, 2, i as u32, false).unwrap()[0])
                .unwrap(),
            1
        );
    }
    let extra = frames(&b, 2, b"extra", 1, 2, 32, false).unwrap();
    assert!(bus.route(0, &extra[0]).is_err());
    let original = frames(&b, 2, &[0], 1, 2, 0, false).unwrap();
    let correlation = unpack(&original[0]).unwrap().1[140..172]
        .try_into()
        .unwrap();
    let reply = frames_correlated(
        &b.reverse(),
        3,
        b"read back",
        1,
        2,
        0,
        true,
        Some(&correlation),
    )
    .unwrap();
    assert_eq!(bus.route(1, &reply[0]).unwrap(), 0);
    assert_eq!(bus.route(0, &extra[0]).unwrap(), 1);
}
