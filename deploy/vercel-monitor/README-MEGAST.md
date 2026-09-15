# Mega ST: original-archive descriptor through Rails on Vercel

This change extends the existing `deploy/vercel-monitor` project. It does not
replace the monitor, add a second repository controller, rebuild an image,
publish a release, start a VM, or manufacture a new boot witness.

## Implemented surface

`GET /api/megast` is an API-only Rails endpoint. It exposes the original source,
archive and netboot pins and the eight owner-specified transport filenames.
`HEAD` returns no body. The Vercel handler rejects write methods with HTTP 405.
`GET /api/megast/download` deliberately returns HTTP 503 with a concrete remaining
action, not a fake link. Both the public path and Vercel's rewritten handler
path are covered. Responses are bounded to 64 KiB and use `Cache-Control: no-store`.

The `VERCEL_GIT_COMMIT_SHA` environment value is labeled as a provider-reported,
not independently verified deployment identity. It is never substituted for
the original image's source commit. A source descriptor is not a live receipt.

## Frozen source artifact

- Repository: `Goldkelch/qik-vrt`, PR #1079.
- Source commit: `2fdcf8d233b1495732ef38e3406ebfc095fd0ef3`.
- Source tree: `e073c90c1d8c5ffa47b8a4c08093ea00046ab850`.
- Original Actions run: `34895793369`; archive artifact: `10368454862`.
- Original archive: `qikvrt-megast-2fdcf8d2.zip`, 3,298,453,805 bytes.
- Archive SHA-256: `762fccec9f80bc83ac0475d5fdc3627dd370ad5ac8aabaa6d1c878de20a1bb76`.
- Netboot manifest SHA-256: `b0f33a6f9385ab72b42737165a427e3c33df49295c13cb10da70562fea9b1701`.

The archive's size and digest were read from GitHub Actions metadata. The archive
was not redownloaded or booted during this change. The manifest pin, assembler
name and transport names come from the owner's supplied instructions. Individual
part digests and anonymous public URLs have not been observed; their JSON values
remain null. The assembler and transport parts are not invented or regenerated.

The new integration candidate inherits #1094's source tree but does not inherit
its P2/P3 evidence. The archived image remains the older, explicitly named source
artifact. No new image is relabeled as the original.

## Tests and runtime admission

The complete `Gemfile.lock` was actually derived by Bundler 2.6.9 on Ruby 3.3.8
from the unchanged Gemfile in GitHub Actions run 34969076014. Its SHA-256 is
`b28e08a527254ea645ae5c2771b55e4538111b2dc399c95247a8fbf6be741c8b`.
The original resolution and failure log remain historical, not final-head P2.
The pin is Rails/railties 8.1.3.1; no dependency downgrade was performed.

From the repository root, with Ruby 3.3.8 and Bundler 2.6.9 provided by the
pinned CI action or a separately verified operator installation:

```sh
sh tools/bootstrap-runtime.sh --install --accept-third-party --profile rails
make megast-rails-test
make test
```

Installation is explicit; neither test target resolves nor installs gems.
The existing bootstrap validates the declared byte authorities, verifies cached
`.gem` archives against the lock, derives a fresh frozen bundle and verifies it.
It never restores an installed executable bundle from a shared cache. A local
receipt outside the tool cache binds installed bytes; check-only verifies those
bytes before loading them. Missing runtime is CONTINUE/20 and fails the Make gate;
corrupt cache, source drift or failed installation is BLOCK, with rollback.
The existing cache verifier covers Ruby, Bundler and the complete Rails closure
through its checksummed lock authority. Locked platforms other than Linux x86_64
are resolver data, not a claim of runtime validation on those platforms.

Both original test suites are mandatory. The production-mode Rails smoke test
creates a random `SECRET_KEY_BASE` only inside its test process, keeps host
rejection and missing-public-delivery checks, and exercises the real
WEBrick-to-Rails handler. It never writes or logs the key. The application has
**no built-in production secret**: the intended Vercel environment must supply
its own `SECRET_KEY_BASE`; that configuration is a separate deployment gate.
No CI/test secret is suitable for production or persisted in Git/cache.

Cold and warm installs execute the same source/checksum/runtime checks. Green
scoped suites do not replace full literal-head P2, Vercel build-only evidence,
native review, Main adoption or independently observed external effects.

## Public delivery and Main continuation

The existing Vercel deployment connection returned no teams, failed to list
projects under the repository-recorded `ingolflohmann-8385` scope, and refused
its recorded Beacon deployment with HTTP 403. These observations establish only
this connection's capability boundary, not absence of the owner's credentials
or repository provisioning. No new production deployment was attempted.

Continue through current-head P2, native counterpart review, independent ruleset
effect, unchanged post-review reobservation, legitimate expected-head Main
promotion, and exact-Main readback. Then reuse the existing original-archive
transport/export and Mega ST publication mechanisms. Do not rebuild the image
merely to transport it. GitHub's release-asset limit is under 2 GiB per file, so
the 3.3 GB archive cannot become a single release asset; preserve the existing
eight-part transport and original assembler.

Public delivery needs independently read-back part bytes, the reconstructed
original archive digest, actual release identities and URLs. Add URL admission
only in that evidence-bound successor. Vercel should serve the small API/UI;
large image files belong on the reviewed binary delivery origin, not in a
buffering Rails function. The actual Linux/QEMU receiver boot remains distinct
from hosting the Rails API. Physical Atari execution, native review, ruleset
enforcement, Main adoption and scoped EFFECT_ACK_DONE remain separate claims.

## Implementation references

- https://vercel.com/docs/functions/runtimes/ruby
- https://guides.rubyonrails.org/api_app.html
- https://rubygems.org/gems/railties/versions/8.1.3.1
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

Human contribution: Ingolf Lohmann's architecture, exact source artifact and
execution request. Artificial-cognitive contribution: ChatGPT's adapter,
validation code and this scoped integration candidate. Acceptance does not
retroactively change that origin attribution. Repository licensing applies.
