<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# TEMDD: Tested Event Model Driven Development als ausführbare Sprache und Effect-Verification-Laufzeit

**Autor:** Ingolf Lohmann  
**Datum:** 23. September 2026  
**Publikationstyp:** technische Architektur- und Sprachdeklaration

## Erklärung

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> q.e.d.  
> Ingolf Lohmann

TEMDD verbindet damit die bisher häufig getrennten Ebenen Entwicklungsmethode, Sprache, Toolchain und Wirkungsnachweis. Ein TEMDD-Programm endet semantisch nicht beim Start einer Aktion oder beim erfolgreichen Testlauf. Es endet erst dann, wenn die beabsichtigte Wirkung ausgeführt, beobachtet, frisch zurückgelesen und gegen die gebundenen Akzeptanzkriterien geprüft wurde.

Die kanonische Laufzeitkette ist:

```text
COMPILE → BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE
```

Die integrierte Werkzeugkette wird als

```text
Compiler → Linker/Binder → Dynamic Loader/Resolver → Runtime
→ Debugger/Observer → Test Runner → Effect Verifier → IDE
```

verstanden.

Daraus folgt die zentrale Abgrenzung:

```text
EXECUTE ≠ DONE
TEST ≠ DONE
OBSERVE ≠ DONE
TRANSPORT_ACK ≠ EFFECT_ACK
```

Die vollständige technische und epistemische Einordnung steht im kanonischen Dokument
[`spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md`](../../../spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md).

## Evidenzgrenze

Diese Veröffentlichung dokumentiert die von Ingolf Lohmann erklärte TEMDD-Architektur. Sie ersetzt keine exact-head Implementierungs-, Conformance-, Release- oder Deployment-Evidenz. Zenodo-Persistenz würde Identität, Verfügbarkeit, Metadaten und Fixität der veröffentlichten Bytes belegen, nicht automatisch wissenschaftliche Validierung, Peer Review oder vollständige Implementierung.

## Repository-Nodes

Die Erklärung ist als gemeinsamer Successor für folgende QIK-VRT-Nodes vorgesehen:

- `Goldkelch/qik-vrt`
- `ingolf-lohmann/qik-vrt`

Historische Veröffentlichungen bleiben unverändert.
