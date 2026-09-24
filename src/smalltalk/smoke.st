"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
(QikvrtEffectAck evaluate: nil) = #EFFECT_ACK_BLOCK
    ifFalse: [ self error: 'QIKVRT restored image missing kernel' ].
Stdio stdout nextPutAll: 'QIKVRT_SMALLTALK_IMAGE_RESTORED'; lf.
Smalltalk snapshot: false andQuit: true.
