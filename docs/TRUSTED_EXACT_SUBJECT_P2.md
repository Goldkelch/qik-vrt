# Trusted exact-subject P2

This infrastructure closes the bootstrap gap where a candidate requires fresh P2 validation but cannot rely on a validator introduced by that same candidate.

The trusted carrier accepts an exact pull-request number and expected head SHA, independently reads the current pull-request head, requires equality, checks out that exact SHA, rechecks the local commit identity, and then executes repository integrity verification, the complete repository test gate, and integrity verification again.

The carrier is read-only. It does not mutate the candidate, submit a review, mutate Main, transfer predecessor evidence, or claim an external effect. A successful workflow run is P2 evidence only when the exact-subject binding and all P2 steps actually execute successfully. Any mismatch or gate failure is a concrete fail, never a successful no-op.
