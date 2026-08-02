# Direkter API-Ausführungsvertrag

## Zweck

Dieser Vertrag verhindert unnötige Statusschleifen zwischen einem autorisierten Auftrag und einer über die offiziell verfügbare GitHub-API tatsächlich möglichen Repository-Wirkung.

## Grundregel

Wenn ein Auftrag eindeutig autorisiert ist und die verbundene GitHub-API die notwendige Operation bereitstellt, wird die Operation ausgeführt. Es wird nicht behauptet, eine Fähigkeit fehle, bevor die verfügbaren API-Funktionen geprüft wurden.

## Ausführungsfolge

1. Kanonischen Entrypoint und aktuelle Repository-Bindungen lesen.
2. Erwartete Base- und Head-Leases rebeobachten.
3. Verfügbare API-Fähigkeiten für Lesen, Branch, Datei, Pull Request, Workflow und Kommentar prüfen.
4. Den kleinsten historienerhaltenden Effekt ausführen.
5. Exakte resultierende Commits und Pull Requests zurückgeben.
6. Repository-native Materialisierung und Gates auslösen oder einen Verification-PR auf identischem Head erzeugen.
7. Erst nach terminaler Evidenz Promotion oder externe Effekte disponieren.

## Keine Scheinblocker

Ein lokaler Container ohne `gh`, DNS oder Checkout ist kein Repository-Blocker, wenn dieselbe Wirkung vollständig und sicher über die verbundene GitHub-API möglich ist.

Ein echter Blocker liegt nur vor, wenn mindestens eine für den autorisierten Effekt notwendige Fähigkeit weder repository-nativ noch über die verfügbare API ausführbar ist.

## Wahrheitsgrenzen

- Kein Merge ohne ausdrückliche Autorisierung.
- Keine Zenodo- oder IETF-Mutation ohne separate, artefaktgebundene Autorisierung und verfügbaren Transport.
- Keine Behauptung von PASS, FINAL_PASS oder EFFECT_ACK_DONE ohne vollständige Evidenz.
- Keine manuelle Nachbildung generator-eigener Outputs, wenn repository-native Materialisierung verfügbar ist.
- Keine Statusquittierung als Ersatz für eine mögliche technische Wirkung.

## Persistenz

Diese Datei ist eine menschenlesbare Betriebsregel. Die zugehörige maschinenlesbare Work Unit befindet sich unter `work-units/QIKVRT_P1_HISTORICAL_RECONSTRUCTION.json`.
