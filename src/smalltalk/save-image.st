"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"Only the pure verified-snapshot kernel enters this reproducible image."
(QikvrtEffectAck evaluate: nil) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'QIKVRT kernel self-test failed' ].
Smalltalk snapshot: true andQuit: true.
