# Zenodo successor closure

A semantic repository successor must never remain silently coupled to a predecessor Zenodo candidate.

```text
SOURCE_CHANGED
→ MATERIALIZE_FRESH_CANDIDATE
→ CHECK_EXACT_SOURCE_IDENTITIES
→ AWAIT_EXACT_CANDIDATE_OWNER_AUTHORIZATION
→ PUBLISH
→ FRESH_PUBLIC_RECORD_AND_FILE_READBACK
→ PERSIST_RECEIPT
→ PUBLICATION_EFFECT_ACK_DONE
```

Candidate materialization is automatic for same-repository pull requests. Main fails closed if a registered target reaches Main without a current public receipt for the same exact source bytes. Once a current candidate-specific authorization and publish request exist, publication, public readback and receipt persistence are automatic.

The human authorization boundary remains explicit. Automation must not manufacture an owner authorization or transfer a predecessor authorization to changed bytes.

For every registered source file `p`:

```text
candidate.git_blob(p)
= publish_request.git_blob(p)
= public_receipt.git_blob(p)
= current_repository.git_blob(p)
```

Any mismatch is non-terminal and machine-visible. New publication families must be registered in `policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json`.
