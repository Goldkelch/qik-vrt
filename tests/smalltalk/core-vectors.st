"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"The C90 oracle exhaustively checks the same 19 flags x 5 decisions."
| output snapshot state |
(QikvrtEffectAck evaluate: nil) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'nil must block' ].
snapshot := QikvrtEffectAck snapshotFromMask: 122879 decision: 2.
(QikvrtEffectAck evaluate: snapshot) = #EFFECT_ACK_DONE
    ifFalse: [ self error: 'Complete snapshot must be DONE' ].
snapshot at: #connection_decision put: 5.
(QikvrtEffectAck evaluate: snapshot) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'Invalid decision must block' ].
snapshot removeKey: #transport_ack.
(QikvrtEffectAck evaluate: snapshot) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'Missing field must block' ].
(QikvrtEffectAck wireCodeFor: #EFFECT_ACK_DONE) = 4
    ifFalse: [ self error: 'Wire DONE must be D4=4' ].
output := 'smalltalk-vectors.bin' asFileReference binaryWriteStream.
[
    0 to: 524287 do: [ :mask |
        snapshot := QikvrtEffectAck snapshotFromMask: mask decision: 0.
        0 to: 4 do: [ :decision |
            snapshot at: #connection_decision put: decision.
            state := QikvrtEffectAck evaluate: snapshot.
            output nextPut: (QikvrtEffectAck coreCodeFor: state) ] ]
] ensure: [ output close ].
Stdio stdout nextPutAll: 'QIKVRT_SMALLTALK_VECTORS=2621440'; lf.
Smalltalk snapshot: false andQuit: true.
