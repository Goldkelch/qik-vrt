import QIKVRTFormalization.Claims.Batch02Factorization

/-!
Kernel axiom inventory for GAT-002.  The forward direction has no axiom
dependency.  The converse and combined theorem use Lean's standard
`Classical.choice` (image representatives) and `Quot.sound` (function
extensionality), with no project-specific axiom.
-/

#print axioms QIKVRT.V2.factorization_implies_fiberConstant
#print axioms QIKVRT.V2.fiberConstant_implies_factorization
#print axioms QIKVRT.V2.GAT002_checked
#print axioms QIKVRT.V2.Claims.GAT002
