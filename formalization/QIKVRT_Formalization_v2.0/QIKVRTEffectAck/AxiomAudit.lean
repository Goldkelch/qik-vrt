import QIKVRTEffectAck.Claims

/-!
# EFFECT_ACK kernel axiom inventory

This generated list covers every proof and registry constant referenced by
the Draft-01 claim matrix, plus both claim-ID inventory theorems.  The
external audit enforces the exact constant-specific axiom sets declared in
the matrix.  `propext` is used by several simplifier-produced proofs;
semantic factorization additionally uses the explicitly declared classical
foundations.  No project-specific axiom is admitted.
-/

#print axioms QIKVRT.EffectAck.V1.Claims.CollapsedDecoderCounterexample
#print axioms QIKVRT.EffectAck.V1.Claims.CompleteMediation
#print axioms QIKVRT.EffectAck.V1.Claims.ConditionalPhysicalBridge
#print axioms QIKVRT.EffectAck.V1.Claims.DoneSelection
#print axioms QIKVRT.EffectAck.V1.Claims.InversionBoundary
#print axioms QIKVRT.EffectAck.V1.Claims.ReleaseSafety
#print axioms QIKVRT.EffectAck.V1.Claims.SemanticBoundary
#print axioms QIKVRT.EffectAck.V1.Claims.StateSpace
#print axioms QIKVRT.EffectAck.V1.Claims.claimIds_count
#print axioms QIKVRT.EffectAck.V1.Claims.claimIds_pairwise
#print axioms QIKVRT.EffectAck.V1.authorized_implies_consumer_checks
#print axioms QIKVRT.EffectAck.V1.authorized_implies_recorded_and_recomputed_done
#print axioms QIKVRT.EffectAck.V1.completelyMediated_execution_implies_done
#print axioms QIKVRT.EffectAck.V1.connectionDecisions_complete
#print axioms QIKVRT.EffectAck.V1.connectionDecisions_count
#print axioms QIKVRT.EffectAck.V1.connectionDecisions_pairwise
#print axioms QIKVRT.EffectAck.V1.coreDone_eq_true_iff
#print axioms QIKVRT.EffectAck.V1.deadlineExceeded_blocks
#print axioms QIKVRT.EffectAck.V1.exactHistoricalReconstruction_implies_injective
#print axioms QIKVRT.EffectAck.V1.explicitBlock_precedes_later_outcomes
#print axioms QIKVRT.EffectAck.V1.explicitIsolate_precedes_done
#print axioms QIKVRT.EffectAck.V1.integrityFailure_blocks
#print axioms QIKVRT.EffectAck.V1.missingEffectCheckableReception_nacks
#print axioms QIKVRT.EffectAck.V1.noExactDecoder_forCollapsedObservation
#print axioms QIKVRT.EffectAck.V1.nonDone_record_never_authorized
#print axioms QIKVRT.EffectAck.V1.physicalOccurrence_implies_authorized_done_conditionally
#print axioms QIKVRT.EffectAck.V1.predecessorInvalid_blocks
#print axioms QIKVRT.EffectAck.V1.selectState_eq_done_iff
#print axioms QIKVRT.EffectAck.V1.semanticReconstruction_iff_fiberConstant
#print axioms QIKVRT.EffectAck.V1.stale_record_never_authorized
#print axioms QIKVRT.EffectAck.V1.states_complete
#print axioms QIKVRT.EffectAck.V1.states_count
#print axioms QIKVRT.EffectAck.V1.states_pairwise
#print axioms QIKVRT.EffectAck.V1.transportAck_is_not_effectAuthorization
