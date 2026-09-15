# TEMDD control-plane migration

Existing Python/YAML mechanisms are not deleted wholesale. Each control relation is migrated only after the TEMDD representation passes the same event vectors plus stricter negative vectors. The sequence is observe existing behavior, encode TEMDD relation, differential test, deploy candidate, read back, then retire only the proven-redundant predecessor. Until equivalence is demonstrated, the predecessor remains authoritative for its admitted scope. This prevents a language bootstrap from weakening a mature fail-closed control plane.
