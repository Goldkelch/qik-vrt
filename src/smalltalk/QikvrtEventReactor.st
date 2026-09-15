"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"Copyright 2026 Ingolf Lohmann. Local causal delivery, never remote authority."
Object subclass: #QikvrtEventReactor
    instanceVariableNames: 'repository subject events pending delivered'
    classVariableNames: ''
    package: 'QIKVRT-Core'!

!QikvrtEventReactor methodsFor: 'initialization'!
bindRepository: aRepository subject: aSubject
    (aRepository isString and: [ aRepository = 'Goldkelch/qik-vrt'
        or: [ aRepository = 'ingolf-lohmann/qik-vrt' ] ])
        ifFalse: [ self error: 'INVALID_REPOSITORY' ].
    (aSubject isKindOf: Dictionary) ifFalse: [ self error: 'INVALID_SUBJECT' ].
    (#('pull_request' 'trusted_main' 'repository' 'external_delivery')
        includes: (aSubject at: 'kind' ifAbsent: [ nil ]))
        ifFalse: [ self error: 'INVALID_SUBJECT_KIND' ].
    (aSubject at: 'kind') = 'pull_request' ifTrue: [
        ((aSubject at: 'pull_request' ifAbsent: [ nil ]) isInteger and: [
            (aSubject at: 'pull_request') > 0 ])
            ifFalse: [ self error: 'INVALID_PULL_REQUEST' ] ].
    #('head_sha' 'tree_sha' 'base_sha') do: [ :key |
        (self isSha: (aSubject at: key ifAbsent: [ nil ]))
            ifFalse: [ self error: 'UNBOUND_SUBJECT' ] ].
    repository := aRepository copy.
    subject := aSubject deepCopy.
    events := Dictionary new.
    pending := Dictionary new.
    delivered := Set new.
    ^ self
!
isSha: value
    ^ value isString and: [ value size = 40 and: [
        value allSatisfy: [ :char | '0123456789abcdef' includes: char ] ] ]
!
isIdentifier: value
    ^ value isString and: [ (value size between: 1 and: 256) and: [
        value allSatisfy: [ :char | char asciiValue >= 32 ] ] ]
! !

!QikvrtEventReactor methodsFor: 'validation'!
validate: event
    | predecessors id |
    (event isKindOf: Dictionary) ifFalse: [ self error: 'INVALID_EVENT' ].
    (event at: 'schema' ifAbsent: [ nil ]) = 'qikvrt_live_event_v1'
        ifFalse: [ self error: 'INVALID_EVENT_SCHEMA' ].
    ((event at: 'repository' ifAbsent: [ nil ]) = repository and: [
        (event at: 'subject' ifAbsent: [ nil ]) = subject ])
        ifFalse: [ self error: 'EXACT_SUBJECT_MISMATCH' ].
    id := event at: 'event_id' ifAbsent: [ nil ].
    (self isIdentifier: id) ifFalse: [ self error: 'INVALID_EVENT_ID' ].
    (#('P0' 'P1' 'P2' 'P3' 'P4' 'P5' 'P6' 'P7' 'EXTERNAL')
        includes: (event at: 'phase' ifAbsent: [ nil ]))
        ifFalse: [ self error: 'INVALID_PHASE' ].
    ((event at: 'd0' ifAbsent: [ nil ]) isInteger and: [
        (event at: 'd0') between: 0 and: 3 ])
        ifFalse: [ self error: 'INVALID_D0' ].
    predecessors := event at: 'predecessor_event_ids' ifAbsent: [ nil ].
    (predecessors isArray and: [ predecessors size <= 64 ])
        ifFalse: [ self error: 'INVALID_PREDECESSORS' ].
    ((predecessors allSatisfy: [ :each | self isIdentifier: each ]) and: [
        predecessors asSet size = predecessors size ])
        ifFalse: [ self error: 'INVALID_PREDECESSORS' ].
    (predecessors includes: id) ifTrue: [ self error: 'CAUSAL_CYCLE' ].
    ((event at: 'payload' ifAbsent: [ nil ]) isKindOf: Dictionary)
        ifFalse: [ self error: 'INVALID_PAYLOAD' ].
    ^ event
!
wouldCycle: event
    | todo visited id |
    id := event at: 'event_id'.
    todo := (event at: 'predecessor_event_ids') asOrderedCollection.
    visited := Set new.
    [ todo isEmpty ] whileFalse: [
        | current |
        current := todo removeLast.
        current = id ifTrue: [ ^ true ].
        (visited includes: current) ifFalse: [
            visited add: current.
            events at: current ifPresent: [ :parent |
                todo addAll: (parent at: 'predecessor_event_ids') ] ] ].
    ^ false
! !

!QikvrtEventReactor methodsFor: 'event delivery'!
accept: rawEvent
    | event id result old ready |
    event := (self validate: rawEvent) deepCopy.
    id := event at: 'event_id'.
    old := events at: id ifAbsent: [ nil ].
    old ifNotNil: [
        old = event ifFalse: [ self error: 'EVENT_ID_REBOUND' ].
        ^ Dictionary newFrom: { 'status' -> 'DUPLICATE'. 'completions' -> #() } ].
    events size >= 10000 ifTrue: [ self error: 'EVENT_CAPACITY_REACHED' ].
    (self wouldCycle: event) ifTrue: [ self error: 'CAUSAL_CYCLE' ].
    events at: id put: event.
    pending at: id put: event.
    result := OrderedCollection new.
    [
        ready := (pending keys select: [ :key |
            ((pending at: key) at: 'predecessor_event_ids')
                allSatisfy: [ :predecessor | delivered includes: predecessor ] ]) sorted.
        ready isEmpty
    ] whileFalse: [
        ready do: [ :key |
            result add: (self continuationFor: (pending at: key)).
            delivered add: key.
            pending removeKey: key ] ].
    ^ Dictionary newFrom: { 'status' -> 'ACCEPTED'.
        'pending' -> pending size. 'completions' -> result asArray }
!
continuationFor: event
    "Closed handler: classify an exact event and optionally execute the pure
    verified-snapshot kernel. Never evaluate supplied code or invoke GitHub.
    Delivered predecessors prove message causality, not successful P0-P7 gates."
    | result payload snapshot state |
    result := Dictionary newFrom: {
        'schema' -> 'qikvrt_smalltalk_event_continuation_v1'.
        'event_id' -> (event at: 'event_id').
        'repository' -> repository. 'subject' -> subject deepCopy.
        'phase' -> (event at: 'phase').
        'predecessor_event_ids' -> (event at: 'predecessor_event_ids') copy.
        'next_action' -> (#('NOOP' 'HOLD' 'REOBSERVE' 'REQUEST_AUTHORITY') at: (event at: 'd0') + 1).
        'phase_satisfied' -> false. 'ordinary_release' -> false.
        'external_effect' -> 'NONE'. 'effect_ack_done' -> false }.
    payload := event at: 'payload'.
    payload at: 'verified_snapshot' ifPresent: [ :raw |
        snapshot := nil.
        (raw isKindOf: Dictionary) ifTrue: [
            snapshot := Dictionary new.
            QikvrtEffectAck fields do: [ :key |
                raw at: key asString ifPresent: [ :value | snapshot at: key put: value ] ].
            raw at: 'connection_decision' ifPresent: [ :value |
                snapshot at: #connection_decision put: value ] ].
        state := QikvrtEffectAck evaluate: snapshot.
        result at: 'snapshot_kernel_state' put: state asString.
        result at: 'snapshot_kernel_scope' put: 'CALLER_SUPPLIED_VERIFIED_FACTS_ONLY'.
        result at: 'snapshot_d4' put: (QikvrtEffectAck wireCodeFor: state) ].
    ^ result
! !
