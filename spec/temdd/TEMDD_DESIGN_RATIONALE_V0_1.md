# TEMDD design rationale v0.1

TEMDD minimizes semantic distance between specification and execution. Evidence, authority, effects, readback, holds and successors are language concepts because treating them as comments or workflow conventions caused divergent implementations. The kernel is intentionally finite and event-driven; persistence and scheduling belong to adapters. Exact-subject typing prevents accidental evidence transfer. Successor-based learning makes self-improvement testable. Multiple backends provide portability and differential checking without multiplying normative semantics.
