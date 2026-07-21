# Wissenschaftsbündel Version 3.0

**Titel:** Mandelbrot-Menge, Anschlussordnung, Physik und Retrokausalität  
**Autor:** Ingolf Lohmann  
**Stand:** 21. Juli 2026  
**Umfang:** 62 Seiten, A4

## Öffentlicher Zugriff

- [PDF im kanonischen Goldkelch-Repository](https://github.com/Goldkelch/qik-vrt/blob/main/docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf)
- [Direkter PDF-Download aus dem Goldkelch-Repository](https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf)
- [Verifizierter Spiegel bei Ingolf Lohmann](https://github.com/ingolf-lohmann/qik-vrt/blob/main/docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf)
- [Direkter PDF-Download aus dem Spiegel](https://raw.githubusercontent.com/ingolf-lohmann/qik-vrt/main/docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf)

## Inhalt

Das Dokument trennt fünf Ebenen:

1. die mengentheoretische Komplementaussage zur Mandelbrot-Menge;
2. die rekursive Anschlussordnung und ihre Fixpunktdarstellung;
3. die dimensionsrichtige Brücke zu physikalischen Größen und Einheiten;
4. Retrokausalität, Retrodiktion, Zeitumkehr, globale Randbedingungen,
   No-Signalling und mögliche experimentelle Konsequenzen;
5. Geltungsgrenzen, Falsifikationsbedingungen und das weitere
   Forschungsprogramm.

Die mathematischen Aussagen gelten innerhalb ihrer angegebenen Definitionen.
Physikalische Korrespondenzen werden als Modelle beziehungsweise prüfbare
Forschungshypothesen ausgewiesen. Insbesondere klärt der Retrokausalitäts-Teil
die verschiedenen Bedeutungen des Begriffs, ohne eine noch ausstehende
empirische Bestätigung als bereits erfolgt auszugeben.

## Dateien

| Datei | Bedeutung |
|---|---|
| Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf | gesetzte und visuell geprüfte Publikationsfassung |
| Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex | vollständiger LaTeX-Quelltext |
| Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.bib | BibTeX-Literaturdatenbank |
| SHA256SUMS | bytegenaue Integritätswerte |

## Integrität prüfen

Im Verzeichnis dieses Bündels:

    sha256sum -c SHA256SUMS

Der SHA-256-Wert der veröffentlichten PDF lautet:

    b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f

## Reproduzierbarer Satzlauf

Mit einer geeigneten TeX-Live-Installation:

    pdflatex -jobname=Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21 -interaction=nonstopmode -halt-on-error Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex
    bibtex Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21
    pdflatex -jobname=Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21 -interaction=nonstopmode -halt-on-error Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex
    pdflatex -jobname=Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21 -interaction=nonstopmode -halt-on-error Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex

## Lizenz- und Geltungsgrenze

Für Dokumentation und andere Nicht-Quellmaterialien gelten die im
Repository ausgewiesenen Lizenz- und Übergangsregeln, insbesondere
LICENSE, LICENSE_NOTICE.md und LICENSE_TRANSITION.md. Diese
Veröffentlichung verändert keine historischen oder fremden Lizenzrechte.

