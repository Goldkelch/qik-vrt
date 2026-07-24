# Reproduzierbare Offline-Audiotranskription

Die dauerhafte Implementierung liegt unter
[`tools/offline-audio-transcription`](../tools/offline-audio-transcription/README.md).

Sie trennt vier Dinge, die nicht verwechselt werden dürfen:

1. das unveränderte Originalaudio;
2. den automatisch erkannten Wortlaut;
3. eine menschlich geprüfte Transkriptfassung;
4. die inhaltliche Interpretation oder ein daraus abgeleiteter Arbeitsauftrag.

Die Transkription selbst ist netzwerkfrei. Für eine Neuinstallation werden nur
die paketverwaltete Laufzeit und das öffentlich referenzierte Sprachmodell
bezogen; Modellherkunft, Versionen und SHA-256-Werte sind maschinenlesbar
festgeschrieben. Persönliche Audiodateien und Transkripte werden nicht
automatisch veröffentlicht.

## Authentifizierte GitHub-Aufträge

Der Workflow `.github/workflows/qikvrt_audio_request.yml` schließt die Lücke
zwischen einer lokalen Audiodatei und der repository-eigenen Offline-Engine.
Ein berechtigter Aufrufer legt die Binärdaten über die Git-Data-API als
**unreferenziertes Git-Blob** ab und übergibt ausschließlich ein kleines,
validiertes Request-Manifest unter `requests/audio/`. Das Manifest bindet:

- Repository und Git-Blob-SHA;
- Originaldateiname, Bytezahl und SHA-256;
- Sprache und begrenzte Verarbeitungsparameter;
- den anschließenden Repository-Arbeitsauftrag.

Der Workflow akzeptiert nur das gleiche Repository, exakt einen Request,
sichere Dateinamen, zugelassene Medienendungen und höchstens 25 MiB. Er prüft
Blobgröße und SHA-256, installiert das festgeschriebene Modell mit Hashprüfung,
transkribiert in einem temporären Runner-Verzeichnis und veröffentlicht
Transkript, Segmente, Provenienz und Antwortauftrag ausschließlich als
kurzlebiges Workflow-Artefakt. Audio und Transkript werden weder als
Repository-Dateien noch in den Job-Logs persistiert.

Ein unreferenziertes Git-Blob ist **nicht als kryptographisch vertraulich zu
behandeln**: Wer seine Objekt-SHA kennt und Leserechte besitzt, kann es bis zur
serverseitigen Bereinigung abrufen. Vertrauliche Aufnahmen gehören deshalb in
ein privates Repository oder direkt in die lokale Offline-Pipeline. Der
öffentliche Transportzweig darf niemals gemergt werden und wird nach dem Lauf
auf den Ausgangsstand zurückgesetzt.
