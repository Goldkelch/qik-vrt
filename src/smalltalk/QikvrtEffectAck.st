"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"Copyright 2026 Ingolf Lohmann. Verified snapshots, never network authority."
Object subclass: #QikvrtEffectAck
    instanceVariableNames: ''
    classVariableNames: ''
    package: 'QIKVRT-Core'!

!QikvrtEffectAck class methodsFor: 'contract'!
fields
    ^ #(transport_ack input_identifier_available input_digest_valid
        origin_checked context_checked semantics_reconstructed effect_anticipated
        risk_classified risk_known responsibility_assigned responsibility_owner_present
        connection_decided policy_allows_release deadline_exceeded no_open_questions
        no_next_required_checks required_evidence_present predecessor_invalid integrity_failure)
!
stateNames
    ^ #(EFFECT_NACK EFFECT_ACK_CONTINUE EFFECT_ACK_DONE EFFECT_ACK_ISOLATE EFFECT_ACK_BLOCK)
!
evaluate: snapshot
    "Preserve the C90 verified-snapshot first-match order. Malformed snapshots block."
    | decision complete |
    (snapshot isKindOf: Dictionary) ifFalse: [ ^ #EFFECT_ACK_BLOCK ].
    (self fields allSatisfy: [ :key |
        (snapshot includesKey: key) and: [
            (snapshot at: key) == true or: [ (snapshot at: key) == false ] ] ])
        ifFalse: [ ^ #EFFECT_ACK_BLOCK ].
    decision := snapshot at: #connection_decision ifAbsent: [ ^ #EFFECT_ACK_BLOCK ].
    (decision isInteger and: [ decision between: 0 and: 4 ])
        ifFalse: [ ^ #EFFECT_ACK_BLOCK ].
    (snapshot at: #predecessor_invalid) ifTrue: [ ^ #EFFECT_ACK_BLOCK ].
    (snapshot at: #deadline_exceeded) ifTrue: [ ^ #EFFECT_ACK_BLOCK ].
    ((snapshot at: #input_identifier_available) and: [ snapshot at: #input_digest_valid ])
        ifFalse: [ ^ #EFFECT_NACK ].
    (snapshot at: #integrity_failure) ifTrue: [ ^ #EFFECT_ACK_BLOCK ].
    decision = 4 ifTrue: [ ^ #EFFECT_ACK_BLOCK ].
    decision = 3 ifTrue: [ ^ #EFFECT_ACK_ISOLATE ].
    decision = 2 ifFalse: [ ^ #EFFECT_ACK_CONTINUE ].
    complete := #(transport_ack input_digest_valid origin_checked context_checked
        semantics_reconstructed effect_anticipated risk_classified risk_known
        responsibility_assigned responsibility_owner_present connection_decided
        policy_allows_release no_open_questions no_next_required_checks required_evidence_present)
        allSatisfy: [ :key | snapshot at: key ].
    ^ complete ifTrue: [ #EFFECT_ACK_DONE ] ifFalse: [ #EFFECT_ACK_CONTINUE ]
!
snapshotFromMask: mask decision: decision
    | snapshot |
    (mask isInteger and: [ mask between: 0 and: 524287 ])
        ifFalse: [ self error: 'Snapshot mask outside 19-bit contract' ].
    snapshot := Dictionary new.
    self fields withIndexDo: [ :key :index |
        snapshot at: key put: (mask bitAt: index) = 1 ].
    snapshot at: #connection_decision put: decision.
    ^ snapshot
!
coreCodeFor: state
    ^ (self stateNames indexOf: state ifAbsent: [ ^ 4 ]) - 1
!
wireCodeFor: state
    "D4 wire codes differ from the C enum. Never transmit the C index directly."
    ^ #(0 1 4 2 3) at: (self coreCodeFor: state) + 1
!
ordinaryRelease: state
    ^ state = #EFFECT_ACK_DONE
! !
