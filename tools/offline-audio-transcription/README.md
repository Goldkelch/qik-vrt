# Offline-Audiotranskription

Dieses Werkzeug transkribiert lokale Audio- und Videodateien mit FFmpeg,
Sherpa-ONNX und einem multilingualen Whisper-base-Modell. Während der
Transkription werden weder Audio noch Text an einen Netzwerkdienst gesendet.

## Grenzen

- Eine automatische Transkription kann Namen, Zahlen, Abkürzungen und
  Verneinungen falsch erkennen. Unsichere Stellen müssen am Original geprüft
  werden.
- Ein Transkript belegt, was ein Modell erkannt hat; es beweist nicht die
  sachliche Richtigkeit des Gesprochenen.
- Originalaudio, temporäres PCM und Ausgabedateien gehören standardmäßig nicht
  in Git. Die `.gitignore`-Regeln schützen die üblichen Formate.
- Der Modelldownload ist ein separater, sichtbarer Installationsschritt. Er
  überträgt keine Audiodaten.

## Voraussetzungen

- Node.js 24 oder neuer
- FFmpeg und FFprobe
- `curl`, `tar` und `sha256sum` für die einmalige Modellinstallation

## Installation

```bash
cd tools/offline-audio-transcription
npm ci
./scripts/install-model.sh
```

Der Installer prüft das 207-MB-Archiv und alle drei extrahierten Dateien gegen
die in `models/whisper-base-int8/MODEL.json` festgeschriebenen SHA-256-Werte.
Binärdateien und Modellgewichte werden nicht in diesem Repository gespeichert.

## Verwendung

```bash
./bin/transcribe-audio \
  --input /pfad/aufnahme.m4a \
  --output-dir /pfad/ausgabe \
  --language de
```

Erzeugt werden:

- `*.transcript.txt`: zusammengeführter Text;
- `*.transcript.json`: Text und Verarbeitungssegmente;
- `*.provenance.json`: Eingabe-, Modell- und Ausgabeprüfsummen sowie Versionen.

Die Eingabedatei wird vor und nach der Verarbeitung gehasht und niemals
überschrieben. Temporäre PCM-Daten werden auch bei Fehlern entfernt.

## Authentifizierter GitHub-Auftrag

Der Workflow `.github/workflows/qikvrt_audio_request.yml` nimmt ein streng
validiertes Request-Manifest unter `requests/audio/` entgegen. Die Audiodaten
werden zuvor über GitHubs Git-Data-API als unreferenziertes Blob angelegt; das
Manifest bindet Repository, Blob-SHA, Originaldateiname, Bytezahl, SHA-256,
Sprache, begrenzte Laufzeitparameter und den anschließenden
Repository-Arbeitsauftrag.

Die Workflow-Grenzen sind fail-closed:

- nur ein Manifest pro Transport-PR;
- nur Branches `audio-request/**` aus demselben Repository;
- höchstens 25 MiB und eine feste Medien-Endungsliste;
- kein Pfad-Traversal, keine versteckten Dateinamen und keine unbekannten
  Manifestfelder;
- Bytezahl- und SHA-256-Prüfung vor der Transkription;
- Modellarchiv und extrahierte Modellkomponenten werden erneut hashgeprüft;
- Audio und Transkript erscheinen weder im Repository noch im Job-Log;
- Transkript, Segmente, Provenienz und Antwortauftrag werden sieben Tage als
  Workflow-Artefakt aufbewahrt.

Ein unreferenziertes Git-Blob ist nicht kryptographisch vertraulich: Wer seine
Objekt-SHA kennt und Leserechte besitzt, kann es bis zur serverseitigen
Bereinigung abrufen. Vertrauliche Aufnahmen gehören deshalb in ein privates
Repository oder direkt in die lokale Offline-Pipeline. Ein Transport-PR wird
nie gemergt und sein Branch nach dem Lauf auf den Ausgangsstand zurückgesetzt.

## Prüfung

```bash
npm test
./bin/transcribe-audio --help
node src/materialize-request.cjs --help
```

Für eine inhaltliche Freigabe ist zusätzlich eine menschliche Gegenprüfung am
Original erforderlich.
