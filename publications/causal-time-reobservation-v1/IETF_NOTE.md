# IETF-Oriented Protocol Note Candidate

## Working title

Causal and Evidential State Separation for Effect-Acknowledging Autonomous Systems

## Problem statement

Distributed and autonomous systems frequently conflate message ordering, request acknowledgement, execution, observation, and real-world effect acknowledgement. QIK-VRT treats these as distinct protocol states and adds an explicit causal-binding requirement before sequence is upgraded to causality.

Core invariants:

```text
CAUSALITY != SEQUENCE
TIMESTAMP_ORDER != CAUSAL_ORDER
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
TRANSPORT_ACK != EFFECT_ACK
```

## Protocol relevance

The proposed protocol discipline is that transport success and application/effect success must be represented independently. A causal prerequisite must be explicit when an action depends on a predecessor; chronological order alone is insufficient. Reobservation supplies a distinct post-execution evidence step.

## Experimental implementation

QIK-VRT PR #796 binds the causal-order model to an ANSI-C89/Motorola-68000 path. A dedicated repository-native workflow executed two five-test groups successfully on source head `98d66de02e98d67af81655b028d15fbd60869bbc`, including positive improvement, later-not-better, degraded, and fail-closed witnesses.

## Standards boundary

This file is a candidate input for standards discussion. It is not an Internet-Draft submission, RFC, IETF consensus statement, implementation interoperability claim, or physical-network effect acknowledgement.

Submission status: `PREPARED_NOT_SUBMITTED`.
