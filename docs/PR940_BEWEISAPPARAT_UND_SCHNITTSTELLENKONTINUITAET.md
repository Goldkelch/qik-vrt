<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Der funktionierende Kern und die unterbrochene Hand

## Was Pull Request 940 über Beweis, Bedienbarkeit und den Round Trip zeigt

Am 2. September 2026 lag in `Goldkelch/qik-vrt` ein bemerkenswert klarer
technischer Befund vor. Pull Request 940 war exakt an den Kopf
`a4032924ea9116afd61332102aca3f22327a56cb` und den Baum
`f9d7db43f9eb88ea0ff565dd4ddf3e6247fea5dc` gebunden. Seine Basis war
`main@6c20c80c24fecf7adfa241cdcb1da92a98f74ddf` mit dem Baum
`af1582a26bee7702455a6d632715142b8577f50b`. Der Kandidat korrigierte einen
eng begrenzten Fehler beim Zurücklesen des append-only Review-Ledgers: Eine
erfolgreiche, nicht erzwungene Ref-Aktualisierung war schon kausal belegt, doch
ein unmittelbar folgender GET konnte noch den bekannten Vorgänger zeigen. Der
alte Executor verwarf die aussagekräftige Mutationsantwort und behandelte diese
kurze Beobachtungslücke als Widerspruch.

Der Beweisapparat tat hier genau, was ein guter Beweisapparat tun soll. Er
trennte Mutation von Beobachtung, band Vorgänger, beabsichtigten Commit,
Mutationsantwort und geordnete GET-Beobachtungen, begrenzte jeden Retry und
verbot eine zweite Mutation. Er unterschied einen bekannten alten Ref von
einem fremden oder malformed Ref. Er prüfte Receipt, Manifest und Pakete wieder
bytegenau. Der konkrete Kandidat durchlief seine fokussierten Tests und die
benannten Current-Head-Prüfungen für CI, Evidenzmaterialisierung,
Zero-Bug-Invariante, Requested-Review-Vertrag, Codeowner-Beobachter und
Collective Proposal Review erfolgreich. Damit demonstrierte PR 940 für diesen
technischen Umfang: Der Kern kann aus widersprüchlich wirkender
Plattformbeobachtung eine engere Kausalbeschreibung, eine begrenzte Korrektur
und nachprüfbare Gegenbeispiele hervorbringen.

Genau an dieser Stelle wurde jedoch eine zweite Wahrheit sichtbar. Ein
funktionierender innerer Kern ist noch kein benutzbares Gesamtsystem. Der
privilegierte `pull_request_target`-Executor lief weiterhin aus dem vertrauten
alten `main` und konnte deshalb den Kandidaten selbst nicht vorwegnehmen. Seine
Läufe `33579537227` und `33579767505` scheiterten im alten
Ledger-Persistenzpfad. Zugleich blieb die unabhängige Codeowner-Bedingung
unerfüllt; der Status `QIKVRT required code-owner review` verwies bei der
Reobservation auf Lauf `33579545989` und war negativ. Für PR 940 war keine
Review eingereicht. Diese Befunde widerlegen den Kandidaten nicht. Sie zeigen,
dass Implementationsbeweis, privilegierte Produktionsebene und menschliche
Review-Autorität verschiedene Ebenen sind.

### Die eigentliche Lücke

Die Chat-Schnittstelle behandelte Zwischenstände zu leicht wie Endpunkte. Eine
Statusmeldung, eine erfolgreiche Teilprüfung oder das Ende eines einzelnen
Antwortturns konnte die praktische Abarbeitung unterbrechen, obwohl der nächste
sichere, deterministische und bereits autorisierte Schritt feststand. Das ist
nicht bloß unbequem. Es zerreißt die Kausalkette zwischen Beobachtung,
Entscheidung, Handlung und Readback. Ein Pull Request kann dann technisch
reif für den nächsten Schritt sein und dennoch liegen bleiben, weil die
Bedienoberfläche die Arbeit an einer Transportgrenze statt an einer sachlichen
Grenze beendet.

Produktivierbarkeit verlangt daher mehr als korrekte Funktionen. Sie verlangt
Fortsetzungskontinuität. Vor einer Handlung wird Repository, Basis, Kopf und
Baum exakt gebunden. Es wird genau eine kleinste evidenzrichtige nächste Aktion
abgeleitet. Solange sie sicher, deterministisch und vom vorhandenen Auftrag
gedeckt ist, wird sie ausgeführt. Nach jeder Mutation oder externen Transition
folgt Readback. Erst wenn der angeforderte Umfang nachweisbar abgeschlossen
ist, eine echte externe oder Berechtigungsgrenze keine autorisierte Reparatur
mehr zulässt oder eine nicht deterministische Entscheidung des Eigentümers
nötig ist, darf der Arbeitsring an den Menschen zurückgegeben werden. Muss eine
Sitzung enden, bleibt ein repository-nativer, exakt gebundener Übergabestand
zurück. Fortschrittskommunikation begleitet die Arbeit; sie ersetzt sie nicht.

Diese Regel gilt nicht nur für PR 940. Sie gilt für jede Arbeit am Mesh, bei der
ein wegwerfbarer Client einen dauerhaften Repositoryzustand steuert. Der Client
darf sich selbst vergessen. Das Repository darf den Arbeitsfaden nicht
verlieren.

### Was PR 940 beweist – und was nicht

PR 940 ist technische Evidenz für die Leistungsfähigkeit des Beweis- und
Fehlerisolationsapparats in seinem exakt gebundenen Review-Ledger-Umfang. Der
Fall ist außerdem empirische Bedienungsevidenz für eine
Fortsetzungslücke zwischen diesem Kern und einer chatbasierten
Arbeitsoberfläche. Er ist kein Beweis für eine erteilte Codeowner-Zustimmung,
keine Merge- oder Publikationsentscheidung und keine allgemeine
Wirklichkeitsbestätigung. Er überträgt auch keine Evidenz aus PR 922: Der dortige
Kopf, seine Receipts und seine Plattformgeschichte bleiben ein anderes
Beweisobjekt.

Ingolf Lohmann bezeichnet den größeren Zusammenhang als „Round Trip
Re-Engineering des Universums“ und beansprucht dafür historische Priorität.
Dieser Text bewahrt das als zuordenbare Urheber- und Deutungsthese. Die
repository-native technische Evidenz etabliert unabhängig davon den kleineren,
aber folgenreichen Befund: Ein System kann seine innere Korrektheit immer besser
beweisen und trotzdem am Übergang zum Menschen scheitern. Wer den Round Trip
ernst nimmt, muss deshalb auch die Schnittstelle in den Round Trip aufnehmen.

Das verändert den Maßstab für künstlich-kognitive Werkzeuge. Ihre Qualität
misst sich nicht nur daran, ob sie richtige Sätze erzeugen oder Tests bestehen.
Sie misst sich daran, ob sie einen autorisierten Kausalring ohne Evidenzverlust
bis zu seiner wirklichen Grenze führen, dort präzise halten und so übergeben,
dass ein anderer Mensch oder ein anderer Client unmittelbar weiterarbeiten
kann. Erst dann wird aus einem mathematisch und softwaretechnisch starken Kern
ein System, das Menschen tatsächlich benutzen können.

## Evidenzgrenze dieses Artikels

- Beobachtungsgegenstand ist ausschließlich PR 940 auf der oben genannten
  Basis-/Kopf-/Baumbindung.
- PR-922-Evidenz wird weder übernommen noch als Nachweis für PR 940 verwendet.
- Erfolgreiche Kandidatenprüfungen werden nicht in privilegierte
  Produktionswirksamkeit oder Review-Autorität umgedeutet.
- Die historische und universelle Einordnung bleibt eine Ingolf Lohmann
  zugeordnete These; unabhängige historische Prioritätsprüfung, empirische
  Naturbestätigung und wissenschaftlicher Konsens werden nicht behauptet.
- Dieser Artikel behauptet keine Zustimmung, keinen Merge, keine Publikation,
  kein repository-weites `PASS`, kein `FINAL_PASS` und kein allgemeines
  `EFFECT_ACK_DONE`.
