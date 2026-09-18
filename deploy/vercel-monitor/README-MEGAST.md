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

Core descriptor and actual WEBrick-to-Rack bridge tests, without Rails:

```sh
cd deploy/vercel-monitor
ruby test/megast_test.rb --seed 1079
```

The real Rails boot/routing test is separate and never skips missing dependencies:

```sh
bundle exec ruby test/rails_smoke_test.rb
```

The optional Rails candidate uses Ruby 3.3.x and pins `railties` to 8.1.3.1.
Before admitting it to P2 or deploying, use the repository's existing tool-cache
and bootstrap mechanism to register/provision the Ruby/Bundler/Rails profile,
resolve and review the full transitive `Gemfile.lock`, verify cache coverage,
and run BOTH test suites on the final exact candidate. The local core test used
Ruby 3.3.8. Rails/Rack dependencies were unavailable in this execution sandbox;
full Rails boot, the repository bootloader, full `make test`, integrity
materialization and a Vercel build have NOT been verified here. The Gemfile is
not represented as a complete transitive dependency lock.

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
