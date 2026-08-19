# QIK-VRT Firefox Proxy Delegation Bridge V1

This bridge closes the local invocation gap between an agent/terminal request and the existing Firefox QIK-VRT terminal renderer without granting the browser new effect authority.

## Execution shape

```text
agent or terminal invocation
→ validate exact HTTPS target
→ launch Firefox with exact target URL
→ stop at human authentication / credential / secret-entry boundary
→ user completes only that owner-authenticated step
→ authoritative repository reobservation
→ next effect decision
```

The executable adapter is `tools/qikvrt_firefox_proxy_delegate.py`.

Example:

```text
python3 -B tools/qikvrt_firefox_proxy_delegate.py \
  --url https://github.com/settings/personal-access-tokens \
  --expected-owner Goldkelch \
  --repository Goldkelch/qik-vrt \
  --json
```

The bridge serializes no secret value and accepts no secret-value argument. It does not create credentials, mutate repository settings, submit reviews, merge, or claim an external effect. Its sole protected local effect is opening an allowlisted HTTPS target in Firefox.

## Boundary invariants

- Firefox remains renderer/proxy, not a privileged truth source.
- Browser permission is not effect authorization.
- A rendered DONE record is not an independently observed external effect.
- Authentication, credential creation and secret entry remain explicit human boundaries.
- Post-boundary repository state is new evidence and must be reobserved.
- Canonical `/AI` semantics remain unchanged.

## Failure classes

`BLOCK` is returned for a non-HTTPS target, non-allowlisted host, or embedded URL credentials. `HOLD` is returned when a Firefox executable is unavailable. Neither state is converted into release or completion.
