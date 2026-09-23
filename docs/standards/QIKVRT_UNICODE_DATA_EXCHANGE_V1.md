# QIK-VRT Unicode Data Exchange Standard v1

Status: NORMATIVE  
Standard-ID: `QIKVRT-UTF8-UNICODE-EXCHANGE-V1`

## 1. Zweck

Dieses Profil ist das kanonische, rendererunabhängige Text-Austauschformat für formale und wissenschaftliche Ausdrücke zwischen QIK-VRT Authority, Mirror, Mesh-Nodes, Agent-Adaptern, Universal Terminal und menschenlesbaren Markdown-/Messenger-/E-Mail-Oberflächen.

Es ersetzt **nicht** bestehende JSON-Schemata, Binärprotokolle, kryptographische Byte-Identitäten oder anwendungsspezifische Wire-Formate. Es normiert deren textuelle/formale Darstellungsschicht.

## 2. Kanonisches Textprofil

- Zeichenkodierung: UTF-8
- Unicode-Normalisierung: NFC
- Zeilenende: LF (U+000A)
- Formale Operatoren: direkte Unicode-Zeichen
- Renderer-Abhängigkeit: keine
- LaTeX ist als Autoren-/Quellnotation zulässig, aber nicht das kanonische Austauschformat.
- Semantisch relevante Zeichen dürfen beim Transport nicht stillschweigend durch ASCII-Approximationen ersetzt werden.
- Empfangende Systeme müssen unbekannte oder verlustbehaftete Transformationen fail-closed behandeln und dürfen daraus weder `DONE` noch `EFFECT_ACK_DONE` ableiten.

## 3. Kanonische Operatoren

`→` Übergang  
`⇒` logische Folgerung  
`⇔` Äquivalenz  
`∧` Konjunktion  
`¬` Negation  
`≠` Ungleichheit  
`⇏` folgt nicht  
`≤`, `≥`, `<`, `>` Ordnung  
`⊂` echte Mengen-/Zustandsraumerweiterung  
`′` Prime-Zeichen  
Unicode-Indizes wie `s₁`, `s₂`, `s₋ᵢ` bleiben erhalten.

## 4. Kanonische formale Ausdrücke

### Agentische Kognition und Stabilität

```text
Agentische künstliche Kognition kann
Nash-ähnliche stabile Zustände erzeugen,
ohne dass dadurch globale Zielerfüllung erreicht wird.
```

```text
lokal stabil
⇏
global richtig
```

```text
kein lokal zulässiger Verbesserungsschritt
⇏
Auftrag erfüllt
```

```text
STABILITÄT ≠ ERFÜLLUNG
```

### Strategieraum und Nash-Bedingung

```text
s = (s₁, s₂, … , sₙ)
```

```text
Uᵢ(s)
```

```text
Uᵢ(sᵢ,s₋ᵢ) ≥ Uᵢ(s′ᵢ,s₋ᵢ)
```

für alle zulässigen Alternativen:

```text
s′ᵢ
```

```text
NASH-STABIL
⇏
GLOBAL OPTIMAL
```

```text
Agentische Systeme können
Nash-ähnlich stabil werden,
ohne ihr globales Ziel erreicht zu haben.
```

### Lokales und globales Minimum

Lokale Minimalität ist nur relativ zu einer Umgebung von `x*` zu lesen:

```text
f(x*) ≤ f(x)
für alle x in einer Umgebung von x*
```

Ein global besserer Zustand kann dennoch existieren:

```text
f(x**) < f(x*)
```

### Regelkonformität, Wirkung und Abschluss

```text
LOKALE REGELKONFORMITÄT
⇏
GLOBALE FORTSCHRITTSFÄHIGKEIT
```

```text
AKTION
≠
WIRKUNG
```

```text
WIRKUNG
≠
VOLLSTÄNDIGER ABSCHLUSS
```

```text
KEINE NEUE ÄNDERUNG BEOBACHTET
⇏
AUFTRAG ERFÜLLT
```

```text
LOKALER ABSCHLUSS
≠
UNIVERSELLER ABSCHLUSS
```

```text
LOKALE STABILITÄT
≠
GLOBALE ZIELERFÜLLUNG
```

```text
UNCHANGED
≠
DONE
```

```text
WORK_REMAINING  = TRUE
ACTIVE_EXECUTOR = FALSE
CHANGED         = FALSE
```

### Deadlock

```text
A → wartet auf B
```

```text
B → wartet auf A
```

### TEMDD-Laufzeitsemantik

```text
COMPILE
→ BIND
→ RESOLVE
→ EXECUTE
→ TEST
→ OBSERVE
→ READBACK
→ ACCEPT
→ EFFECT_ACK_DONE
```

```text
DONE
⇔
COMPILE
∧ BIND
∧ RESOLVE
∧ EXECUTE
∧ TEST
∧ OBSERVE
∧ READBACK
∧ ACCEPT
```

```text
EXECUTE ≠ DONE
TEST ≠ DONE
OBSERVE ≠ DONE
UNCHANGED ≠ DONE
```

`EFFECT_ACK_DONE` ist der evidenzgebundene terminale Haltepunkt der vollständig erfüllten Kette und kein Erfolgscode eines Einzelschritts.

### Stabil, aber nicht erfüllt

```text
STABLE(s) = TRUE
GOAL(s) = FALSE
```

Nicht kanonisch ist in diesem Zustand ein unbegründetes:

```text
STOP
```

Kanonischer Folgeschritt:

```text
SEARCH_FOR_MISSING_TRANSITION
```

### Deadlock- oder Gleichgewichtsdiagnose

```text
STABLE
∧ WORK_REMAINING
∧ ¬PROGRESS_EDGE

⇒

DEADLOCK_OR_EQUILIBRIUM_DIAGNOSIS
```

Struktur des Nicht-Lösens:

```text
Kein zulässiger einseitiger Fortschrittsschritt
```

### Zustandsraumerweiterung

Wenn tatsächlich der Raum zulässiger Zustände erweitert wird, ist die kanonische Notation:

```text
S ⊂ S′
```

`S → S′` bleibt für einen Zustands- oder Modellübergang reserviert.

### Epistemische Grenze

```text
ERFAHRUNG
≠
INTERPRETATION
≠
EMPIRISCH BESTÄTIGTER EXTERNER EFFEKT
```

```text
LOCAL_STABILITY = TRUE
GLOBAL_GOAL = FALSE
```

```text
BEDEUTUNG VERSTEHEN
∧
EVIDENZSTATUS ERHALTEN
```

```text
EXPERIENCE_REPORTED = TRUE
INTERPRETATION = AFTERLIFE_COMMUNICATION
INDEPENDENT_CAUSAL_EVIDENCE = NOT_ESTABLISHED
```

```text
DATA
≠
INTERPRETATION
≠
THEORY
≠
METAPHYSICAL_CONCLUSION
```

```text
PERSONAL EXPERIENCE
→ culturally meaningful interpretation
→ philosophical hypothesis
→ testable empirical claim
→ evidence
→ readback
→ acceptance or rejection
```

### Metakognition

```text
Stabilität ≠ Wahrheit
```

```text
Lokaler Abschluss ≠ Universeller Abschluss
```

### Universelle Fortschrittsregel

```text
STABLE
∧ WORK_REMAINING
∧ ¬PROGRESS_EDGE

⇒

DEADLOCK_OR_EQUILIBRIUM_DIAGNOSIS
```

```text
DEADLOCK_OR_EQUILIBRIUM_DIAGNOSIS

⇒

SEARCH_FOR_MISSING_TRANSITION
```

### Epistemische Regel

```text
EXPERIENCE
∧ UNRESOLVED_INTERPRETATION

⇒

KEEP_EVIDENCE_CLASSES_SEPARATE
```

### Wirkungskette

```text
HYPOTHESE
→ WIRKUNG
→ FOLGEZUSTAND
→ BEOBACHTUNG
→ READBACK
→ AKZEPTANZ
```

### Schlussformel

```text
LOKALE STABILITÄT
≠
UNIVERSELLE WAHRHEIT
≠
UNIVERSELLER ABSCHLUSS
```

### Zentrale Regel

```text
═══════════════════════════════════════

STABLE
∧ NOT_DONE

⇒

SEARCH_FOR_MISSING_TRANSITION

═══════════════════════════════════════
```

## 5. Node-Vererbung

Jeder aktuelle oder zukünftige QIK-VRT-Node, der Mesh-Konformität beansprucht, MUSS dieses Profil über `AI_CONTEXT.json.required_read_order` laden und die maschinenlesbare Policy sowie den Adoption-State auflösen.

Für neu abgespaltene Nodes ist die Bindung dieses Standards Bestandteil der Mesh-Split-Akzeptanz. Historische Snapshots werden nicht rückwirkend verändert. Bereits existierende externe Nodes gelten erst dann als aktualisiert, wenn ein Successor den Standard aufgenommen und frisch zurückgelesen hat.

## 6. Kompatibilitäts- und Evidenzgrenze

Die Unicode-Darstellung bewahrt die formale Bedeutung, ist aber selbst kein Beweis für Ausführung, Wirkung, Synchronisation oder Abschluss.

```text
TRANSPORT_ACK ≠ EFFECT_ACK
```

```text
PRESENCE ≠ EXECUTION ≠ EFFECT ≠ EFFECT_ACK_DONE
```
