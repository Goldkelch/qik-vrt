# QIK-VRT E-Mail-Infrastruktur: Karlsruhe 1984 bis Cloud V1

## Auftrag und präziser historischer Ausgangspunkt

QIK-VRT bewahrt die Entwicklung der E-Mail nicht als lose Produktliste, sondern als durchgängige, prüfbare Fähigkeitsschichtung.

Der gebundene Ausgangspunkt ist die erste **direkte Internet-E-Mail an einen getrennten, deutschlandweit erreichbaren E-Mail-Server**. Laura Breeden sandte die Nachricht am 2. August 1984 um 12:35 US-Ortszeit vom CSNET Coordination and Information Center bei BBN in Boston. Sie erreichte Werner Zorn und Michael Rotert in Karlsruhe am 3. August 1984 um 10:14 Ortszeit unter `zorn@germany.csnet` und `rotert@germany.csnet`. Der überlieferte Pfad führte über CSNET-SH und ein CSNET-Relay; die Nachricht wurde in Karlsruhe manuell abgerufen.

Diese Qualifizierung ist verbindlich: Elektronische Nachrichten wurden in Deutschland schon vorher genutzt. Der historische Claim wird nicht zu „erste E-Mail jeder Art in Deutschland“ erweitert.

Primärquellen:

- <https://www.kit.edu/kit/english/pi_2009_090.php>
- <https://www.kit.edu/kit/english/pi_2014_15153.php>

## Eine Infrastruktur, achtzehn getrennte Schichten

```text
ADDRESS_AND_IDENTITY
→ MESSAGE_FORMAT
→ MIME_CONTENT
→ MAIL_USER_AGENT
→ MESSAGE_SUBMISSION_AGENT
→ MAIL_TRANSFER_AGENT
→ DNS_MX_ROUTING
→ QUEUE_RETRY_AND_DSN
→ MAIL_DELIVERY_AGENT
→ MAILBOX_STORE
→ POP_IMAP_JMAP_ACCESS
→ WEBMAIL_AND_MOBILE_CLIENT
→ DOMAIN_AUTHENTICATION
→ TRANSPORT_CONFIDENTIALITY
→ END_TO_END_SECURITY
→ ABUSE_MALWARE_AND_POLICY
→ ARCHIVE_E_DISCOVERY_AND_RETENTION
→ EVENTING_OBSERVABILITY_AND_EFFECT_ACK
```

Keine Schicht darf die Aussage einer späteren Schicht vorwegnehmen. Insbesondere ist die Annahme durch einen SMTP-Server noch keine Speicherung im Zielpostfach, eine Speicherung noch keine Synchronisation zum Client, eine Darstellung noch kein menschliches Lesen und eine Lesebestätigung noch kein QIK-VRT Effect Acknowledgement.

## Protokoll- und Kompatibilitätslinie

Die gebundene Linie umfasst:

1. SMTP und das ARPA/Internet-Nachrichtenformat der RFC-821/RFC-822-Generation;
2. CSNET-Relay und manuell abgerufene Serverzustellung;
3. DNS-MX-Routing, UUCP-Austausch und X.400/RFC-822-Gateways;
4. MIME, POP3 und IMAP;
5. modernes SMTP, getrennte Message Submission und internationalisierte Nachrichten;
6. SPF, DKIM, DMARC und ARC als Domain- beziehungsweise Weiterleitungsnachweise;
7. TLS-first Submission und Zugriff, MTA-STS, TLS Reporting und optional DANE;
8. IMAP4rev2 sowie JMAP Core und JMAP Mail für synchronisierte, API-fähige Mailboxen.

Die 24 aktuell gebundenen Standards stehen maschinenlesbar in `policy/QIKVRT_EMAIL_INFRASTRUCTURE_V1.json`. Historische Standards bleiben als Kompatibilitäts- und Provenienzschicht erhalten; sie sind keine Erlaubnis, unsichere Klartext- oder Legacy-Authentifizierung in einer neuen produktiven Installation wieder einzuführen.

## Cloud-Varianten

Die Architektur schließt folgende Klassen vollständig ein:

```text
SAAS_MAILBOX
HOSTED_SMTP_IMAP
API_FIRST_MAILBOX
TRANSACTIONAL_OUTBOUND
INBOUND_PROCESSING
CLOUD_SMTP_RELAY
SECURE_EMAIL_GATEWAY
HYBRID_ON_PREM_CLOUD
PRIVATE_CLOUD_SELF_HOSTED
CONTAINER_ORCHESTRATED
SERVERLESS_EVENT_DRIVEN
MULTI_CLOUD_FAILOVER
EDGE_ROUTING_WORKER
SOVEREIGN_REGULATED_CLOUD
END_TO_END_ENCRYPTED_CLOUD
CLOUD_ARCHIVE_E_DISCOVERY
```

Provider werden ausschließlich als Host-Adapter eingesetzt. Die kanonische QIK-VRT-Semantik bleibt providerneutral:

- Google Workspace/Gmail: SMTP Relay, Gmail API und Pub/Sub-gebundene Mailbox-Watches;
- Microsoft 365/Exchange Online: Mail Flow, Microsoft Graph und Change-Notification-Webhooks;
- Amazon SES: SMTP- oder API-Versand sowie regelbasierte Inbound-Verarbeitung;
- Cloudflare Email Service: MX-Routing, Email Workers und transaktionaler Versand;
- JMAP-kompatible Dienste: standardisierte Synchronisation, Suche, Submission und Push.

Ein Adapter erhält weder Repository-Authority noch Rechte an Nachrichten oder Artefakten. Zugangsdaten bleiben außerhalb von Repository, Receipts und M68000-Kapseln.

## Ereignismodell

Der reguläre Betrieb ist ausschließlich ereignisgetrieben:

```text
PROVIDER_EVENT / SMTP_EVENT / QUEUE_EVENT / WEBHOOK
→ BIND_PROVIDER_EVENT_ID
→ RESOLVE_EXACT_DELTA
→ NORMALIZE_WITHOUT_MESSAGE_BODY_TELEMETRY
→ SELECT_BOUNDED_ROUTE
→ EXECUTE_OR_HOLD_IN_HOST_ADAPTER
→ REOBSERVE_PROVIDER_OR_MAILBOX_STATE
→ APPEND_RECEIPT
```

Periodisches Polling ist kein fachlicher Betriebsmodus. Zeitlich begrenzte Watch- oder Subscription-Erneuerung darf nur eine Lease erhalten und keine Mailverarbeitung auslösen. Erst ein beobachtetes Ereignis oder eine erkannte Cursor-/History-Lücke aktiviert die exakt begrenzte Delta-Reconciliation.

Receipts bilden mindestens die Zustände:

```text
COMPOSED
PREPARED
SUBMITTED
SMTP_ACCEPTED
RELAYED
REMOTE_MTA_ACCEPTED
MAILBOX_STORED
MAILBOX_CHANGE_NOTIFIED
CLIENT_SYNCHRONIZED
RENDERED
OPTIONAL_READ_RECEIPT
EFFECT_PREPARED
EFFECT_COMMITTED
EFFECT_REOBSERVED
```

Die Historie ist append-only. Korrekturen erzeugen Nachfolgerreceipts und überschreiben keine früher versiegelten Zustände.

## Wahrheits- und Sicherheitsgrenzen

```text
RFC5321_ENVELOPE != RFC5322_CONTENT
MESSAGE_SUBMISSION != SMTP_RELAY != FINAL_DELIVERY
SMTP_250 != MAILBOX_STORED
MAILBOX_STORED != CLIENT_SYNCHRONIZED
CLIENT_SYNCHRONIZED != RENDERED
RENDERED != HUMAN_READ
READ_RECEIPT != EFFECT_ACK
TRANSPORT_ACK != EFFECT_ACK
WEBHOOK_NOTIFICATION != MAILBOX_DELTA
CLOUD_EVENT != MESSAGE_CONTENT
SPF_DKIM_DMARC != NATURAL_PERSON_AUTHENTICATION
TLS_TRANSPORT != END_TO_END_CONTENT_CONFIDENTIALITY
M68000_ROUTE_DECISION != NETWORK_EFFECT
```

Neue Submission- und Zugriffspfade sind TLS-gebunden. Domain-Authentifizierung, Transportverschlüsselung, optionale Ende-zu-Ende-Verschlüsselung, Malware-/DLP-Prüfung und Retention bleiben getrennte Verträge. Telemetrie und Route-Receipts speichern keine Nachrichtentexte; zulässig sind nur Digests und minimal erforderliche Metadaten.

## Motorola-68000-Mikrokern

`email_route_select_v1` konsumiert einen einzigen endlichen Flag-Byte-Zustand:

| Bit | Bedeutung |
|---:|---|
| 0 | Envelope gültig |
| 1 | Route aufgelöst |
| 2 | TLS-Policy erfüllt |
| 3 | Content-Policy frei |
| 4 | Domain-Authentifizierung ausgerichtet |
| 5 | wiederholbarer Abhängigkeitsfehler |
| 6 | zusätzliche Authority erforderlich |
| 7 | Authority vorhanden |

Die Ausgabe verwendet den bestehenden QIK-VRT-Vierzustands-ABI:

```text
D0=0 COMPLETE_ACCEPT_ROUTE
D0=1 HOLD
D0=2 REOBSERVE_RETRY
D0=3 REQUEST_AUTHORITY
```

D1 ist der Abschlusszeuge, D2 markiert maschineneigene Reobservation, D3 bleibt byteidentisch. Der Compiler materialisiert 82 M68000-Bytes. Referenzmodell und Maschinenpfad werden über `256 × 256 = 65.536` Flag-/D3-Paare verglichen.

Der Kern entscheidet nur. SMTP, DNS, Mailbox, Provider-API, Credentials und Effect-Reobservation bleiben Host-Adapter-Aufgaben.

## Umsetzungspfad

```text
V1  LINEAGE + CLOUD TAXONOMY + EVENT CONTRACT + M68000 ROUTE CORE
V2  CANONICAL RFC5322/MIME OBJECT + CONTENT-ADDRESSING + MAILDIR STORE
V3  SMTP SUBMISSION/TRANSFER + QUEUE/RETRY/DSN + DNS MX
V4  IMAP4REV2 + JMAP CORE/MAIL + PUSH
V5  SPF/DKIM/DMARC/ARC + MTA-STS/TLS-RPT + OPTIONAL DANE
V6  GMAIL + MICROSOFT GRAPH + AWS SES + CLOUDFLARE ADAPTERS
V7  HYBRID/MULTI-CLOUD ROUTING + FAILOVER + REPLAY CONTROL
V8  FIREFOX EFFECT-ACK CLIENT + OPERATING-SYSTEM/TRANSPORT INTEGRATION
V9  OCI APPLIANCE + CLOUD DEPLOYMENT + PUBLIC REOBSERVATION
V10 ARCHIVE/E-DISCOVERY + SOVEREIGN/ENCRYPTED VARIANTS + HARDWARE REVIEW
```

Jede Stufe bleibt exact-head-, exact-tree- und scope-gebunden. Ein Adapter wird erst wirksam, wenn seine Credentials, Providerbedingungen, DNS-Authority, Tests und post-effect Reobservation separat vorliegen.

## Gegenwärtige Grenze

V1 ist eine ausführbare Architektur- und Entscheidungstranche. Sie sendet oder empfängt keine produktive Nachricht, ändert keine DNS-/MX-Zone, eröffnet kein Cloud-Konto, akzeptiert keine Providerbedingungen, überträgt keine Rechte und behauptet weder vollständige Produktionsbereitschaft noch `PASS`, `FINAL_PASS` oder allgemeines `EFFECT_ACK_DONE`.

Refs #856.
