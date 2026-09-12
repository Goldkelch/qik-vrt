<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Ich bin von dieser Reise zurückgekehrt

Author and publication direction: **Ingolf Lohmann**.

This is the candidate source surface for the requested 47-edition reading page.
It preserves the complete owner-supplied German essay, including **Der Rückweg**,
and the later supplied opening Spotify link. It is not a Wikipedia article or
an assertion of an independently confirmed physical theory.

## Exact source and scope

- German source: `source.de.txt`, UTF-8/LF, 39,745 bytes.
- Source SHA-256: `181314375effc68933baec365e7973a14ad3981605bb192f93a62c37a321f487`.
- Source Git blob: `45c1f23cdf842ef5d92bfbef1d17da536b47f069`.
- 540 source blocks; 20 separator blocks. The source file, not a prose summary,
  is the authoritative translation input.
- `WIKIPEDIA_47_LANGUAGE_SOURCE.json` supplies only the historical edition set.
  Its old translation status does not apply to this new essay. The 47 include
  the German original and Simple English; they are Wikipedia editions, not a
  claim that Wikipedia has only 47 languages.
- Translations are complete-text **ChatGPT drafts without independent language
  review**, with immutable source and translation byte bindings.

## Reproduce the reading preview

From the repository root, using the declared Python runtime:

```sh
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B -m unittest discover -s tests -p test_qikvrt_journey_site.py -v
python3 -B tools/qikvrt_journey_site.py check
python3 -B tools/qikvrt_journey_site.py preview --output /tmp/qikvrt-journey/index.html
python3 -B tools/qikvrt_journey_site.py coverage-check
```

The preview is explicitly incomplete until all 47 full texts are present.
The initial candidate contains the German original and the English draft;
45 editions remain unimplemented. Missing editions are disabled, not replaced
by a different language or a link to an unarchived translation service.
The coverage command must return a nonzero result while any edition is absent.
Structural equality of block counts is not a proof of linguistic equivalence.

The read-only preview job extends the existing QIKVRT CI workflow. It uploads
an exact-head preview, coverage report and canonical integrity proposal without
writing the checkout, changing a Git ref, merging, or deploying the website.
The proposal must be independently checked and legitimately persisted before
fresh exact-successor validation can be claimed.

## Remaining delivery conditions

Complete the remaining source-bound translations, validate their coverage and
language quality, then follow the required exact-head validation, native review,
post-review readback, legitimate Main promotion and exact-Main readback path.
Public delivery requires a separate actual deployment and HTTP/content readback
of the landing page and every available language route. The planned `/reise/`
URL is not a delivered homepage until those observations exist.

No native review, merge, deployment, Wikipedia/Zenodo/arXiv publication,
independent empirical confirmation, PASS, FINAL_PASS or EFFECT_ACK_DONE is
claimed here. The introduction email to Joachim remains deferred until the
requested homepage is delivered.
