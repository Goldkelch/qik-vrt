# IED correspondence templates

Work unit: `IED-DISSEMINATION-2026-08-21-V1`

All templates below are `DRAFT_TEMPLATE_ONLY`. They contain no resolved recipient and have not been sent.

```text
EMAIL_DRAFTED != EMAIL_SENT
EMAIL_SENT != EMAIL_RECEIVED
EMAIL_RECEIVED != EMAIL_RESPONDED
```

Replace every bracketed field before creating a recipient-bound draft.

## 1. Independent technical review request

**Subject:** Review request: IED — Intelligence, Evidence, Development

Dear [NAME],

I am requesting an independent technical review of the attached or linked IED source bundle.

Exact artifact:
- repository: `Goldkelch/qik-vrt`
- pull request: [PR]
- head: [40-HEX HEAD]
- tree: [40-HEX TREE]
- bundle checksum: [SHA-256]

Requested action:
- inspect the distinction between authored thesis, repository implementation, formal theorem, empirical observation, and external publication;
- identify overclaims, missing related work, reproducibility gaps, or ambiguous terminology;
- return comments without implying acceptance or institutional endorsement.

The bundle does not claim peer review, DOI publication, arXiv announcement, IETF consensus, Wikipedia acceptance, IEEE acceptance, or `EFFECT_ACK_DONE`.

Kind regards,  
Ingolf Lohmann

## 2. IETF discussion or submission-routing inquiry

**Subject:** Routing inquiry for Effect-Acknowledgement interoperability material

Dear [IETF CONTACT / WORKING GROUP CONTACT],

I am seeking guidance on the appropriate IETF discussion or submission route for a narrowly scoped Effect-Acknowledgement interoperability document.

Exact candidate:
- draft name/revision: [DRAFT]
- source digest: [SHA-256]
- repository head/tree: [HEAD] / [TREE]

The request concerns protocol semantics and interoperability. It does not claim IETF adoption, consensus, approval, or RFC status.

Requested action: [ROUTING GUIDANCE / REVIEW / SUBMISSION CHECK].

Kind regards,  
Ingolf Lohmann

## 3. arXiv preprint support or endorsement inquiry

**Subject:** arXiv submission inquiry: [MANUSCRIPT TITLE]

Dear [NAME / ARXIV SUPPORT],

I am preparing a self-contained preprint package for [CATEGORY].

Exact package:
- source archive digest: [SHA-256]
- PDF digest: [SHA-256]
- repository head/tree: [HEAD] / [TREE]

The manuscript separates formal theorem statements from empirical claims and does not present repository verification as peer review.

Requested action: [ENDORSEMENT GUIDANCE / TECHNICAL SUBMISSION SUPPORT].

Kind regards,  
Ingolf Lohmann

## 4. IEEE editor or conference submission cover letter

**Subject:** Submission: [MANUSCRIPT TITLE]

Dear [EDITOR / PROGRAM CHAIR],

Please consider the manuscript “[TITLE]” for [VENUE].

Contribution:
[ONE PARAGRAPH]

Evidence and reproducibility:
[ONE PARAGRAPH WITH EXACT ARTIFACT DIGESTS]

This manuscript is not simultaneously under review at another venue: [CONFIRM BEFORE SEND].

Conflicts, funding, and prior dissemination:
[DECLARATION]

Kind regards,  
Ingolf Lohmann

## 5. Wikipedia talk-page source inquiry

**Subject:** Source review for a neutral encyclopedic treatment of [TOPIC]

Hello,

I am disclosing that I am associated with the underlying QIK-VRT project. I am not asking that project claims be accepted on the basis of self-published sources.

Independent secondary sources identified:
- [SOURCE 1]
- [SOURCE 2]

Proposed narrow topic:
[TOPIC]

Requested action: assess whether the independent sourcing is sufficient for a neutral, policy-compliant treatment. Repository materials should be used only within the limits applicable to primary sources.

Regards,  
Ingolf Lohmann

## 6. Zenodo record preparation checklist message

**Subject:** Pre-publication metadata and byte review for IED bundle

Dear [REVIEWER],

Please review the exact Zenodo candidate before any production publication.

- publication id: [ID]
- upload file set: [FILES]
- aggregate digest: [SHA-256]
- metadata digest: [SHA-256]
- repository head/tree: [HEAD] / [TREE]
- licence: [LICENCE]
- creators: [CREATORS]

Requested action: confirm only whether the frozen bytes and metadata are internally consistent. This draft is not a publication receipt and no DOI should be reported until the public record is observed and revalidated.

Kind regards,  
Ingolf Lohmann
