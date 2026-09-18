# TEMDD interoperability v0.1

TEMDD interoperates through canonical events, canonical IR, explicit effect intents and readback receipts. GitHub Actions, Railway/runtime services, REST, browsers and other systems are adapters. Adapters may translate representation but must not reinterpret semantic status. Existing QIK-VRT event envelopes and Effect-Ack contracts are intended transport/effect boundaries; adapters must preserve their digests and exact-subject binding.
