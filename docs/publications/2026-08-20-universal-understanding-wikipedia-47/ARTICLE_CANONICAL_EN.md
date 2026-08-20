# Causal ordering and reconstructable event histories in distributed systems

Distributed systems do not generally possess a single, directly observable global time. Processes advance through local states, messages can experience different delays, and the order in which information is received can differ from the order in which it was produced. This makes it important to distinguish chronology, message delivery, causal dependence, serialization, and externally observed effects.

Leslie Lamport's 1978 "happened-before" relation gave a foundational way to describe causal precedence without assuming a perfectly synchronized global clock. If two events occur successively in one process, or if one event sends a message that another event receives, those relations contribute to a partial order. Logical clocks can be assigned consistently with this order, but the clock values are representations of the ordering constraints rather than a physical universal time. Later work on vector clocks and causal message ordering developed methods for detecting and preserving causal precedence more precisely.

## Send order, receive order, and causal order

Suppose a source produces event A and later event B. If A is transmitted along a slower path and B along a faster path, a receiver can observe B before A. There is no contradiction: the source order and the receive order are different relations.

A system that retains only receive order may lose information about provenance. A system that retains event identity, source order, causal predecessors, observer identity, and local state can instead reconstruct where a late-arriving event belongs within a history constrained by those relations. Such reconstruction does not alter the earlier event and does not imply that information travelled backward in physical time.

This distinction is related to causal delivery and causal consistency. A causally ordered communication system preserves relevant dependency relations even when physical transport delays vary. In modern distributed storage, causal consistency similarly aims to ensure that operations that are causally related are observed in a compatible order, while allowing greater freedom for concurrent operations.

## Partial orders and serialization

A causal structure is often a partial order rather than a total sequence. If A must precede both C and D, while C and D are independent, and E depends on both, then both

`A, C, D, E`

and

`A, D, C, E`

can be valid serializations. They are two topological orderings of the same dependency graph. Consequently, a concrete execution sequence can represent a causal graph without being identical to it.

This distinction is useful in compilers, workflow systems, distributed databases, event sourcing, and provenance systems: implementation requires a concrete execution order, while correctness can depend on a more general dependency relation.

## Local logical time and physical proper time

Distributed systems frequently use local counters, logical clocks, sequence numbers, or process-local state transitions as ordering coordinates. Such coordinates can be described as operational local time, but they should not be confused with relativistic proper time unless a physical worldline and an appropriate measurement or calibration are supplied. The informational statement that one local state follows another is therefore weaker than a physical statement about spacetime.

## From transport to effect

Network and software protocols also distinguish different stages of an action. A request can be sent without being executed; an operation can be executed without its intended external effect being observed; and an observation can exist without a later application-level acknowledgement. Treating these states separately is important in auditing and safety-critical automation.

A useful generic distinction is therefore:

`requested != executed != observed != acknowledged`.

Likewise, a transport acknowledgement establishes facts about communication, not necessarily about the intended application effect.

## Reobservation and reconstructed histories

When new evidence arrives, a system can re-evaluate an earlier interpretation without rewriting history arbitrarily. For example, a late record may reveal a source relation that was previously unknown. The system can preserve the old observation, add the new evidence, and derive a better constrained history. This is a common pattern in event reconciliation, distributed tracing, replicated data systems, and provenance-aware processing.

The resulting history is "reconstructable" in the limited technical sense that the placement of events is justified by retained relations and evidence. It is not a claim that every lost historical fact can be recovered, or that causal relationships can be inferred from timestamps alone.

## Scientific and engineering boundary

These concepts do not imply a physical time machine, reception before emission, backward-running relativistic proper time, or a controllable signal into one's own causal past. They concern representation and preservation of ordering, dependency, provenance, and effect state in information systems.

## References

1. Leslie Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System", *Communications of the ACM* 21(7), 1978. DOI: 10.1145/359545.359563.
2. Friedemann Mattern, "Virtual Time and Global States of Distributed Systems", 1989.
3. Reinhard Schwarz and Friedemann Mattern, "Detecting Causal Relationships in Distributed Computations: In Search of the Holy Grail", *Distributed Computing* 7, 1994. DOI: 10.1007/BF02277859.
4. Bernadette Charron-Bost, Friedemann Mattern, Gerard Tel, "Synchronous, Asynchronous, and Causally Ordered Communication", *Distributed Computing* 9, 1996. DOI: 10.1007/s004460050018.
5. João Freitas et al., "A Survey on the State of the Art of Causally Consistent Cloud Systems", *ACM Computing Surveys* 57, 2025. DOI: 10.1145/3731444.

## QIK-VRT provenance note

The QIK-VRT research repository uses these established distinctions as part of a broader provenance- and effect-oriented architecture. That project-specific implementation is primary-source material and is deliberately separated from the independent literature used for the encyclopedic claims above. It must not be used as evidence of its own encyclopedic notability or scientific consensus.
