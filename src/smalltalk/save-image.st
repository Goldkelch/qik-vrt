"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"The pure kernel and causal event scheduler enter the source-bound image."
(QikvrtEffectAck evaluate: nil) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'QIKVRT kernel self-test failed' ].
(Smalltalk globals includesKey: #QikvrtEventReactor)
    ifFalse: [ self error: 'QIKVRT event reactor missing' ].
Smalltalk snapshot: true andQuit: true.
