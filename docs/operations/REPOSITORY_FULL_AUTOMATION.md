# Repository full automation

This carrier implements the owner-authorized repository-internal continuation from an explicitly marked pull request through protected Main integration.

Opt-in marker:

```text
<!-- qikvrt-full-automation:v1 external_effect=REPOSITORY_MAIN_INTEGRATION -->
```

The marker does not weaken branch protection. A merge remains impossible until the existing exact-head technical gates are green and GitHub records the required native Code-Owner approval on the same head. The existing delegated native-account review adapter may provide that platform review only when its self-identifying counterpart credential and activation secret are valid.

At the final fence the trusted-Main promotion workflow reobserves Main, base, head, review state, Mesh review evidence, and the marker body. It then calls GitHub's pull-merge API with the exact expected head and merge method `merge`. A successful HTTP response is not the acknowledgement.

The transaction reaches scoped `EFFECT_ACK_DONE` only after fresh GitHub readback proves all of these simultaneously: the pull request is merged; Main equals the returned merge commit; merge parent 1 equals the reobserved base; merge parent 2 equals the exact reviewed head; and the merge tree equals the exact reviewed head tree.

The resulting status context is `QIKVRT repository main integration effect ack`.

This acknowledgement has scope `REPOSITORY_MAIN_INTEGRATION`. It does not imply a Vercel deployment, public release, publication, Zenodo effect, physical effect, scientific confirmation, or repository-wide/global completion. Those remain separate effect contracts and require their own execution and readback.
