"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"Copyright 2026 Ingolf Lohmann."
"Canonical TEMDD outer main-loop semantics."

Object subclass: #QIKVRTTEMDDMainLoop
    instanceVariableNames: ''
    classVariableNames: ''
    package: 'QIKVRT-TEMDD-MainLoop'!

!QIKVRTTEMDDMainLoop class methodsFor: 'semantics'!
effectAckDoneFor: evidence
    ^ #(compile bind resolve execute test observe readback accept)
        allSatisfy: [ :key | evidence at: key ifAbsent: [ false ] ]
!

runOneOn: runtime subject: subject
    | evidence observed |
    evidence := Dictionary new.
    evidence at: #compile put: (runtime compile: subject).
    evidence at: #bind put: (runtime bind: subject).
    evidence at: #resolve put: (runtime resolve: subject).
    evidence at: #execute put: (runtime execute: subject).
    evidence at: #test put: (runtime test: subject).
    observed := runtime observe: subject.
    evidence at: #observe put: observed first.
    evidence at: #readback put: (runtime readback: observed second).
    evidence at: #accept put: (runtime accept: observed second).
    (self effectAckDoneFor: evidence)
        ifTrue: [ ^ { true. runtime bindSuccessorFrom: subject to: observed second } ].
    ^ { false. subject }
!

runForeverOn: runtime subject: initialSubject
    | current result |
    current := initialSubject.
    [ true ] whileTrue: [
        result := self runOneOn: runtime subject: current.
        result first ifTrue: [ current := result second ] ]
! !
