# Empirische Rückkopplung: Artikel und Kooperationsdemonstrator

Publikationskennung: `qikvrt-empirical-feedback-20260920-v1`.

Die Fassung enthält einen wissenschaftlichen Diskussionsbeitrag, eine gut vorlesbare Prosa und einen offenen Brief an Gunter Dueck. Die Originalerklärung Ingolf Lohmanns bleibt erhalten. Philosophische Ausgangsthesen, Gestaltungsentscheidungen, beobachtete Softwareergebnisse und offene Forschungsfragen werden in `CLAIM_MATRIX.json` getrennt zugeordnet. Vollständig künstliche Daten werden nicht als Beobachtungen an Menschen ausgegeben.

## Lesen

- `ARTICLE_SCIENTIFIC_DE.md` und `QIKVRT_Empirische_Rueckkopplung_Fachartikel.pdf`.
- `ARTICLE_PUBLIC_DE.md`, `QIKVRT_Die_Welt_antwortet.pdf` und die zugehörige TXT-Lesefassung.
- `OPEN_LETTER_DUECK_DE.md`, `QIKVRT_Offener_Brief_Gunter_Dueck.pdf` und TXT.
- `CHANGE_NOTICE.md`: konkrete Präzisierungen gegenüber dem Original.

Der Brief ist als Veröffentlichungstext vorbereitet. Dieser Auftrag versendet keine E-Mail. Der bisherige E-Mail-Text wurde separat um die neue Brieffassung ergänzt; sein technischer Hintergrundartikel bleibt erhalten.

## Reproduzieren

`REPRODUCTION_PACKAGE.zip` enthält den im vorausgehenden Arbeitsschritt bereitgestellten Demonstrator unverändert. Seine ausführbaren Quellen liegen außerdem unter `experiments/cooperation/`. Der native QIK-VRT-Vergleich ist an Commit `a86054139b49c13c5cd344753b248b46b5daf66f` und Tree `feff1cae2401a3df83febc3b9458de70d79b818e` gebunden. Der neue Anwendungsadapter und der enthaltende Publikationscommit sind gesonderte Gegenstände.

Die aktuelle Fassung enthält erneut ausgeführte Komponententests und Beispieldurchläufe in `validation/COMPONENT_RUNS.json`. Erfolgreiche Tests beziehen sich auf die dokumentierten Dateien und Testfälle. Eine Prüfung aller Repository-Release-Bedingungen wird nicht behauptet.

## Publikationsweg

Die bestehende Policy `policy/zenodo-machine-proof-policy-v2.json` verlangt einen an identische Dateien gebundenen Rückgabebeleg und eine zeitlich nachfolgende kanonische Entscheidung des Eigentümers. Die allgemeine Aufforderung, den Artikel auf Zenodo abzulegen, wird als Publikationsauftrag bearbeitet; sie ersetzt nicht den durch diese Policy vorgeschriebenen nachfolgenden Entscheid über die präzisierte Fassung.

`ZENODO_METADATA.json` beschreibt genau diesen Beitrag. `MACHINE_PROOF_BUNDLE.json` wird nach tatsächlicher Bereitstellung der Kandidatendateien mit dem Rückgabebeleg vervollständigt. Ein positives Ergebnis seines Validators betrifft die technischen Publikationsvoraussetzungen. Das historisch so benannte Feld `zenodo_upload_authorized` im nativen Beweisschema erzeugt keine menschliche Freigabe; der native Publisher prüft eine gesonderte Eigentümerentscheidung. Der tatsächliche Status bleibt in `PUBLICATION_STATE.json` ausgewiesen.

Ein DOI, ein Zenodo-Eintrag, ein nativer Review, ein Merge oder ein Versand werden erst nach dem jeweils passenden beobachteten Ereignis behauptet. Ein öffentlich lesbarer Repository-Kandidat ist kein bereits publizierter Zenodo-Datensatz.
