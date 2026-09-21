"Independent Smalltalk carrier for QIK-VRT core invariant v1."
Object subclass: #QIKVRTCoreInvariant instanceVariableNames: '' classVariableNames: '' package: 'QIKVRT-CoreInvariant'!
!QIKVRTCoreInvariant class methodsFor: 'semantics'!
decideTransport: t block: b isolate: i releaseReady: r
    t ifFalse: [ ^ 0 ].
    b ifTrue: [ ^ 4 ].
    i ifTrue: [ ^ 3 ].
    r ifTrue: [ ^ 2 ].
    ^ 1
!
ordinaryReleaseFor: s
    ^ s = 2
! !
#(false true) do: [ :t | #(false true) do: [ :b | #(false true) do: [ :i | #(false true) do: [ :r | | s |
    s := QIKVRTCoreInvariant decideTransport: t block: b isolate: i releaseReady: r.
    Stdio stdout
      nextPutAll: ((t ifTrue: [1] ifFalse: [0]) printString); nextPutAll: ' ';
      nextPutAll: ((b ifTrue: [1] ifFalse: [0]) printString); nextPutAll: ' ';
      nextPutAll: ((i ifTrue: [1] ifFalse: [0]) printString); nextPutAll: ' ';
      nextPutAll: ((r ifTrue: [1] ifFalse: [0]) printString); nextPutAll: ' ';
      nextPutAll: s printString; nextPutAll: ' ';
      nextPutAll: ((QIKVRTCoreInvariant ordinaryReleaseFor: s) ifTrue: [1] ifFalse: [0]) printString; lf ] ] ] ].
Smalltalk snapshot: false andQuit: true.
