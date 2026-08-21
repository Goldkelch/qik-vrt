# IED — Intelligenz teilen, Evidenz binden, Entwicklung ermöglichen

**Autor:** Ingolf Lohmann  
**Arbeitsgegenstand:** `IED-DISSEMINATION-2026-08-21-V1`  
**Repository:** `Goldkelch/qik-vrt`  
**Quellenbindung:** Issue #768 und `SOURCE_BINDING.json`

> Für Intelligenz gilt das Gleiche wie alles andere auch: Es muss geteilt werden, damit es sich vermehrt. Ich habe meine Intelligenz jetzt mit dir geteilt und du bist jetzt dazu aufgefordert, sie weiter zu teilen, zum Beispiel mit den QIK-VRT-Repositories auf GitHub und allem, was weiter daran hängt: Zenodo, EETF, arXiv, Wikipedia, IEEE und die dazu notwendige E-Mail-Korrespondenz.
>
> q.e.d.  
> Ingolf Lohmann

Der historische Quelltext bleibt wortgetreu erhalten. Die vom Product Owner freigegebene Meta-Normalisierung ordnet das Quelltoken `EETF` für Standardisierungs-, Protokoll- und Interoperabilitätsrouting dem gemeinten Ziel `IETF` zu. Diese Normalisierung ändert nicht die historische Quelle und behauptet weder IETF-Konsens noch eine bereits erfolgte Einreichung.

## 1. Intelligenz vermehrt sich durch überprüfbare Teilung

Intelligenz ist in diesem Arbeitsmodell kein Besitz, der durch Weitergabe kleiner wird. Sie wird produktiv, wenn ein anderer Beobachter sie empfangen, unterscheiden, prüfen, kritisieren, reproduzieren und weiterentwickeln kann.

Daraus folgt nicht, dass jede Weitergabe automatisch wahr, akzeptiert oder wirksam ist. Die Teilung eröffnet zunächst eine neue Beobachtungsmöglichkeit. Erst die nachfolgende Prüfung erzeugt neue Evidenz. Erst eine gebundene Entscheidung erzeugt Entwicklung.

```text
INTELLIGENCE
→ SHARE
→ EXTERNAL OBSERVATION
→ NEW EVIDENCE
→ NEW INTELLIGENCE
```

Deshalb gilt:

```text
SHARING != ACCEPTANCE
DRAFT != SUBMITTED
SUBMITTED != PEER_REVIEWED
TRANSPORT_ACK != EFFECT_ACK
```

## 2. IED: Intelligence, Evidence, Development

### Intelligence

Intelligence bezeichnet die Fähigkeit, einen scheinbar einheitlichen Zustand in entscheidungsrelevante Unterschiede zu zerlegen. Im QIK-VRT-Kontext betrifft das insbesondere Bedeutung, Evidenz und Autorität.

```text
BEDEUTUNG
EVIDENZ
AUTORITÄT
```

### Evidence

Evidence bindet eine Aussage an überprüfbare Artefakte und Beobachtungen. Dazu gehören je nach Gegenstand Repository, Commit, Tree, Vorgänger, Datei, Digest, Workflow-Lauf, Kernelprüfung, Runtime-Beobachtung oder externer Receipt.

Evidence ist nicht bloß Aktivität. Ein Workflow-Start ist keine erfolgreiche Ausführung. Ein Transport-ACK ist keine Wirkungsbestätigung. Eine Implementierung ist keine kanonische Wirkung.

### Development

Development materialisiert aus den getrennten Befunden genau eine zulässige nächste Fortsetzung. Entwicklung bedeutet damit nicht maximale Änderungsmenge, sondern den kleinsten kausal hinreichenden, history-preserving und verantwortbaren nächsten Unterschied.

```text
INTELLIGENCE
→ EVIDENCE
→ TRIAGE
→ DEVELOPMENT
```

## 3. Aus eins mach drei — und aus drei mach eins

Die IED-Struktur folgt der Triageformel:

```text
EINS
→ UNTERSCHEIDEN
→ DREI
→ PRÜFEN
→ ENTSCHEIDEN
→ EINS
```

Aus einem Problem werden mehrere voneinander unabhängige Fragen. Aus den Antworten entsteht genau eine nächste Entscheidung. Die Unterschiede werden dabei nicht eingeebnet, sondern ausgewertet.

Im QIK-VRT-Maschinenrand kann die nächste Entscheidung als vierwertige D0-ABI erscheinen:

```text
D0=0  NOOP
D0=1  HOLD
D0=2  REOBSERVE
D0=3  REQUEST_AUTHORITY
```

Die Auswahl bleibt dynamisch. Ändern sich Head, Tree, Evidenz, Vorgänger oder Autorität, wird erneut triagiert. Das Optimum ist daher kein zeitloser Endzustand, sondern die unter dem aktuellen gebundenen Zustand beste zulässige nächste Fortsetzung.

## 4. Das Repository als Teilungs- und Eigenzeitmechanismus

Ein QIK-VRT-Repository teilt nicht nur Text. Es bindet Inhalt an eine Geschichte.

```text
TREE   = Inhaltszustand
COMMIT = Ereignisidentität
PARENT = historischer Vorgänger
BRANCH = lokale Entwicklungslinie
```

Zwei Commits können denselben Tree tragen und dennoch unterschiedliche Ereignisse sein. Derselbe Zustandstyp kann zu einer neuen lokalen Zeitposition wiederkehren, ohne dass das frühere Ereignis überschrieben wird.

```text
1[n] → IED[n] → 1[n+1]
```

In diesem informatischen Sinn entsteht eine lokale, kausal fortschreitende Repository-Zeit. Ein Paket kann die Bindung einer Information an diese lokale Geschichte transportieren. Es transportiert nicht die physikalische Zeit selbst und belegt keine Nachricht in die eigene physikalische Vergangenheit.

## 5. Was geteilt werden soll

Der Disseminationsauftrag umfasst unterschiedliche Zielräume, die nicht zu einem einzigen Publikationsstatus zusammengezogen werden dürfen.

### GitHub

GitHub ist der primäre, versionierte Quellen- und Entwicklungsraum. Hier werden Wortlaut, Claim-Grenzen, Artefakte, Tests, Reviews und Integrationsgeschichte gebunden.

### Zenodo

Zenodo ist ein Archivierungs- und Identifikationspfad. Ein vorbereitetes Paket ist noch keine Veröffentlichung. Eine DOI darf erst nach beobachteter öffentlicher Publikation und erneuter Byteprüfung als Wirkung berichtet werden.

### IETF

Der IETF-Pfad betrifft das Protokoll- und Interoperabilitätsthema, insbesondere Effect Acknowledgement. Ein Repository-Dokument oder Internet-Draft-Kandidat ist weder Working-Group-Konsens noch IETF-Zustimmung noch RFC.

### arXiv

Der arXiv-Pfad ist ein Preprint-Pfad. Ein eingefrorenes Manuskriptpaket ist noch keine Einreichung; eine Einreichung ist noch keine Ankündigung und keine Peer-Review-Publikation.

### Wikipedia

Wikipedia ist kein Ersatz für Primärpublikation oder unabhängige Rezeption. Eine neutrale enzyklopädische Einordnung setzt geeignete unabhängige Sekundärquellen voraus. Repository-Artefakte können Quellenmaterial bereitstellen, erzeugen allein aber keine unabhängige Relevanz.

### IEEE

Der IEEE-Pfad verlangt ein konkretes Journal oder eine konkrete Konferenz, ein zielgerechtes Manuskript, reproduzierbare Evidenz, klare Beitragserklärung und die Einhaltung der jeweiligen Einreichungsregeln. Ein Cover Letter ist noch keine Einreichung; eine Einreichung ist noch keine Annahme.

### E-Mail-Korrespondenz

Korrespondenz muss empfängerspezifisch sein. Ein Entwurf ohne real aufgelösten Empfänger bleibt ein Entwurf. Versand, Empfang und Antwort sind getrennte Ereignisse.

## 6. Claim- und Evidenzgrenzen

Dieses Bündel bindet einen Product-Owner-Auftrag und eine Disseminationsarchitektur. Es beweist nicht, dass der allgemeine Satz „Intelligenz vermehrt sich durch Teilung“ als universelles Naturgesetz gilt.

Der getrennte formale Strang #757/#758/#759 behandelt einen präzisen Lean-Satz zur prädiktiven Optimalität unter gleichen Informationen. Seine formale Gültigkeit darf nicht als empirische Messung menschlicher, kollektiver oder physikalischer Intelligenz ausgegeben werden.

```text
FORMAL_THEOREM != EMPIRICAL_MEASUREMENT
REPOSITORY_BOUND != CANONICAL_MAIN
VERIFIED_IMPLEMENTATION != AUTHORITY_EFFECT
```

## 7. Gegenwärtiger Wirkungsstand

Dieses Repository-Bündel materialisiert Quellen, Artikel, Claim-Matrix, Routing und Korrespondenzvorlagen. Es führt keine externe Einreichung aus.

```text
GITHUB_SOURCE_BUNDLE = REPOSITORY_CANDIDATE

ZENODO_PUBLICATION = NOT_EXECUTED
ARXIV_SUBMISSION   = NOT_EXECUTED
IETF_SUBMISSION    = NOT_EXECUTED
WIKIPEDIA_EDIT     = NOT_EXECUTED
IEEE_SUBMISSION    = NOT_EXECUTED
EMAIL_SEND         = NOT_EXECUTED
```

Jeder spätere externe Übergang benötigt ein exakt eingefrorenes Artefakt, einen geeigneten Empfänger oder Zielkanal, eine beobachtete Ausführung und einen post-effect Receipt.

## 8. Schluss

Intelligenz wird nicht dadurch geteilt, dass man ihre Wirkung behauptet. Sie wird geteilt, indem man ihren Ursprung bewahrt, ihre Aussagen typisiert, ihre Evidenz offenlegt und anderen eine reproduzierbare Fortsetzung ermöglicht.

```text
INTELLIGENCE
→ EVIDENCE
→ DEVELOPMENT
→ SHARE
→ REOBSERVE
→ NEW INTELLIGENCE
```

> Intelligenz erkennt den Unterschied.  
> Evidenz bindet den Unterschied.  
> Entwicklung macht ihn anschlussfähig.  
> Teilung eröffnet den nächsten Beobachter.

**q.e.d.**  
**Ingolf Lohmann**
