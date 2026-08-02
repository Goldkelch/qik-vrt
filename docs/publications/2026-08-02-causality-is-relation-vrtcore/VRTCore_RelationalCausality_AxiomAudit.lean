import VRTCore_RelationalCausality_Candidate

/-!
# QIK-VRT VRTCore axiom audit

This file asks Lean 4.19 to print the axiom dependencies of every theorem in
the byte-bound relational-causality candidate.  The publication gate accepts
only an empty dependency set or the explicitly disclosed Lean foundational
axiom `propext`; project-defined axioms are rejected.
-/

#print axioms QIKVRT.VRTCore.epistemicKindExhaustive
#print axioms QIKVRT.VRTCore.formalAndEmpiricalAreDistinct
#print axioms QIKVRT.VRTCore.interpretiveAndUnresolvedAreDistinct
#print axioms QIKVRT.VRTCore.observedSequenceHasNoBridge
#print axioms QIKVRT.VRTCore.bridgedRelationHasBridge
#print axioms QIKVRT.VRTCore.observedSequenceAloneIsNotCausality
#print axioms QIKVRT.VRTCore.bridgedRelationIsStructurallyLicensed
#print axioms QIKVRT.VRTCore.causalLicenseRequiresBridge
#print axioms QIKVRT.VRTCore.successfulReceiptIsTechnicallySuccessful
#print axioms QIKVRT.VRTCore.withheldAuthorizationIsFalse
#print axioms QIKVRT.VRTCore.grantedAuthorizationIsTrue
#print axioms QIKVRT.VRTCore.withheldAuthorizationBlocksAnyReceipt
#print axioms QIKVRT.VRTCore.successfulReceiptStillBlockedWithoutAuthority
#print axioms QIKVRT.VRTCore.memAppendLeft
#print axioms QIKVRT.VRTCore.mergePreserves
#print axioms QIKVRT.VRTCore.extendsRefl
#print axioms QIKVRT.VRTCore.extendsTrans
#print axioms QIKVRT.VRTCore.seedMaterializes
#print axioms QIKVRT.VRTCore.recursiveStepPreserves
#print axioms QIKVRT.VRTCore.suppliedStableMinkowskiWitnessIsAdmissible
#print axioms QIKVRT.VRTCore.missingMinkowskiWitnessIsRejected
