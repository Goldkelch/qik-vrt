# Owner return package — remaining corpus corrected candidates

Owner: **Ingolf Lohmann** (`NATURAL_PERSON`)

Review surface: **Goldkelch/qik-vrt PR #231**

Branch: `agent/remaining-corpus-corrected-candidates-owner-return-v1`

Source evidence head: `f60810b56a35f6e3434f1cacaca05a83e494aba2`

Candidate index Git blob: `713150777d5b3d23571da3c3bca39d9dc4a2b3f5`

## Candidate set

| Subject | Public record(s) | Selected correction claims | Candidate Git blob |
|---|---:|---:|---|
| `SUBJECT-172dd9bc2738fa43` | `20712301` | 175 | `dc2a79f76d9ce5f025859f30c137527d59ae37e7` |
| `SUBJECT-780b9bf86425cee3` | `21266670` | 176 | `11a020d055238492fd47c7acfa58b7a68a8ee81f` |
| `SUBJECT-7956d8acdc473825` | `21252415` | 276 | `6c882f051cd0fcfc712e1d9587f12fffb7c87b16` |
| `SUBJECT-7fdb36aa7c07c07d` | `21267021` | 209 | `2270ee8ffac3b36b4db1918a4413eb90affc174d` |
| `SUBJECT-b4849e1a2d6b2270` | `21244412`, `21245282`, `21245951`, `21247297`, `21247388` | 100 | `648e51025424076a3251afce78cd478b5a0991f9` |
| `SUBJECT-ce2390f18618ad0c` | `21252649` | 276 | `2b9d921ba65bdc3b2c7dfc2bc75c02f7805578b6` |

Total selected correction claims: **1,212**.

Observed internal hash mismatches bound by the source audits: **89**.

## Proposed versioned correction

The historical public files remain immutable evidence. The candidate set applies exactly two bounded operations:

1. Regenerate inconsistent internal manifest bindings from the exact bytes of a later candidate version, retaining historical values only in provenance.
2. Replace unbound positive `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, `P_nash`, persistence, completion and universality assertions with `NOT_REVALIDATED_IN_THIS_CANDIDATE` boundaries.

No unlisted claim is selected for change.

## Owner decision

The exact indexed candidate set is awaiting one explicit decision:

- `ACCEPT`
- `REJECT`

Acceptance authorizes only later repository verification and promotion work. It does **not** authorize Zenodo upload, publication, record mutation, proof-corpus publication, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
