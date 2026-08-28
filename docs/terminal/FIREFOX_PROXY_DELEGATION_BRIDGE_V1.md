# QIK-VRT Firefox Proxy Delegation Bridge V1

This bridge closes the local invocation gap between an agent/terminal request and the existing Firefox QIK-VRT terminal renderer without granting the browser general effect authority.

## Execution shape

```text
agent or terminal invocation
→ validate exact HTTPS target
→ bind a non-secret PR/head/tree review request when explicitly selected
→ launch Firefox with the exact target URL
→ stop at the authenticated-session boundary
→ extension reobserves principal, repository, open review-ready PR, head, tree,
  current review request and prior exact-head substantive APPROVE disposition
→ extension attempts only the bounded APPROVE UI submission
→ authoritative repository reobservation determines whether the review effect occurred
→ next effect decision
```

The executable adapter is `tools/qikvrt_firefox_proxy_delegate.py`. It accepts no secret-value argument and serializes no credential.

Example dry run:

```text
python3 -B tools/qikvrt_firefox_proxy_delegate.py \
  --url https://github.com/Goldkelch/qik-vrt/pull/727/files \
  --expected-owner Goldkelch \
  --repository Goldkelch/qik-vrt \
  --effect review_approve \
  --pr 727 \
  --head <40-hex-head> \
  --tree <40-hex-tree> \
  --dry-run \
  --json
```

The local adapter does not claim that launching Firefox submitted a review. The content script may attempt `review_approve` only for `Goldkelch/qik-vrt`, only inside a live `Goldkelch` session, and only after the live PR/head/tree and the prior workflow-authored exact-head substantive `APPROVE` marker are reobserved. A UI click is still not effect evidence; the resulting GitHub review must be reobserved separately.

When GitHub renders the review controls after the content script has started,
the script waits on DOM mutation edges using `MutationObserver`; it does not
periodically rescan the page. A single bounded `AbortSignal.timeout` edge turns
an absent control into `HOLD` and never retries it implicitly.

The bridge does not merge, mutate rulesets, publish, deploy, create credentials, enter secrets or perform arbitrary browser automation.

## Boundary invariants

- Firefox remains renderer/proxy, not a privileged truth source.
- Browser permission is not effect authorization.
- Activity is not effect; a submitted-click marker is not an observed review.
- `TRANSPORT_ACK != EFFECT_ACK` remains explicit.
- A rendered DONE record is not an independently observed external effect.
- Authentication, credential creation and secret entry remain explicit human boundaries.
- Post-boundary repository state is new evidence and must be reobserved.
- Canonical `/AI` semantics remain unchanged.

## Failure classes

`BLOCK` is returned for a non-HTTPS target, non-allowlisted host, embedded URL credentials or an invalid exact binding. `HOLD` is returned when Firefox is unavailable or when live principal/PR/head/tree/review-disposition checks fail. Neither state is converted into review authority, release or completion.
