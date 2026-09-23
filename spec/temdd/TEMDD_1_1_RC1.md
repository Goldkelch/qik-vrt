# TEMDD 1.1-rc1
## Tested Event Model Driven Development

**Version:** 1.1-rc1  
**Status:** Repair Candidate – normative closure, semantik-erhaltend gegenüber TEMDD 1.1 Draft  
**Sprache:** Deutsch  
**Kanonische Auflösung des Akronyms:** Tested Event Model Driven Development  
**Normative Schlüsselwörter:** MUST, SHALL, SHOULD, MAY gemäß BCP 14 (RFC 2119 und RFC 8174), wenn sie in Großbuchstaben verwendet werden

---

# Präambel

TEMDD ist ein Protokoll-, Verifikations- und Vertrauensmodell zur Feststellung tatsächlicher Wirkung.

Klassische Systeme beantworten typischerweise:

```text
Wurde übertragen?
Wurde zugestellt?
Wurde ausgeführt?
```

TEMDD beantwortet zusätzlich:

```text
Ist die beabsichtigte Wirkung nachweislich eingetreten?
```

Der zentrale Gedanke lautet:

> Ein Vorgang gilt erst dann als erfolgreich, wenn seine Wirkung unabhängig beobachtet, zurückgelesen, verifiziert und akzeptiert wurde.

---

# 1. Grundaxiome

## Axiom 1: No Effect Without Evidence

\[
\boxed{
\text{No effect without evidence.}
}
\]

Eine Wirkung darf nicht allein aus Transport- oder Ausführungsstatus abgeleitet werden.

---

## Axiom 2: No Accepted Effect Without Trust

\[
\boxed{
\text{No accepted effect without authenticated actors, authorized actions and verified evidence.}
}
\]

---

## Axiom 3: Effect Over Delivery

Transporterfolg ist nicht gleich Wirkungserfolg.

Formal:

\[
TRANSPORT\_ACK
\nRightarrow
EFFECT\_ACK
\]

---

## Axiom 4: Fresh Observation Required

Jede akzeptierte Wirkung MUSS auf frischer Evidenz beruhen.

\[
t_{readback}
>
t_{execution}
\]

---

# 2. Terminologie

## Subject

Der überprüfbare Gegenstand.

Beispiele:

```text
Datei
Prozess
VM
Container
FPGA
Gerät
Sensor
Motor
Datenbankobjekt
```

Formal:

\[
S=id(x)
\]

---

## Intent

Beschreibt die gewünschte Wirkung.

Beispiel:

```json
{
  "action":"set_speed",
  "target":1200
}
```

---

## Evidence

Nachweis über den beobachteten Zustand.

---

## Acceptance Criteria

Formale Regeln zur Bewertung der Evidenz.

---

## Principal

Authentifizierte handelnde Entität.

Typen:

```text
USER
SERVICE
DEVICE
PROCESS
ROBOT
AI_AGENT
```

---

# 3. Logisches Modell

Eine TEMDD-Transaktion besteht aus:

```text
Transaction
 ├─ Principal
 ├─ Subject
 ├─ Intent
 ├─ Acceptance Criteria
 ├─ Evidence
 ├─ Result
 └─ State
```

Formal:

\[
TX =
(P,S,I,C,E,R,Q)
\]

mit:

```text
P = Principal
S = Subject
I = Intent
C = Acceptance Criteria
E = Evidence
R = Result
Q = State
```

---

# 4. Zustandsmodell

## Normative Zustände

```text
CREATED
SENT
RECEIVED
EXECUTED
OBSERVED
READBACK
VERIFIED
ACCEPTED
EFFECT_ACK_DONE
FAILED
```

---

## Zustandsautomat

```text
CREATED
   |
SENT
   |
RECEIVED
   |
EXECUTED
   |
OBSERVED
   |
READBACK
   |
VERIFIED
   |
 +---------+
 |         |
 v         v
ACCEPTED  FAILED
   |
   v
EFFECT_ACK_DONE
```

---

## Terminale Zustände

```text
EFFECT_ACK_DONE
FAILED
```

Terminale Zustände SHALL unveränderlich sein.

\[
Terminal(TX)
\Rightarrow
Immutable(TX)
\]

---

# 5. ACK-Klassen

## TRANSPORT_ACK

Bestätigt:

```text
Bytes angekommen
```

Garantiert nicht:

```text
Ausführung
Zielzustand
Wirkung
```

---

## EXEC_ACK

Bestätigt:

```text
Aktion ausgeführt
```

Garantiert nicht:

```text
beobachtete Wirkung
```

---

## EFFECT_ACK

Bestätigt:

```text
akzeptierte Evidenz vorhanden
```

`EFFECT_ACK` ist ein Acknowledgement/Resultat und KEIN terminaler Transaktionszustand.

---

## EFFECT_ACK_DONE

Terminaler Erfolg und normativer Transaktionszustand.

\[
Observed(S)
\equiv
Expected(S)
\]

unter der definierten Äquivalenzrelation.

---

# 6. Äquivalenzmodell

TEMDD verlangt die explizite Definition der verwendeten Gleichheitsrelation.

Die gewählte Äquivalenzrelation MUSS Bestandteil der Acceptance Criteria sein und MUSS vor `EXECUTE` an die Transaktion gebunden werden. Ein nachträglicher Wechsel der Äquivalenzrelation ist für dieselbe Transaktion unzulässig.

---

## Exact Equality

\[
Observed = Expected
\]

---

## Bit Equality

\[
bits(Observed)=bits(Expected)
\]

---

## Semantic Equality

\[
Meaning(Observed)=Meaning(Expected)
\]

---

## Functional Equality

\[
f(Observed)=f(Expected)
\]

---

## Tolerance Equality

\[
|Observed-Expected| < \epsilon
\]

---

# 7. Evidenzmodell

## Verbotene Evidenz

Nicht ausreichend:

```text
COMMAND_SENT
COMMAND_EXECUTED
SUCCESS_FLAG
LOG_ENTRY
```

---

## Zulässige Evidenz

```text
READBACK
MESSSYSTEM
EXTERNE BEOBACHTUNG
SIGNIERTE TELEMETRIE
```

---

## Mindestanforderungen

Evidenz MUSS sein:

```text
fresh
bound
authentic
observable
traceable
verifiable
```

---

# 8. Evidenzklassen

## E1

Selbstberichtete Evidenz

Beispiele:

```text
API-State
Softwarestatus
```

---

## E2

Unabhängige Systembeobachtung

Beispiele:

```text
Monitoring-System
zweiter Controller
Validator-Service
```

---

## E3

Physische Evidenz

Beispiele:

```text
Sensor
Messgerät
Encoder
GPS
Oszilloskop
```

---

Normativ:

\[
E3 > E2 > E1
\]

High-Assurance-Systeme SHOULD mindestens E2 verlangen.

---

# 9. Kausalitätsanforderung

Evidenz MUSS kausal auf eine Aktion folgen.

\[
Action(A)
\prec
Evidence(E)
\]

Nicht zulässig:

```text
Cachewerte
alte Messwerte
Readbacks früherer Transaktionen
```

---

# 10. Vertrauensmodell

TEMDD definiert eine vollständige Vertrauenskette:

```text
Principal
 →
Credential
 →
Authorization
 →
Action
 →
Evidence Source
 →
Evidence
 →
Verification
 →
Acceptance
```

Formal:

\[
TrustChain=
(P,Cr,Az,A,ES,E,V,Ac)
\]

mit:

```text
P  = Principal
Cr = Credential
Az = Authorization
A  = Action
ES = Evidence Source
E  = Evidence
V  = Verification
Ac = Acceptance
```

---

# 11. Authentifizierung

Jeder API-Aufruf MUSS authentifiziert werden.

Anonyme Requests SHALL NOT akzeptiert werden.

---

## Unterstützte Verfahren

### JWT

```http
Authorization: Bearer <token>
```

---

### Mutual TLS

```text
Client Certificate
```

---

### Hardware Credentials

```text
TPM
HSM
FIDO2
Passkey
```

---

### Digitale Signaturen

```text
Ed25519
ECDSA
RSA-PSS
```

---

# 12. Autorisierung

Authentifizierung allein ist nicht ausreichend.

Vor jeder Operation MUSS geprüft werden:

\[
Authorized(P,S,O)
\]

---

## Standardrechte

```text
TEMDD.CREATE
TEMDD.EXECUTE
TEMDD.OBSERVE
TEMDD.READBACK
TEMDD.VERIFY
TEMDD.ACCEPT
TEMDD.ADMIN
```

---

# 13. Rollenmodell (RBAC)

## Observer

```text
OBSERVE
READBACK
```

---

## Operator

```text
CREATE
EXECUTE
OBSERVE
READBACK
```

---

## Verifier

```text
VERIFY
```

---

## Approver

```text
ACCEPT
```

---

## Administrator

```text
ADMIN
```

---

# 14. Separation of Duties

Für kritische Systeme SHOULD gelten:

\[
CREATE \neq VERIFY
\]

\[
VERIFY \neq ACCEPT
\]

\[
EXECUTE \neq APPROVE
\]

---

# 15. Readback-Protokoll

Ein Readback MUSS enthalten:

```json
{
  "subject_id":"motor:1",
  "value":1198,
  "timestamp":"2026-09-24T12:00:01Z",
  "source":"sensor-17"
}
```

---

## Signierte Readbacks

SHOULD enthalten:

```json
{
  "signature":{
    "algorithm":"ed25519",
    "value":"..."
  }
}
```

---

# 16. Challenge-Response

Zur Vermeidung von Replay-Angriffen MAY TEMDD Challenge-Response verwenden.

\[
Response =
Sign(Readback,Nonce)
\]

Die Antwort MUSS transaktionsgebunden sein.

---

# 17. API-Spezifikation

## Create Transaction

```http
POST /temdd/v1/transactions
```

Request:

```json
{
  "subject_id":"motor:1",
  "intent":{
    "action":"set_speed",
    "target":1200
  },
  "acceptance":{
    "type":"range",
    "relation":"TOLERANCE_EQUALITY",
    "minimum":1195,
    "maximum":1205
  }
}
```

---

## Execute

```http
POST /temdd/v1/transactions/{id}/execute
```

---

## Observe

```http
POST /temdd/v1/transactions/{id}/observation
```

---

## Readback

```http
POST /temdd/v1/transactions/{id}/readback
```

---

## Verify

```http
POST /temdd/v1/transactions/{id}/verify
```

---

## Accept

```http
POST /temdd/v1/transactions/{id}/accept
```

Request:

```json
{
  "verification_id":"verification-123",
  "decision":"ACCEPT"
}
```

Der aufrufende Principal MUSS für `TEMDD.ACCEPT` autorisiert sein. Die Acceptance MUSS an dieselbe Transaktion, dieselbe Evidenz und dieselben zuvor gebundenen Acceptance Criteria gekoppelt sein.

---

## Status

```http
GET /temdd/v1/transactions/{id}
```

---

# 18. Idempotenz

Jede Transaktion MUSS einen Idempotenzschlüssel besitzen.

```json
{
  "idempotency_key":"7be2a9d4..."
}
```

Wiederholte Requests DÜRFEN keine neue Transaktion erzeugen.

---

# 19. Audit-Modell

Jede Operation MUSS auditierbar sein.

Mindestfelder:

```json
{
  "transaction_id":"tx-123",
  "principal":"user:ingolf",
  "operation":"VERIFY",
  "timestamp":"2026-09-24T12:00:00Z",
  "result":"SUCCESS"
}
```

---

# 20. Nichtabstreitbarkeit

TEMDD SOLLTE kryptographische Beweise erzeugen.

Nachweisbar sein MUSS:

```text
Wer?
Wann?
Was?
Warum?
Mit welcher Evidenz?
Mit welchem Ergebnis?
```

Formal:

\[
Proof(P,TX,E)
\]

---

# 21. Abschlusszertifikat

Nach erfolgreicher Verifikation SOLLTE ein Zertifikat erstellt werden.

```json
{
  "transaction_id":"tx-123",
  "subject_id":"motor:1",
  "result":"EFFECT_ACK_DONE",
  "verified_at":"2026-09-24T12:00:01Z",
  "signature":"..."
}
```

Dieses Zertifikat bildet den portablen Wirkungsnachweis.

---

# 22. Referenzalgorithmus

```pseudo
authenticate()

authorize()

transaction := create()

execute()

observe()

readback()

verify()

accept()

emit_effect_certificate()

return EFFECT_ACK_DONE
```

---

# 23. Kanonische formale Erfolgsdefinition

Für eine Transaktion `TX` seien `P=Principal(TX)`, `S=Subject(TX)`, `O=Operation(Intent(TX))`, `C=AcceptanceCriteria(TX)` und `E=Evidence(TX)`.

Dann gilt als einzige normative Erfolgsdefinition:

\[
\begin{aligned}
TEMDD\_SUCCESS(TX) \iff
& Authenticated(P)
\\
\land& Authorized(P,S,O)
\\
\land& Bound(TX,S,Intent(TX),C)
\\
\land& Executed(TX)
\\
\land& Observed(TX)
\\
\land& ReadBack(TX,E)
\\
\land& Trusted(Source(E))
\\
\land& Fresh(E)
\\
\land& Bound(E,TX,S)
\\
\land& Causal(E,TX)
\\
\land& Verify(E,C)
\\
\land& Accept(E,C)
\end{aligned}
\]

`Authorized` besitzt normativ überall die Stelligkeit `Authorized(P,S,O)`.

---

# 24. Normatives Endtheorem

\[
\boxed{
State(TX)=EFFECT\_ACK\_DONE
\iff
TEMDD\_SUCCESS(TX)
}
\]

Daraus folgt:

\[
State(TX)=EFFECT\_ACK\_DONE
\Rightarrow
Terminal(TX)
\land
Immutable(TX)
\]

---

# 25. TEMDD-Kernsatz

\[
\boxed{
\text{Ein Vorgang gilt nicht als erfolgreich, weil er gesendet, empfangen oder ausgeführt wurde, sondern weil seine beabsichtigte Wirkung durch vertrauenswürdige, frische, kausal gebundene und verifizierte Evidenz nachgewiesen wurde.}
}
\]

**TEMDD 1.1-rc1** definiert damit ein vollständiges Framework für **nachweisbare Wirkung**, das Transport, Ausführung, Beobachtung, Evidenz, Vertrauen, Autorisierung und formale Akzeptanz in einem konsistenten Modell zusammenführt.

## 26. Fehlerbehandlung und Retry-Regeln

### 26.1 Ziel

TEMDD unterscheidet zwischen:

```text
Temporären Fehlern
(Potential Retry)

Permanenten Fehlern
(No Retry)

Terminalen Fehlern
(Transaction Failed)
```

Nicht jeder Fehler führt zu:

```text
FAILED
```

Ein TEMDD-System MUSS bestimmen können, ob eine Wiederholung zulässig ist.

—

# 26.2 Fehlerklassifikation

## Retryable Errors

Temporäre Fehler.

Der Vorgang DARF wiederholt werden.

Beispiele:

```text
Netzwerkunterbrechung
Timeout
temporär nicht erreichbarer Sensor
kurzzeitige Ressourcensperre
```

Kategorie:

```text
RETRYABLE
```

—

## Non-Retryable Errors

Permanente Fehler.

Eine Wiederholung führt erwartungsgemäß nicht zum Erfolg.

Beispiele:

```text
ungültiges Subject
ungültige Berechtigung
ungültiges Datenformat
fehlende Pflichtfelder
```

Kategorie:

```text
NON_RETRYABLE
```

—

## Terminal Errors

Fehler, welche die Transaktion endgültig beenden.

Kategorie:

```text
TERMINAL
```

—

# 26.3 Normative Fehlercodes

## Authentifizierung

```text
AUTH_REQUIRED
AUTH_INVALID
AUTH_EXPIRED
AUTH_REVOKED
```

—

## Autorisierung

```text
ACCESS_DENIED
ROLE_REQUIRED
INSUFFICIENT_PRIVILEGES
POLICY_VIOLATION
```

—

## Subject

```text
INVALID_SUBJECT
SUBJECT_NOT_FOUND
SUBJECT_UNAVAILABLE
SUBJECT_LOCKED
```

—

## Intent

```text
INVALID_INTENT
INTENT_NOT_SUPPORTED
INTENT_CONFLICT
```

—

## Ausführung

```text
EXECUTION_FAILED
EXECUTION_TIMEOUT
EXECUTION_REJECTED
EXECUTION_ABORTED
```

—

## Evidenz

```text
EVIDENCE_MISSING
EVIDENCE_EXPIRED
EVIDENCE_TAMPERED
EVIDENCE_UNTRUSTED
EVIDENCE_INVALID_SIGNATURE
```

—

## Readback

```text
READBACK_FAILED
READBACK_TIMEOUT
READBACK_SOURCE_UNAVAILABLE
READBACK_STALE
READBACK_INCONSISTENT
```

—

## Verifikation

```text
VERIFICATION_FAILED
VERIFICATION_TIMEOUT
VERIFICATION_ERROR
```

—

## Akzeptanz

```text
ACCEPTANCE_FAILED
ACCEPTANCE_TIMEOUT
```

—

## System

```text
NETWORK_ERROR
RATE_LIMITED
RESOURCE_EXHAUSTED
DEPENDENCY_UNAVAILABLE
SYSTEM_OVERLOADED
INTERNAL_ERROR
```

—

# 26.4 Fehlerobjekt

Normatives Fehlerformat:

```json
{
  "error": {
    "code": "READBACK_TIMEOUT",
    "category": "RETRYABLE",
    "message": "Readback source did not respond within timeout.",
    "retry_allowed": true,
    "retry_after_seconds": 30
  }
}
```

—

# 26.5 Retry-Regeln

## Grundregel

Ein Retry DARF nur erfolgen, wenn:

```math
RetryAllowed(error)=true
```

—

## Verbotene Retries

Retry SHALL NOT erfolgen bei:

```text
AUTH_INVALID
ACCESS_DENIED
INVALID_INTENT
INVALID_SUBJECT
POLICY_VIOLATION
ACCEPTANCE_FAILED
```

Diese Fehler gelten als fachlich endgültig.

—

## Zulässige Retries

Retry SHOULD erfolgen bei:

```text
NETWORK_ERROR
EXECUTION_TIMEOUT
READBACK_TIMEOUT
DEPENDENCY_UNAVAILABLE
SYSTEM_OVERLOADED
RESOURCE_EXHAUSTED
```

—

# 26.6 Exponential Backoff

TEMDD SHOULD Exponential Backoff verwenden.

Formel:

\[
delay_n =
base \cdot 2^n
\]

Beispiel:

```text
Retry 1 = 1 s
Retry 2 = 2 s
Retry 3 = 4 s
Retry 4 = 8 s
Retry 5 = 16 s
```

—

# 26.7 Jitter

Zur Vermeidung synchroner Lastspitzen SHOULD ein zufälliger Offset verwendet werden.

\[
delay =
backoff + random(jitter)
\]

Beispiel:

```text
8 s + random(0..2 s)
```

—

# 26.8 Retry-Limit

Ein TEMDD-System MUSS ein Maximum definieren.

Beispiel:

```text
MAX_RETRIES = 5
```

Nach Erreichen:

```text
FAILED
```

—

# 26.9 Readback-spezifische Retries

Readbacks besitzen besondere Regeln.

Zulässig:

```text
READBACK_TIMEOUT
READBACK_SOURCE_UNAVAILABLE
```

Nicht zulässig:

```text
READBACK_STALE
EVIDENCE_TAMPERED
```

Begründung:

Ein manipuliertes oder veraltetes Readback wird durch Wiederholung nicht automatisch vertrauenswürdig.

—

# 26.10 Evidenz-Quorum

Evidenzklasse und Quorum sind getrennte Eigenschaften. Aus `E1`, `E2` oder `E3`
folgt kein implizites Mehrheits- oder Fehlertoleranzmodell.

Ein Quorum DARF nur ausgewertet werden, wenn vor `EXECUTE` eine Quorum-Policy an
die Transaktion gebunden wurde. Diese MUSS mindestens die zulässigen Mitglieder,
den Schwellenwert und die erforderliche Unabhängigkeit benennen.

Mehrfachzählung derselben Quelle ist unzulässig. Jede gezählte Evidenz MUSS an
dieselbe Transaktion, dasselbe Subject, dieselbe Execution Identity und – falls
gefordert – dieselbe Challenge/Nonce gebunden sein.

Ohne gebundene Quorum-Policy gilt kein implizites `2/3`-Quorum.

—

# 26.11 Transaktionswiederaufnahme

Eine nicht-terminale Transaktion DARF fortgesetzt werden.

Zustände:

```text
CREATED
SENT
RECEIVED
EXECUTED
OBSERVED
READBACK
VERIFIED
```

sind wiederaufnehmbar.

—

Nicht wiederaufnehmbar:

```text
FAILED
EFFECT_ACK_DONE
```

Formal:

\[
Terminal(TX)
\Rightarrow
Resume(TX)=false
\]

—

# 26.12 Dead-Letter Queue (DLQ)

Ein TEMDD-System SHOULD eine Dead-Letter Queue unterstützen.

Beispiel:

```text
MAX_RETRIES exceeded
```

führt zu:

```text
DLQ_ENTRY_CREATED
```

Eintrag:

```json
{
  "transaction_id": "tx-123",
  "last_error": "READBACK_TIMEOUT",
  "attempts": 5,
  "state": "FAILED"
}
```

—

# 26.13 Retry Audit

Jeder Retry MUSS protokolliert werden.

Beispiel:

```json
{
  "transaction_id": "tx-123",
  "attempt": 3,
  "error": "READBACK_TIMEOUT",
  "timestamp": "2026-09-24T12:01:00Z"
}
```

—

# 26.14 Erweiterte Terminaldefinition

Eine Transaktion erreicht genau einen der beiden terminalen Zustände nach folgender deterministischer Zuordnung:

\[
TEMDD\_SUCCESS(TX)=true
\Rightarrow
State(TX):=EFFECT\_ACK\_DONE
\]

\[
RetryCount(TX) \ge MaxRetries
\lor
Error(TX) \in NonRetryable
\Rightarrow
State(TX):=FAILED
\]

`FAILED` und `EFFECT_ACK_DONE` sind disjunkte terminale Zustände. Nach Eintritt eines terminalen Zustands sind weitere Zustandsübergänge unzulässig.

—

# 26.15 Retry-Axiom

\[
\boxed{
\text{Retries SHALL compensate transient uncertainty, but SHALL NEVER compensate missing trust, authorization, or evidence integrity.}
}
\]

—

# 26.16 Vertrauensaxiom für Fehlerfälle

\[
\boxed{
EVIDENCE\_TAMPERED
\;\lor\;
AUTH\_INVALID
\;\lor\;
ACCESS\_DENIED
\Rightarrow
No\ Retry
}
\]

Ein TEMDD-System darf Unsicherheit durch Wiederholung reduzieren, aber niemals fehlendes Vertrauen, fehlende Berechtigung oder kompromittierte Evidenz durch Retries ersetzen.

Für eine echte **Normativspezifikation** benötigt TEMDD neben den funktionalen Abschnitten einen eigenen Abschnitt mit **Conformance Requirements**. Dieser Abschnitt definiert, welche Eigenschaften eine Implementierung erfüllen MUSS, um sich als *TEMDD 1.1-rc1 conformant implementation* bezeichnen zu dürfen.

—

# 27. Conformance Requirements

## 27.1 Allgemeine Konformität

Ein System DARF sich nur dann als:

```text
TEMDD 1.1-rc1 Compliant
```

bezeichnen, wenn sämtliche MUST-Anforderungen dieser Spezifikation erfüllt werden.

Implementierungen DÜRFEN zusätzliche Funktionen bereitstellen, diese DÜRFEN jedoch die normativen Eigenschaften von TEMDD nicht verletzen.

—

# 28. MUST-Anforderungen

## 28.1 Transaktionsmodell

Eine TEMDD-Implementierung MUSS:

```text
Transaction-ID erzeugen
Subject-ID verwalten
Intent speichern
Akzeptanzkriterien speichern
Evidenz speichern
Endzustand speichern
```

Jede Transaktion MUSS eindeutig identifizierbar sein.

—

## 28.2 Zustandsautomat

Implementierungen MÜSSEN die in Abschnitt 4 normativ definierten Zustände unterstützen:

```text
CREATED
SENT
RECEIVED
EXECUTED
OBSERVED
READBACK
VERIFIED
ACCEPTED
EFFECT_ACK_DONE
FAILED
```

Zusätzliche interne Zustände SIND zulässig.

Zusätzliche terminale Erfolgszustände SIND NICHT zulässig.

—

## 28.3 Evidenzanforderungen

Ein System MUSS:

```text
Freshness prüfen
Binding prüfen
Authentizität prüfen
Verifizierbarkeit prüfen
```

Die Verifikation MUSS fail-closed ablehnen oder HOLD/REOBSERVE liefern, wenn Evidenz diese Bedingungen nicht erfüllt. Ein terminales `FAILED` entsteht nur gemäß der gebundenen Fehler- und Retry-Policy.

—

## 28.4 Verifikation

Ein TEMDD-System MUSS vor dem Erreichen von:

```text
EFFECT_ACK_DONE
```

eine explizite Verifikation durchführen.

Ein reiner:

```text
EXEC_ACK
```

oder

```text
TRANSPORT_ACK
```

DARF niemals zu:

```text
EFFECT_ACK_DONE
```

eskalieren.

—

## 28.5 Authentifizierung

Jeder schreibende API-Zugriff MUSS authentifiziert sein.

Dies betrifft mindestens:

```text
CREATE
EXECUTE
OBSERVE
READBACK
VERIFY
ACCEPT
```

Anonyme Requests MÜSSEN abgelehnt werden.

—

## 28.6 Autorisierung

Vor jeder Operation MUSS geprüft werden:

\[
Authorized(P,S,O)
\]

Fehlt eine gültige Autorisierung, MUSS:

```text
ACCESS_DENIED
```

zurückgegeben werden.

—

## 28.7 Auditierung

Jede sicherheitsrelevante Operation MUSS protokolliert werden.

Mindestens:

```text
Wer
Wann
Welche Aktion
Auf welchem Subject
Mit welchem Ergebnis
```

—

## 28.8 Integrität

Alle sicherheitsrelevanten Datensätze MÜSSEN gegen Manipulation geschützt sein.

Dies betrifft:

```text
Evidenz
Readbacks
Auditdaten
Abschlusszertifikate
```

—

## 28.9 Terminale Immutabilität

Nach:

```text
FAILED
```

oder

```text
EFFECT_ACK_DONE
```

MUSS die Transaktion unveränderlich werden.

Formal:

\[
Terminal(TX)
\Rightarrow
Immutable(TX)
\]

—

## 28.10 Retry-Sicherheit

Retries MÜSSEN idempotent ausgeführt werden.

Ein Retry DARF keine neue fachliche Transaktion erzeugen.

—

# 29. SHOULD-Anforderungen

## 29.1 Digitale Signaturen

Evidenzobjekte SOLLTEN digital signiert werden.

Bevorzugte Verfahren:

```text
Ed25519
ECDSA
RSA-PSS
```

—

## 29.2 Challenge-Response

Implementierungen SOLLTEN Replay-Schutz unterstützen.

Empfohlen:

```text
Challenge
Nonce
Signierter Readback
```

—

## 29.3 Mehrfach-Evidenz

Sicherheitskritische Systeme SOLLTEN mehrere Evidenzquellen verwenden.

Beispiel:

```text
Encoder
+
Strommessung
+
Positionssensor
```

—

## 29.4 Separation of Duties

Kritische Systeme SOLLTEN Rollen trennen:

```text
Operator
Verifier
Approver
```

Eine Person SOLLTE nicht alle Rollen gleichzeitig ausüben.

—

## 29.5 Kryptographische Abschlusszertifikate

Implementierungen SOLLTEN ein signiertes Abschlusszertifikat erzeugen.

Beispiel:

```json
{
  "transaction_id":"tx-123",
  "result":"EFFECT_ACK_DONE",
  "signature":"..."
}
```

—

## 29.6 Evidenzklassifikation

Implementierungen SOLLTEN Evidenz nach Vertrauensniveau klassifizieren:

```text
E1
E2
E3
```

—

## 29.7 Backoff-Verfahren

Retry-fähige Fehler SOLLTEN mit Exponential Backoff verarbeitet werden.

—

## 29.8 Zeitquellen

Implementierungen SOLLTEN vertrauenswürdige Zeitquellen verwenden.

Beispielsweise:

```text
NTP
PTP
GPS-Zeit
Hardware-RTC
```

—

# 30. MAY-Anforderungen

Implementierungen DÜRFEN unterstützen:

```text
Quorum-Evidenz
mehrstufige Workflows
ABAC
RBAC
Zero-Trust-Policies
Hardware Attestation
TPM
HSM
Blockchain-basierte Audit-Logs
```

—

# 31. Konformitätsstufen

## TEMDD Core

MUSS erfüllen:

```text
Transaktionen
Readback
Verifikation
EFFECT_ACK_DONE
Audit
Authentifizierung
Autorisierung
```

—

## TEMDD Enhanced

Zusätzlich:

```text
Digitale Signaturen
Retry-System
Challenge-Response
Evidenzklassen
Abschlusszertifikate
```

—

## TEMDD High Assurance

Zusätzlich:

```text
Mehrfach-Evidenz
Separation of Duties
Hardware Root of Trust
Nichtabstreitbarkeit
Kryptographische Attestierung
```

—

# 32. Konformitätsaxiom

\[
\boxed{
\text{A system SHALL NOT claim TEMDD compliance unless it can demonstrate independent effect verification before issuing EFFECT\_ACK\_DONE.}
}
\]

—

# 33. Referenz-Kernsatz

Dieser Kernsatz ist eine abgeleitete Kurzform der einzigen normativen Erfolgsdefinition aus Abschnitt 23 und führt keine zweite Erfolgsdefinition ein.

\[
\boxed{
State(TX)=EFFECT\_ACK\_DONE
\Rightarrow
Authenticated(P)
\land
Authorized(P,S,O)
\land
Executed(TX)
\land
Observed(TX)
\land
ReadBack(TX,E)
\land
Trusted(Source(E))
\land
Fresh(E)
\land
Bound(E,TX,S)
\land
Causal(E,TX)
\land
Verified(E,C)
\land
Accepted(E,C)
}
\]

Dieser Abschnitt schließt die TEMDD‑1.1‑rc1‑Spezifikation als normatives Regelwerk ab und definiert präzise, welche Anforderungen verpflichtend (MUST), empfohlen (SHOULD) oder optional (MAY) sind.


---

# 34. RC1 Repair-Delta

TEMDD 1.1-rc1 ist ein normativer Closure-Repair des TEMDD-1.1-Drafts. Die fachliche Grundsemantik bleibt unverändert: Transport oder bloße Ausführung begründen keinen Wirkungserfolg; `EFFECT_ACK_DONE` setzt gebundene, frische, kausale, vertrauenswürdige Evidenz sowie Verifikation und Akzeptanz voraus.

RC1 schließt ausschließlich folgende formale Inkonsistenzen:

```text
R01  eine kanonische Erfolgsdefinition
R02  einheitliche Authorized(P,S,O)-Stelligkeit
R03  vollständiges TX-Tupel einschließlich State
R04  vollständige TrustChain einschließlich Authorization, Action und Acceptance
R05  Conformance-Zustände an normativen Zustandsautomaten angeglichen
R06  fehlenden ACCEPT-API-Schritt ergänzt
R07  Äquivalenzrelation transaktionsgebunden
R08  Retry-Terminalzuordnung deterministisch geschlossen
R09  Error Registry um zuvor verwendete, undefinierte Codes geschlossen
R10  EFFECT_ACK und EFFECT_ACK_DONE typologisch getrennt
R11  JSON-Beispiele syntaktisch maschinenlesbar normalisiert
```

Kein Repair-Punkt darf als Nachweis einer konkreten Systemwirkung verstanden werden. Konformität und `EFFECT_ACK_DONE` entstehen ausschließlich durch die in dieser Spezifikation geforderte Ausführung, Beobachtung, frische Rücklesung, Verifikation und Akzeptanz.


---

# 35. Interoperabilität

## 35.1 Ziel

Unterschiedliche TEMDD-1.1-Implementierungen MÜSSEN semantisch interoperabel
sein. Mindestens folgende Artefakte MÜSSEN austauschbar und versioniert sein:

```text
Transaction
Evidence
Readback
Audit Record
Effect Certificate
Verification Policy
Verification Context
```

Interoperabilität bedeutet nicht nur syntaktische Lesbarkeit. Eine
Implementierung DARF Status, Evidenzklasse, Äquivalenzrelation,
Terminalität oder Fehlerkategorie beim Übersetzen nicht umdeuten.

## 35.2 Kanonische Serialisierung

Für kryptographische Identität und Hash-Bindung MUSS TEMDD 1.1 mindestens JSON
Canonicalization Scheme (JCS, RFC 8785) unterstützen.

Deterministische CBOR-Codierung gemäß RFC 8949 DARF als binäres Profil
unterstützt werden.

Protocol Buffers oder andere Adapterformate DÜRFEN für Transport verwendet
werden, gelten aber ohne separat spezifiziertes kanonisches Profil NICHT als
kanonische Hash-Repräsentation.

## 35.3 Version Negotiation

Jede versionierte Nachricht MUSS `temddVersion` oder eine äquivalente
protokollgebundene Versionsangabe tragen. Vor Beginn einer Transaktion MÜSSEN
Version, Schema-Identität, Policy-Version und relevante Algorithmusprofile
feststehen.

Ein Major-Version-Mismatch MUSS fail-closed abgelehnt werden.

## 35.4 Deterministische Verifikation

Zwei Implementierungen MÜSSEN bei identischen vollständigen
Verifikationseingaben zum selben normativen Ergebnis kommen. "Identisch"
umfasst mindestens:

```text
Transaction bytes
Evidence bytes
Verification Policy bytes
Verification Context
Evaluation Time
Trust-root set
Algorithm profile
Canonicalization profile
Acceptance evaluator identities
```

Gleiche Policy allein ist nicht hinreichend, wenn Kontext oder Trust Roots
abweichen.

---

# 36. Zeitmodell

## 36.1 Zeitfelder

Eine Transaktion SOLLTE, soweit die jeweilige Phase erreicht wurde, mindestens
folgende RFC-3339-Zeitpunkte führen:

```text
createdAt
executedAt
observedAt
readbackAt
verifiedAt
acceptedAt
issuedAt
```

## 36.2 Zeitquelle

Die Verification Policy MUSS eine Zeitbasis und die maximal zulässige
Uhrabweichung definieren. Implementierungen SOLLTEN für erhöhte
Assurance-Profile synchronisierte und vertrauenswürdige Zeitquellen verwenden,
z. B. NTP, PTP, GNSS/GPS oder eine attestierte Hardware-Zeitquelle.

## 36.3 Freshness

Die Freshness-Prüfung MUSS gegen einen explizit gebundenen
`evaluationTime` erfolgen und DARF nicht von einem impliziten lokalen
`now` abhängen.

Für `maxAge` gilt:

```text
evaluationTime - capturedAt(E) <= maxAge
```

Falls `requireAfterExecution=true`, MUSS die Evidenz unter Berücksichtigung
des gebundenen `maxClockSkew` mit der Ausführung vereinbar sein.

Zeitstempel allein erzeugen keine Kausalität. Kausalität MUSS zusätzlich durch
Transaction-, Execution- und Subject-Bindung belegt sein.

---

# 37. Formales Zertifikatsmodell

## 37.1 Effect Certificate

Ein Effect Certificate DARF nur ausgestellt werden, wenn
`State(TX)=EFFECT_ACK_DONE`.

Es MUSS mindestens binden:

```text
certificateId
transactionId
subjectId
result
policyId + policyDigest
transactionDigest
evidenceSetDigest
acceptanceScopeDigest
evaluationContextDigest
issuedAt
canonicalization
hashAlgorithm
signerId
keyId
signature
```

## 37.2 Certificate Hash

Der Zertifikathash MUSS über eine kanonische, selbstreferenzfreie Payload
gebildet werden:

```text
certificateHash =
SHA-256(JCS(CertificatePayloadWithoutHashAndSignature))
```

Die Signatur MUSS genau diese gebundene Payload oder deren normativ definierten
Digest schützen.

## 37.3 Offline Verification

Ein Zertifikat MUSS offline prüfbar sein, sofern die gebundenen Policy-Bytes,
Trust Roots, Algorithmusprofile und die zur Prüfung erforderlichen
Evidenz-/Digestobjekte lokal vorliegen.

"Offline prüfbar" bedeutet nicht, dass externe Realität ohne die zugehörige
Evidenz erneut beobachtet wird.

---

# 38. Quorum- und Konsensmodell

Das geforderte Quorum MUSS vor `EXECUTE` definiert und an die Transaktion
gebunden werden.

Zulässige Grundformen sind:

```text
SINGLE       = 1 von 1
K_OF_N       = k von N
MAJORITY     = floor(N/2) + 1
TWO_THIRDS   = ceil(2*N/3)
ALL          = N von N
```

Gezählte Evidenzquellen MÜSSEN eindeutig identifiziert sein. Eine Quelle DARF
nicht mehrfach zählen. Eine Quorum-Policy SOLLTE zusätzlich
Unabhängigkeitsbedingungen für Principals, Geräte oder Trust Domains
definieren.

Ein `2/3`-Ergebnis ist nur dann gültig, wenn die gebundene Policy genau dieses
Quorum fordert und alle gezählten Evidenzen die übrigen Freshness-, Trust-,
Binding- und Verification-Anforderungen erfüllen.

Evidenzklasse (`E1/E2/E3`) und Quorum sind orthogonal: eine höhere
Evidenzklasse ersetzt kein fehlendes Quorum und ein Quorum erhöht nicht
automatisch die Evidenzklasse.

---

# 39. Referenz-Metamodell

TEMDD 1.1 verwendet folgende Kernobjekte:

```text
Principal
Intent
Action
Subject
Evidence
Verification
Acceptance
Certificate
```

Normative Beziehungen:

```text
Principal --authorizes/initiates--> Intent
Intent    --targets-------------> Subject
Action    --executes intent on--> Subject
Evidence  --observes successor--> Subject
Verification --evaluates-------> Evidence + Policy + Context
Acceptance   --decides---------> Verification + Criteria
Certificate  --attests---------> terminal accepted transaction
```

Das Metamodell DARF in UML, SysML, OWL, JSON Schema oder OpenAPI projiziert
werden. Eine Projektion DARF die normativen Beziehungen nicht abschwächen.

---

# 40. Assurance-Profile

Assurance-Profile sind additive Konformitätsprofile und keine bloßen
Marketingbezeichnungen.

## Level 1 — TEMDD Core

MUSS mindestens enthalten:

```text
Authentication
Authorization
Exact Subject Binding
Readback
Verification
Acceptance
Audit
Policy-bound evaluation
```

## Level 2 — TEMDD Enhanced

Zusätzlich zu Level 1:

```text
Digital Signatures
Retry Framework
Challenge/Response
Evidence Classification
Effect Certificates
```

## Level 3 — TEMDD High Assurance

Zusätzlich zu Level 2:

```text
Independent Evidence
Separation of Duties
Hardware Root of Trust or equivalent
Secure/attested Time Source
Hardware Attestation where applicable
```

## Level 4 — TEMDD Critical Systems

Zusätzlich zu Level 3:

```text
Multi-Evidence Quorum
Formal Verification of declared critical invariants
Cryptographic Audit Chain
Explicit Trust-Root Governance
Fail-closed Algorithm/Profile Registry
```

Eine Implementierung DARF ein Level nur beanspruchen, wenn die zugehörige
Conformance Suite auf dem exakt gebundenen Implementierungs-Subject bestanden
wurde.

---

# 41. TEMDD-Hauptsatz

Es gibt genau eine normative Erfolgsdefinition. Die Kurzform ist:

```text
State(TX) = EFFECT_ACK_DONE
iff
TEMDD_SUCCESS(TX, VerificationContext)
```

Dabei gilt:

```text
TEMDD_SUCCESS
iff
Authenticated
AND Authorized
AND ExactSubjectBound
AND PolicyBound
AND Executed
AND Observed
AND ReadBack
AND FreshEvidence
AND TrustedEvidence
AND EvidenceBoundToTransactionAndExecution
AND CausalBindingEstablished
AND VerificationPassed
AND AcceptancePassed
AND RequiredQuorumSatisfied
```

`RequiredQuorumSatisfied` ist für Policies ohne Quorum-Anforderung trivial
wahr.

Daraus folgt:

```text
TRANSPORT_ACK  does not imply EFFECT_ACK_DONE
EXEC_ACK       does not imply EFFECT_ACK_DONE
EFFECT_ACK     does not imply EFFECT_ACK_DONE
EFFECT_ACK_DONE implies an accepted effect under the exact bound scope
```

Die letzte Aussage ist scope-relativ. Sie bedeutet nicht "absolute Wahrheit",
sondern: Die im vorab gebundenen Acceptance Scope geforderte Wirkung wurde mit
der dort vorgeschriebenen Evidenz und Policy erfolgreich nachgewiesen.

## 41.1 Policy-Meta-Axiom

```text
Verification SHALL be policy-driven, not implementation-defined.
```

JSON Schema serialisiert die Struktur der Policy. Dynamische Prädikate wie
Signaturprüfung, Zeitrelationen, Trust-Root-Auflösung, Quorum und
domänenspezifische Acceptance werden durch den normativen Policy-Evaluator
ausgeführt; JSON Schema allein beweist diese Laufzeiteigenschaften nicht.


---

# 42. Maschinenlesbare normative Artefakte

TEMDD 1.1-rc1 bindet die abstrakte Normativsemantik zusätzlich an maschinenlesbare Referenzartefakte:

```text
schemas/temdd-transaction-v1.1.schema.json
schemas/temdd-evidence-v1.1.schema.json
schemas/temdd-readback-v1.1.schema.json
schemas/temdd-effect-certificate-v1.1.schema.json
schemas/temdd-error-v1.1.schema.json
schemas/temdd-verification-policy-v1.1.schema.json
schemas/temdd-verification-context-v1.1.schema.json
spec/temdd/api/TEMDD_OPENAPI_1_1.yaml
spec/temdd/api/TEMDD_ASYNCAPI_1_1.yaml
spec/temdd/TEMDD_SECURITY_PROFILES_V1_1.md
spec/temdd/TEMDD_VERIFICATION_POLICY_V1_1.md
spec/temdd/conformance/TEMDD_VERIFICATION_POLICY_TEST_VECTORS_V1_1.json
```

JSON Schema validiert Struktur und statische Constraints. Freshness, Signaturprüfung, Trust-Root-Auflösung, Kausalbindung, Quorum und domänenspezifische Acceptance bleiben Laufzeitprädikate des normativen Policy-Evaluators. Eine Implementierung DARF Schema-Validität nicht als Wirkungsnachweis oder `EFFECT_ACK_DONE` behandeln.
