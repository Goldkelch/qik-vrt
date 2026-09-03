# IONOS delivery package for `horizont.goldkelch.de`

This directory is the static document root prepared for the official public origin:

`https://horizont.goldkelch.de/`

The display brand remains **Horizon by QIK VRT** with **Copyright by Ingolf Lohmann.**

## Authenticated provider transitions still required

1. Register `goldkelch.de` inside the existing IONOS customer contract after the authenticated checkout has shown the exact price, renewal terms, and assignment.
2. Create the `horizont` subdomain and bind it to this directory as its document root.
3. Upload this directory, or connect an authenticated IONOS Git deployment that serves it unchanged.
4. Activate HTTPS and verify the certificate for `horizont.goldkelch.de`.
5. Read back `/`, `/health.json`, DNS, and TLS from the public origin.

No registration, DNS, TLS, publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE claim is valid before authoritative provider and public readback.
