"TEMDD v0.1 executable Smalltalk backend vector test."
| required incomplete |
(TEMDDRuntime transitionFor: #unknown state: #hold) = #hold ifFalse: [ self error: 'unknown must HOLD' ].
(TEMDDRuntime transitionFor: #evidence state: #hold) = #continue ifFalse: [ self error: 'evidence must CONTINUE' ].
(TEMDDRuntime transitionFor: #blocker state: #continue) = #successorRequired ifFalse: [ self error: 'blocker must require successor' ].
(TEMDDRuntime transitionFor: #unknown state: #done) = #done ifFalse: [ self error: 'done must remain done' ].
required := #(ZERO_BUGS ALL_PULL_REQUESTS_REGARDED ALL_BRANCHES_REGARDED ALL_PRODUCTIVE_BRANCHES_MERGED FRESH_EXACT_MAIN_VALIDATION_PASS FRESH_EFFECT_READBACK).
(TEMDDRuntime doneForPredicates: required) ifFalse: [ self error: 'complete predicate set must be done' ].
incomplete := required copyWithout: #FRESH_EFFECT_READBACK.
(TEMDDRuntime doneForPredicates: incomplete) ifTrue: [ self error: 'missing effect readback must not be done' ].
Stdio stdout nextPutAll: 'TEMDD_SMALLTALK_EXECUTED vectors=6'; lf.
Smalltalk snapshot: false andQuit: true.
