"TEMDD v0.1 live Smalltalk semantic kernel. Source form is image-independent."
Object subclass: #TEMDDRuntime
    instanceVariableNames: ''
    classVariableNames: ''
    package: 'QIKVRT-TEMDD'!

!TEMDDRuntime class methodsFor: 'semantics'!
transitionFor: event state: state
    "Finite event transition. HOLD/CONTINUE are never NOOP."
    (state = #done) ifTrue: [ ^ #done ].
    (event = #blocker) ifTrue: [ ^ #successorRequired ].
    (event = #evidence) ifTrue: [ ^ #continue ].
    ^ #hold
!
doneForPredicates: predicates
    | required |
    required := #(ZERO_BUGS ALL_PULL_REQUESTS_REGARDED ALL_BRANCHES_REGARDED ALL_PRODUCTIVE_BRANCHES_MERGED FRESH_EXACT_MAIN_VALIDATION_PASS FRESH_EFFECT_READBACK).
    ^ required allSatisfy: [ :each | predicates includes: each ]
! !
