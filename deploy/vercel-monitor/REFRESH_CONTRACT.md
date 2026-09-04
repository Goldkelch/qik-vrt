# Horizon split refresh contract

The Vercel monitor has two independent read-only refresh loops.

- Gate projection: `GET /api/gates?head=<exact-40-hex-sha>` every 1 second while the page is visible. It renders exactly eight named repository gate slots in the sticky, above-the-fold gate rail. It never mutates repository state.
- Page projection: `GET /api/state` every 60 seconds. It updates the subject metadata, product-owner signal, explanatory state and workflow table without reloading the document or moving the user's scroll position.

The gate endpoint is exact-head bound. A missing or malformed head is `HOLD_UNVERIFIED`; predecessor results are not transferred to another head. Both endpoints are monitor-only and do not assert merge, approval, deployment, publication, PASS, FINAL_PASS or EFFECT_ACK_DONE.

For sustained one-second GitHub readback, the Vercel deployment should provide a read-only `GITHUB_READ_TOKEN` (or compatible `GITHUB_TOKEN`). The code adds that credential only to GitHub GET requests and exposes no write API. If upstream readback is unavailable, the surface fails closed rather than inferring a gate state.
