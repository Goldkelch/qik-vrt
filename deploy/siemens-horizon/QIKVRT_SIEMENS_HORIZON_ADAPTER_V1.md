# QIK-VRT Siemens Horizon Adapter Profile V1

## Scope

This profile defines a safe integration path between the QIK-VRT universal terminal pattern and Siemens Horizon / Siemens digital-twin environments.

## Verified external fit

Siemens publicly describes multiple closely related targets that are relevant here:

- **D4R::Horizon Suite** for rail signalling engineering, with modular SDK/plugin architecture, model-based data management, import/export including XML/CSV/RailML, and transport/rail use cases.
- **Siemens Digital Twin / Executable Digital Twin** environments that connect real systems and virtual representations, ingest live IoT data, support simulation, prediction, monitoring/control, and deployment on edge or cloud.
- Siemens Xcelerator as the wider integration context for digital-twin packaging/deployment/operation.

This profile does **not** claim that Siemens exposes a generic OCI container runtime inside D4R::Horizon Suite itself. Container deployment must bind to an actually supported Siemens execution surface or adjacent infrastructure.

## QIK-VRT mapping

QIK-VRT terminal semantics map to Siemens integration concepts as follows:

1. `OBSERVE` -> Siemens/Horizon model, SDK, file, event, telemetry or twin-state observation.
2. `D0 EXACT SUBJECT BINDING` -> exact project/model/entity/version/hash binding.
3. `PREPARE` -> proposed model/data/configuration change without protected physical effect.
4. `COMMIT` -> authorized write through the supported Siemens API/SDK/import mechanism.
5. `EFFECT_ACK` -> post-write readback of the same exact subject proving the intended effect rather than transport success alone.
6. `HOLD_UNVERIFIED` -> missing/stale identity, unsupported adapter, ambiguous target, failed readback, or safety-boundary violation.

## AD/DA terminal profile

The universal AD/DA terminal is represented as two explicitly separated directions:

- **AD / world-to-model**: sensor, telemetry, rail topology, medical-device or mobility data -> bounded digital state -> exact provenance -> model/twin observation.
- **DA / model-to-world**: validated model decision -> authorized actuator/configuration interface -> exact effect -> reobservation.

The DA edge MUST remain fail-closed. No physical actuation is inferred from simulation, message delivery, workflow success, or API acceptance.

## Containerization profile

The existing QIK-VRT Firefox + EFFECT_ACK HTTP daemon remains an OCI-compatible Linux userspace implementation profile.

For Siemens environments the preferred deployment order is:

1. package the terminal as OCI image;
2. deploy only to a Siemens-supported container/edge/cloud execution surface or a customer-controlled POSIX/OCI runtime adjacent to the Siemens environment;
3. expose a monitor-only HTTPS surface to Horizon/Xcelerator clients;
4. connect through supported SDK/API/file/telemetry adapters;
5. keep protected effects behind explicit authority and EFFECT_ACK readback.

## Domain adapters

### Rail / Mobility

Primary candidate: D4R::Horizon Suite SDK and supported interchange formats, including RailML where appropriate. QIK-VRT can act as an exact-subject provenance and effect-readback layer around model/data transitions.

### Digital Twin / Industry

Primary candidate: Siemens executable digital twin / Xcelerator integration. QIK-VRT can wrap the closed feedback loop with explicit distinction between prediction, command transport, physical effect and reobservation.

### Medical / MedTech

Use only as an integration/evidence pattern around validated medical software/device interfaces. No diagnostic, therapeutic or patient-affecting action may be inferred or executed without the applicable regulated safety, authorization and clinical validation layers.

## Integration state machine

`DISCOVER_CAPABILITY -> BIND_EXACT_SUBJECT -> PREPARE -> VALIDATE -> AUTHORITY_COMMIT -> POST_EFFECT_REOBSERVE -> RECEIPT -> SUCCESSOR | HOLD_UNVERIFIED`

## Current status

This document is an implementation/integration profile only. It does not establish Siemens endorsement, production deployment into a Siemens tenant, clinical validation, rail-safety certification, physical actuation, PASS, FINAL_PASS, or EFFECT_ACK_DONE.
