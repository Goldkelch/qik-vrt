# Completion plan — QIK-VRT manuscript formalization v2.0

Status: ACTIVE
Authority repository: `Goldkelch/qik-vrt`
Base tree: `a09cbdcbcc6c64975a06f2ddd92264547bc31ee0`
Responsible human: Ingolf Lohmann

## Objective

Close every remaining formal obligation of the locked 62-page manuscript without weakening source binding, claim boundaries, axiom policy, or epistemic classification.

Completion does not mean converting empirical, interpretive, or normative statements into mathematical theorems. It means that every formal environment is source-bound and each theorem-like statement is either kernel-checked with explicit assumptions or retained as an explicit, justified non-theorem obligation.

## Locked source

- TeX SHA-256: `c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf`
- PDF SHA-256: `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`
- Physical PDF pages: 62

## Remaining theorem tranches

### T1 — Escape-time reconstruction
Claims: `ESC-004`, `ESC-005`, `ESC-003`

### T2 — Finite epsilon quantization
Claims: `QUA-004`, `QUA-005`, `QUA-003`

### T3 — Trajectory and boundary classification
Claims: `GAT-003`, `GAT-007`

### T4 — Dimensional and Lorentz claims
Claims: `DIM-006`, `DIM-007`

## Definition tranche
Claims: `DEF-001` through `DEF-020`

Each definition node must receive an exact TeX source span and source hash, a Lean declaration or a justified non-Lean schema binding, explicit type/domain/codomain/preconditions, dependency edges in the claim graph, generated proof-map projection, and validation tests preventing orphaned or circular bindings.

## Non-regression gates

- full Lean 4.19.0 `lake build`;
- no project axioms, `sorry`, `admit`, unchecked `constant`, or proof escape;
- unified `#print axioms` audit;
- deterministic inventory, claim graph, proof map, and verification report regeneration;
- positive and negative source-binding tests;
- repository `make test`;
- repository integrity regeneration;
- identical verified content tree in both canonical repositories before final promotion.

## Completion boundary

The manuscript reaches formalization completion only when no theorem or definition node remains `PENDING`, all conditional assumptions are explicit in the Lean types or machine-readable bindings, and all generated evidence agrees.
