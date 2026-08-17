# IETF alignment note

This research article is not itself an IETF standards submission. The standards-trackable component is the companion Individual Internet-Draft `draft-lohmann-qikvrt-effect-ack-http-00`.

Normative alignment required by the article:

- causal authorization MUST NOT be inferred solely from message order, wall-clock order, source-text order, transport completion, or HTTP success;
- serialization and parallel execution are projections of explicit causal dependencies;
- new HTTP field values use Structured Fields as specified by RFC 9651;
- effect discovery uses the Web Linking model of RFC 8288;
- HTML discovery is advisory and MUST NOT itself authorize a protected effect;
- Prepare, Commit, Observation, and Effect Acknowledgement remain distinct states;
- unsupported or ambiguously bound effects fail closed.

The article provides explanatory and research context; protocol interoperability requirements belong in the Internet-Draft.
