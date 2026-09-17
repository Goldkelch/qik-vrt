"QIK-VRT IDE Smalltalk perspective V1 — deterministic, side-effect-free receipt projection."
Object subclass: #QIKVRTIDEPerspective
    instanceVariableNames: ''
    classVariableNames: ''
    poolDictionaries: ''
    category: 'QIKVRT-IDE'.

QIKVRTIDEPerspective class >> language [ ^ 'smalltalk' ]
QIKVRTIDEPerspective class >> role [ ^ 'object_event_reflective_system' ]
QIKVRTIDEPerspective class >> operations [ ^ #('observe' 'inspect' 'reflect' 'adapt' 'test' 'receipt') ]
QIKVRTIDEPerspective class >> effectBoundary [ ^ 'CANDIDATE_ONLY' ]
QIKVRTIDEPerspective class >> predecessorEvidenceTransfer [ ^ false ]
QIKVRTIDEPerspective class >> receiptForHead: head tree: tree inputDigest: inputDigest contractDigest: contractDigest [
  ^ Dictionary new
    at: 'schema' put: 'QIKVRT_IDE_PERSPECTIVE_RECEIPT_V1';
    at: 'language' put: self language;
    at: 'head_sha' put: head;
    at: 'tree_sha' put: tree;
    at: 'input_sha256' put: inputDigest;
    at: 'contract_sha256' put: contractDigest;
    at: 'assertions' put: #('smalltalk_object_model_executes' 'subject_bound');
    at: 'counterexamples' put: #();
    at: 'effect_boundary' put: self effectBoundary;
    at: 'predecessor_evidence_transfer' put: self predecessorEvidenceTransfer;
    yourself
]
