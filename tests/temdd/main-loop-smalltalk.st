"TEMDD Main Loop V1 executable Smalltalk checks."
| complete partial |
complete := Dictionary new.
#(compile bind resolve execute test observe readback accept)
    do: [ :key | complete at: key put: true ].
(QIKVRTTEMDDMainLoop effectAckDoneFor: complete)
    ifFalse: [ self error: 'all eight stages must close the subject' ].
#(compile bind resolve execute test observe readback accept) do: [ :missing |
    partial := complete copy.
    partial at: missing put: false.
    (QIKVRTTEMDDMainLoop effectAckDoneFor: partial)
        ifTrue: [ self error: 'single missing stage must block DONE' ] ].
Stdio stdout nextPutAll: 'TEMDD_MAIN_LOOP_SMALLTALK_EXECUTED vectors=9'; lf.
