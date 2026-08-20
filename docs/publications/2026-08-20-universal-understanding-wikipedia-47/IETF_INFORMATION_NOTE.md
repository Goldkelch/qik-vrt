# IETF informational relevance note

This note is non-normative context for the existing QIK-VRT Effect Acknowledgement Internet-Draft work. It is not a new Internet-Draft and does not request working-group adoption.

The distributed-systems article distinguishes four kinds of order that may coexist:

`source order != receive order != causal order != effect order`.

For protocol design, the relevant consequence is that a successful transport event does not, by itself, establish the intended application effect. This motivates the separate distinction already used by the QIK-VRT Effect Acknowledgement work:

`TRANSPORT_ACK != EFFECT_ACK`

and the application lifecycle:

`REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`.

This separation is compatible with ordinary forward message transport. A message may arrive out of source order because of variable delay while every individual message still travels from its source toward its receiver. Later provenance can refine an application's reconstructed event history without implying reception before emission or backward signalling.

For IETF discussion, this bundle is therefore relevant as explanatory material about why application-effect acknowledgement must not be inferred from TCP, QUIC, HTTP transport success, or receipt alone. Any normative protocol language remains exclusively in the corresponding Internet-Draft revision and must pass the normal Datatracker/IETF process.

Related repository primary source: `external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml`.

Platform boundary: an Internet-Draft is an individual contribution and is not an RFC, standard, working-group adoption, or IETF consensus.
