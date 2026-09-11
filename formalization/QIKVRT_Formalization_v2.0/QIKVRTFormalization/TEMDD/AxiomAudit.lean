import QIKVRTFormalization.TEMDD.Correctness

/-!
Axiom audit for the TEMDD evidence-bound completion kernel.

The executable witness and the QCE bridge theorem remain within their declared
formal scopes.  This file prints the axiom dependencies of every theorem
introduced by `TEMDD.Correctness`; the exact-head workflow fails closed if any
printed theorem depends on axioms.
-/

#print axioms QIKVRT.TEMDD.DONE_correct
#print axioms QIKVRT.TEMDD.DONE_correct_from_binding
#print axioms QIKVRT.TEMDD.DONE_nonempty_not_vacuous
#print axioms QIKVRT.TEMDD.DONE_rejects_outside_goal
#print axioms QIKVRT.TEMDD.witnessActual_mem_E0
#print axioms QIKVRT.TEMDD.witnessActual_mem_E1
#print axioms QIKVRT.TEMDD.witnessActual_mem_E2
#print axioms QIKVRT.TEMDD.E1_subset_E0
#print axioms QIKVRT.TEMDD.E2_subset_E1
#print axioms QIKVRT.TEMDD.witness_DONE
#print axioms QIKVRT.TEMDD.witness_DONE_correct
#print axioms QIKVRT.TEMDD.qce_certificate_excludes_superdeterministic_candidate
