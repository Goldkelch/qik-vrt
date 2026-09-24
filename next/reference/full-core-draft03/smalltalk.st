"Independent Draft03 finite snapshot and consumer semantics."
Object subclass: #QIKVRTFullDraft03 instanceVariableNames: '' classVariableNames: '' package: 'QIKVRT-FullDraft03'!
!QIKVRTFullDraft03 class methodsFor: 'semantics'!
stateFor: mask risk: risk decision: decision
    (risk >= 5 or: [ decision >= 5 ]) ifTrue: [ ^ 5 ].
    ((mask bitAnd: 16r10000) ~= 0) ifTrue: [ ^ 4 ].
    ((mask bitAnd: 16r1000) ~= 0) ifTrue: [ ^ 4 ].
    ((mask bitAnd: 6) = 6) ifFalse: [ ^ 0 ].
    ((mask bitAnd: 16r20000) ~= 0) ifTrue: [ ^ 4 ].
    decision = 4 ifTrue: [ ^ 4 ].
    decision = 3 ifTrue: [ ^ 3 ].
    ((decision = 2 and: [ risk > 0 ]) and: [ (mask bitAnd: 16rEFFF) = 16rEFFF ])
        ifTrue: [ ^ 2 ].
    ^ 1
!
admitDerived: derived declared: declared validators: validators
    ^ (derived = 2 and: [ declared = 2 and: [ validators = 511 ] ])
        ifTrue: [ 1 ] ifFalse: [ 0 ]
! !
| output |
output := WriteStream on: (String new: 9455616).
0 to: 262143 do: [ :mask |
    0 to: 5 do: [ :risk |
        0 to: 5 do: [ :decision |
            output nextPut: (Character value: 48 +
                (QIKVRTFullDraft03 stateFor: mask risk: risk decision: decision)) ] ] ].
0 to: 5 do: [ :derived |
    0 to: 5 do: [ :declared |
        0 to: 511 do: [ :validators |
            output nextPut: (Character value: 48 +
                (QIKVRTFullDraft03 admitDerived: derived declared: declared validators: validators)) ] ] ].
'full-smalltalk.out' asFileReference writeStreamDo: [ :stream | stream nextPutAll: output contents ].
Smalltalk snapshot: false andQuit: true.
