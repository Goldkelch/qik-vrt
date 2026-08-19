import QIKVRTEffectAck.SerializedRemainder

/-!
# Axiom audit for live serialization and remainder theorems

The repository-native test executes this file with the pinned Lake/Lean
runtime and requires every listed theorem to be axiom-free.
-/

#print axioms QIKVRT.EffectAck.Live.V1.mem_activeRemainder_iff
#print axioms QIKVRT.EffectAck.Live.V1.activeRemainder_subset_requirements
#print axioms QIKVRT.EffectAck.Live.V1.closedVerified_not_active
#print axioms QIKVRT.EffectAck.Live.V1.frameConsistent_encode
#print axioms QIKVRT.EffectAck.Live.V1.decode_encode
#print axioms QIKVRT.EffectAck.Live.V1.remainder_encode
#print axioms QIKVRT.EffectAck.Live.V1.wireSequence_not_causalAuthority
#print axioms QIKVRT.EffectAck.Live.V1.wireSequence_not_snapshotAuthority
#print axioms QIKVRT.EffectAck.Live.V1.inconsistentRemainder_rejected
