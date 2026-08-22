# QIK-VRT Mesh Rights and Provenance Audit V1

Status: **HOLD_UNVERIFIED**

This contract binds the two Product-Owner audio instructions recorded on
2026-08-22 without committing raw audio or a verbatim transcript. It turns the
owner's protection and audit requirement into a bounded, executable repository
contract.

## Universal protection rule

QIK-VRT operations must preserve human dignity and human rights, data-protection
and privacy interests, copyright and license interests, independent
verifiability, and procedural fairness. A technical optimization, scaling
operation, repository role or automated classifier may not override those
interests.

The Product Owner names the categorical imperative as a pragmatic ethical
reference when complexity grows. In this contract it remains exactly that:

```text
OWNER_ETHICAL_HEURISTIC != APPLICABLE_LAW
```

It cannot silently replace legislation, jurisdiction, due process, the rights
of affected people, or qualified legal review.

Official source anchors used only for the bounded legal guard are:

- German Basic Law, Articles 1 and 2:
  <https://www.gesetze-im-internet.de/gg/BJNR000010949.html>
- GDPR, Article 5:
  <https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04/eng>
- German Copyright Act, section 97:
  <https://www.gesetze-im-internet.de/urhg/__97.html>

The repository does not claim that every QIK-VRT actor is German state
authority, that German law governs every use, or that these anchors replace the
law applicable to a particular case.

## Authority and Mirror

The technical Mesh hierarchy remains explicit:

```text
AUTHORITY = Goldkelch/qik-vrt
MIRROR    = ingolf-lohmann/qik-vrt
```

Authority has normative policy precedence. Mirror may preserve an exactly equal
tree and independently verify or adopt Authority material, but it may not
silently replace the Authority role. This is a trust and provenance topology,
not a hierarchy of people:

```text
AUTHORITY_ROLE != HUMAN_SUPERIORITY
MIRROR_ROLE != FEWER_HUMAN_RIGHTS
TREE_EQUALITY != ROLE_EQUALITY
REPLICATION != NORMATIVE_OVERRIDE
```

## What the verifier can establish

For an exact evidence envelope, the standard-library verifier checks:

1. repository role;
2. Authority-source binding;
3. exact head and tree identifiers;
4. manifest, license-map and artifact SHA-256 values;
5. repository-relative path safety;
6. an exact declared-license-notice resolution;
7. data-protection guards when personal data are present; and
8. that the requested effect remains read-only verification, an evidence-bound
   alert, or HOLD for review.

A successful decision is:

```text
PROVENANCE_AND_NOTICE_MATCH_VERIFIED
```

It means only that the observed bytes and declared notice match the supplied,
exact expectation under the bound repository role.

## What the verifier cannot establish

The following distinctions are mandatory:

```text
PROVENANCE_MATCH != AUTHORSHIP_PROOF
PROVENANCE_MATCH != LICENSE_COMPLIANCE_IN_ALL_CONTEXTS
DECLARED_NOTICE_MATCH != PROVEN_RIGHTS_CHAIN
LICENSE_MISMATCH != LEGAL_INFRINGEMENT
DETECTED_SIMILARITY != COPYING
AUTOMATED_ALERT != LEGAL_NOTICE
REPOSITORY_RECEIPT != COURT_FINDING
TECHNICAL_AUDIT != DAMAGES_CALCULATION
```

Therefore the verifier always emits false for authorship proved, copying
determined, legal infringement determined, damages determined and court
finding. It performs no external effect.

A possible legal follow-up requires, at minimum, an authorized human/legal
review, the applicable jurisdiction, a proven rights chain and standing, an
identified act and actor, factual and causal evidence, and a lawful,
proportionate remedy basis. No repository test can manufacture those facts.

## Data-protection guard

When personal data are present, all of the following must be bound before the
technical envelope can verify:

```text
lawful_basis_bound
purpose_bound
data_minimized
retention_bound
access_controlled
data_subject_rights_path_bound
```

Unknown personal-data status fails closed. Raw owner audio and verbatim owner
transcripts remain outside ordinary repository content.

## Language and jurisdiction boundary

The second recording contains the number `47`, but automatic recognition does
not resolve whether the owner meant countries or natural-language projections.
The policy preserves the number and the ambiguity without silently rewriting
it:

```text
LANGUAGE_COUNT != COUNTRY_COUNT
MULTILINGUAL_PROJECTION != JURISDICTION
TRANSLATED_NOTICE != UNIVERSAL_ENFORCEABILITY
```

## Reproduction

```bash
python -B tools/qikvrt_mesh_rights_provenance.py --self-check --pretty
python -B -m unittest -v tests.test_qikvrt_mesh_rights_provenance
```

A successful targeted run establishes only internal consistency of this
fail-closed candidate. It does not imply Authority-main effect, independent
review, `PASS`, `FINAL_PASS`, merge, legal enforcement, publication, or
`EFFECT_ACK_DONE`.
