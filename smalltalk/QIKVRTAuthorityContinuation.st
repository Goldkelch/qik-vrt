"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.

Smalltalk-first authority continuation core.
Pure message-driven state transition: no polling, no GitHub mutation, no approval synthesis.
The GitHub carrier supplies an immutable event dictionary and consumes the returned disposition."

Object subclass: #QIKVRTAuthorityContinuation
    instanceVariableNames: 'subjectHead state'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'QIKVRT-ControlPlane'.

QIKVRTAuthorityContinuation class >> forHead: aHead
    ^ self new initializeForHead: aHead

QIKVRTAuthorityContinuation >> initializeForHead: aHead
    subjectHead := aHead.
    state := #waitingProductively.
    ^ self

QIKVRTAuthorityContinuation >> state
    ^ state

QIKVRTAuthorityContinuation >> receive: event
    | eventHead kind reviewState reviewCommit |
    eventHead := event at: #head ifAbsent: [ nil ].
    eventHead = subjectHead ifFalse: [
        state := #stalled.
        ^ Dictionary new
            at: #state put: state;
            at: #reason put: #headDrift;
            yourself ].

    kind := event at: #kind ifAbsent: [ #unknown ].
    kind = #review ifFalse: [
        ^ Dictionary new
            at: #state put: state;
            at: #action put: #observeOnly;
            yourself ].

    reviewState := event at: #reviewState ifAbsent: [ #unknown ].
    reviewCommit := event at: #reviewCommit ifAbsent: [ nil ].
    (reviewState = #approved and: [ reviewCommit = subjectHead ])
        ifTrue: [
            state := #progress.
            ^ Dictionary new
                at: #state put: state;
                at: #action put: #requestFreshExactHeadReobservation;
                yourself ].

    ^ Dictionary new
        at: #state put: state;
        at: #action put: #hold;
        yourself
