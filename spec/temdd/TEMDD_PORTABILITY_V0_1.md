# TEMDD portability v0.1

The canonical interchange boundary is UTF-8 TEMDD source plus canonical JSON IR. A backend is conforming only when it preserves the semantic fields required by `TEMDD_COMPILER_CONTRACT_V0_1.json`. The C90 kernel provides the portable deterministic baseline. M68000 is the fixed-relation low-level target. Smalltalk is the inspectable live-object target. Python is the bootstrap reference frontend. Lean carries proof obligations. Platform-specific transports are adapters outside the semantic kernel.
