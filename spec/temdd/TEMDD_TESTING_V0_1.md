# TEMDD testing strategy v0.1

Language changes require: parser unit tests; positive and negative corpus vectors; semantic invariant tests T01-T12; C90 differential vectors; backend-specific executable gates as those runtimes become admitted; formal obligations for invariants that are represented in Lean; repository integrity; and exact-subject CI. Tests must include failure cases because fail-closed behavior is part of the language semantics. A green transport/build job cannot substitute for semantic or effect readback.
