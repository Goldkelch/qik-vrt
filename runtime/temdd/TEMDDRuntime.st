"TEMDD v0.1 live Smalltalk semantic kernel. Source form is intentionally image-independent."
Object subclass: #TEMDDRuntime
    instanceVariableNames: ''
    classVariableNames: ''
    poolDictionaries: ''
    category: 'QIKVRT-TEMDD'.

TEMDDRuntime class >> transitionFor: event state: state
    "Finite event transition. HOLD/CONTINUE are never NOOP."
    (state = #done) ifTrue: [ ^ #done ].
    (event = #blocker) ifTrue: [ ^ #successorRequired ].
    (event = #evidence) ifTrue: [ ^ #continue ].
    ^ #hold.

TEMDDRuntime class >> doneForPredicates: predicates
    | required |
    required := #(ZERO_BUGS ALL_PULL_REQUESTS_REGARDED ALL_BRANCHES_REGARDED ALL_PRODUCTIVE_BRANCHES_MERGED FRESH_EXACT_MAIN_VALIDATION_PASS FRESH_EFFECT_READBACK).
    ^ required allSatisfy: [ :each | predicates includes: each ].
