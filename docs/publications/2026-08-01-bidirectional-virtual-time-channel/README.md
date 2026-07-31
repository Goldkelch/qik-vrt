# QIK-VRT: Der bidirektionale virtuelle Zeitkanal

Dies ist der bytegebundene Vorveröffentlichungskandidat vom 1. August 2026.

## Hauptartefakte

- QIK-VRT_Bidirektionaler_Virtueller_Zeitkanal_2026-08-01.pdf:
  gesetztes 16-seitiges Working Paper.
- QIK-VRT_Bidirektionaler_Virtueller_Zeitkanal_2026-08-01.tex:
  vollständige LaTeX-Quelle.
- ARTICLE_WHATSAPP_DE.md:
  allgemeinverständliche, vorlesefreundliche Langfassung.
- tools/qikvrt_bidirectional_virtual_channel_witness.c:
  dependency-freier strikter ISO-C90-Zeuge.
- WITNESS_RUN.txt:
  exaktes Referenzlaufprotokoll.
- CLAIM_MATRIX.json:
  vollständige Disposition der 13 Hauptclaims.

## Ergebnis

Der Kandidat trägt eine ausgeführte bidirektionale virtuelle
Informationsübertragung, bedingte Konstruktionssätze für jede einzelne
endliche Nachricht und eine explizite Trennung von Hostzeit, virtueller
Adresse und Wirkungszeit.

Er beansprucht keine physikalische Rückwärtssignalisierung. Die dafür
erforderliche Brückenhypothese und ein falsifizierbares Experiment werden
offen ausgewiesen.

## Reproduzierbarkeit

Der C-Zeuge wird mit folgendem Vertrag gebaut:

    cc -std=c90 -pedantic-errors -Wall -Wextra -Werror -O2 \
      tools/qikvrt_bidirectional_virtual_channel_witness.c

Das PDF wurde mit drei XeLaTeX-Pässen gebaut, vollständig mit Poppler
gerendert und Seite für Seite visuell geprüft.

## Publikationszustand

Repository-Push, Zenodo-Upload und IETF-Datatracker-Mutation sind getrennte
externe Effekte. Dieser Ordner enthält den prüfbaren Kandidaten und die
Vorveröffentlichungsbelege; er behauptet diese externen Effekte nicht.

