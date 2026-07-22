import QIKVRTFormalization.Retrocausality

/-!
# Epistemic claim ledger

This executable data layer prevents category collapse.  In particular,
interpretive, ontological, normative, and empirically open claims cannot be
encoded as `proved` by the compatibility predicate.
-/

namespace QIKVRT

public inductive ClaimKind where
  | mathematicalTheorem
  | modelDefinition
  | modelTheorem
  | correspondenceHypothesis
  | empiricalClaim
  | interpretation
  | causalClaim
  | ontologicalInterpretation
  | normativeConclusion
deriving DecidableEq, Repr, BEq

public inductive ClaimStatus where
  | proved
  | provedConditional
  | defined
  | refutedInModel
  | establishedBackground
  | openEmpirical
  | unsupported
  | interpretive
  | normative
  | falseInGeneral
deriving DecidableEq, Repr, BEq

@[expose] public def compatible : ClaimKind → ClaimStatus → Bool
  | .mathematicalTheorem, .proved => true
  | .mathematicalTheorem, .falseInGeneral => true
  | .modelDefinition, .defined => true
  | .modelTheorem, .proved => true
  | .modelTheorem, .provedConditional => true
  | .modelTheorem, .refutedInModel => true
  | .correspondenceHypothesis, .openEmpirical => true
  | .correspondenceHypothesis, .unsupported => true
  | .empiricalClaim, .establishedBackground => true
  | .empiricalClaim, .openEmpirical => true
  | .empiricalClaim, .unsupported => true
  | .interpretation, .interpretive => true
  | .causalClaim, .provedConditional => true
  | .causalClaim, .openEmpirical => true
  | .causalClaim, .unsupported => true
  | .causalClaim, .refutedInModel => true
  | .ontologicalInterpretation, .interpretive => true
  | .normativeConclusion, .normative => true
  | _, _ => false

public structure Claim where
  id : String
  kind : ClaimKind
  status : ClaimStatus
  statement : String
deriving Repr

@[expose] public def coreClaims : List Claim := [
  ⟨"SET-001", .mathematicalTheorem, .proved,
   "A class and its relative complement form a disjoint partition."⟩,
  ⟨"MAP-001", .mathematicalTheorem, .proved,
   "A total correspondence map pulls the partition back to its domain."⟩,
  ⟨"ESC-001", .modelTheorem, .provedConditional,
   "Finite escape certificates exhaust the complement under a sound-complete escape specification."⟩,
  ⟨"GATE-001", .modelTheorem, .provedConditional,
   "PASS and BLOCK are sound when certificates carry soundness proofs."⟩,
  ⟨"GATE-002", .mathematicalTheorem, .proved,
   "A deterministic factor gate exists on an image exactly under fiber constancy."⟩,
  ⟨"QUANT-001", .mathematicalTheorem, .proved,
   "Arbitrarily fine finite representation does not imply ontic finite resolution."⟩,
  ⟨"PHYS-001", .correspondenceHypothesis, .openEmpirical,
   "A Mandelbrot correspondence describes physical spacetime."⟩,
  ⟨"PHYS-002", .empiricalClaim, .openEmpirical,
   "Spacetime is fundamentally discrete at the Planck scale."⟩,
  ⟨"RETRO-001", .modelTheorem, .refutedInModel,
   "The autonomous QIK-VRT/Mandelbrot process contains a backward state channel."⟩,
  ⟨"RETRO-002", .causalClaim, .openEmpirical,
   "A freely controllable later intervention changes an earlier observable."⟩,
  ⟨"ONTO-001", .ontologicalInterpretation, .interpretive,
   "Difference is a universal structural creation principle."⟩,
  ⟨"ETH-001", .normativeConclusion, .normative,
   "Technology should be developed for peaceful and responsibility-preserving use."⟩
]

@[expose] public def claimValid (c : Claim) : Bool :=
  compatible c.kind c.status

public theorem coreClaimsCompatible : coreClaims.all claimValid = true := by rfl

public theorem interpretationCannotBeProved :
    compatible ClaimKind.interpretation ClaimStatus.proved = false := rfl

public theorem ontologyCannotBeProvedByStatusCollapse :
    compatible ClaimKind.ontologicalInterpretation ClaimStatus.proved = false := rfl

public theorem normativeCannotBeProvedByStatusCollapse :
    compatible ClaimKind.normativeConclusion ClaimStatus.proved = false := rfl

end QIKVRT
