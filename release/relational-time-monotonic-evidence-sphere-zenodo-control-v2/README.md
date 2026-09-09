# Relational-time Zenodo control carrier v2

This directory preserves the canonical nine-file upload candidate without
reusing the consumed v1 authorization. It is intentionally inert before P7:
there is no workflow, production trigger, publication receipt, remote lock, or
Zenodo client invocation here.

The local finalizer accepts an externally supplied, action-time authorization
only after the input binds the current trusted main head and a P7
reobservation. It requires explicit write mode before it can create the two
production control files that a later, separately reviewed effect carrier may
use.

The frozen candidate stays byte-exact. Neither this staging package nor its
tests publish, reserve a DOI, upload a file, use a token, or write public
publication evidence.
