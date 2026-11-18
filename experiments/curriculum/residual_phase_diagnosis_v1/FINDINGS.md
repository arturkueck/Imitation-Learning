# Restfehlerdiagnose: Ergebnis und Grenzen · 18.11.2026

Status **COMPLETE**. 112 Episoden in 34 Fallgruppen, Laufzeit 396,8 Sekunden,
**null Optimizerupdates**. Es wurden 17 bekannte erfolglose Modell-/Szenenpaare
und 17 unterschiedliche erfolgreiche Vergleichsfälle untersucht. Die 17
Fehlerpaare stammen aus zehn verschiedenen Anfangsszenen und drei vorhandenen
Parents. Das ist keine unabhängige Trainingsreplikation und kein frisches
Testpanel. Der abgeschlossene Nachtlauf bleibt unverändert.

## Hauptbefunde

| Geprüfter Kontext | Ausgewählte Fehlerfälle | Bewegung allein: Gesamtaufgabe gerettet | Abschluss allein: Gesamtaufgabe gerettet | Beides: Gesamtaufgabe gerettet |
|---|---:|---:|---:|---:|
| Erstes Absenken zum Griff | 3 | 2 | 3 | 3 |
| Erster Transport | 3 | 0 | 0 | 0 |
| Zweites Absenken zum Griff | 2 | 0 | 0 | 0 |
| Zweiter Transport | 3 | 2 | 0 | 2 |
| Erste/zweite Freigabe zusammen | 6 | 0 | nicht anwendbar | nicht anwendbar |

**Erstes Absenken:** Die drei Fehlerfälle betreffen dieselbe Anfangsszene
2026189003 bei allen drei Parents. Die vorhandene Bewegung erreicht dort
die Experten-Abschlussbedingung über viele Frames, aber die gelernte
Abschlusswahrscheinlichkeit bleibt unter 0,8. Der reine Abschluss-Eingriff
rettet alle drei vollständigen Abläufe. Bei zwei Parents genügt auch die
veränderte Bewegung, die wiederum andere Zustände für den unveränderten
Abschlussklassifikator erzeugt. Kein allgemeiner Nachweis auf drei verschiedenen
Fehlerszenen und keine pauschale Trennung sämtlicher Bewegungs-/Abschlusseffekte.

**Zweiter Transport:** Die Aktionsübernahme führt in allen drei ausgewählten
Fehlerfällen zur nächsten Phase und rettet zwei Gesamtaufgaben. Diese beiden
Gesamterfolge betreffen dieselbe Anfangsszene 2026189019 bei Parent 2/3.
Die reine Abschlussübernahme rettet keine Gesamtaufgabe und schädigt einen
zuvor erfolgreichen Vergleichsfall. Ein pauschaler Austausch des Abschlusses
ist daher keine durch diese Diagnose gestützte Lösung.

**Freigabe:** Die reine Aktionsübernahme rettet keinen der sechs gewählten
Fehlerfälle. Die gelernte Abschlussausgabe wird in dieser Phase nicht
verwendet; dafür existiert bewusst kein Completion-only-Arm. Das Ergebnis
schließt Probleme in der vorherigen Ablage oder in der Freigabedynamik nicht aus.

## Lokaler Fortschritt ist nicht vollständiger Erfolg

Beim ersten Transport ermöglicht die Abschlussübernahme in 3/3 ausgewählten
Fehlerfällen eine folgende Phase, beim zweiten Absenken in 2/2. Dennoch
scheitern diese Gesamtaufgaben später. Die Abhilfe eines lokalen Stillstands
ist somit nicht gleichbedeutend mit einer erfolgreich gelösten Stapelaufgabe.

Die Diagnose enthält außerdem zwei verlorene erfolgreiche Kontrollfälle:
einmal durch kombinierte Übernahme im ersten Transport und einmal durch
reine Abschlussübernahme im zweiten Transport. Sämtliche Ausgänge bleiben
erhalten; auch ein vorhandener Experte ist in diesen geerbten Eingangszuständen
keine garantierte Verbesserung.

## Auffällige Eingangszustände als nächste Hypothesen

Ein ausgewählter Fall vor der zweiten Freigabe, Parent 3 / Szene 2026189042,
hat bereits beim Phaseneintritt etwa **2,53 cm horizontalen Versatz** und
**9,00 cm Höhenabstand** zwischen Quell- und Zielwürfel, ohne Würfelkontakt.
Die Zielgeometrie verlangt etwa 4 cm Höhenabstand und höchstens 9 mm XY-Versatz.
Der Eintritt in die Freigabe erfolgt hier also ohne bereits hergestellte
Stapelgeometrie. Dies begründet eine gezielte Prüfung der vorherigen Ablage
und ihrer Übergangsregel; diese Ursache wurde noch nicht durch einen
Phase-5-Eingriff isoliert.

Andere Freigabefälle beginnen näher an der Zielgeometrie und scheitern trotzdem.
Ein einziges geometrisches Merkmal erklärt daher nicht sämtliche Ausfälle.
Kontakt-/Geschwindigkeitsverlauf und Stabilität vor dem Öffnen sind getrennt
zu untersuchen. Diese Beobachtungen sind Hypothesen aus bereits geöffneten
Diagnosefällen, keine nachträglich kalibrierte allgemeine Schwierigkeitsskala.

## Technische und wissenschaftliche Gültigkeit

- Acht Unit-/Integritätstests bestanden; der finale technische Smoke umfasst
  20 Episoden mit allen drei Parents und Phasen. Danach unveränderter voller Plan.
- Alle 34 Kontrollverläufe reproduzieren die archivierten Nachtresultate.
- Anfangszustand und komplette Vorgeschichte bis zum jeweiligen Eingriff sind
  zwischen den Armen identisch. Keine Teleportation oder erzwungene Kontakte.
- Modellparameter und gehashte Eingänge unverändert, keine Optimizerupdates.
- Die ursprünglichen Quellen und Checkpoints des Nachtlaufs wurden erneut geprüft.
- Worker und Supervisor endeten regulär mit Exitcode 0; Wachhaltezustand freigegeben.
- Der erste vorbereitete technische Ordner blieb ungestartet erhalten; vor dem
  finalen Smoke wurde ausschließlich eine ungeschlossene Lesedatei korrigiert.

Der Analysebericht ergänzt nach dem Lauf die lokale Phasenfortschrittsmessung
und Eingangszustände aus den gespeicherten Traces. Diese ergänzende Auswertung
ist explorativ; ursprünglicher Endpunkt, Auswahl, Interventionen und
Einzelergebnisse wurden nicht verändert. Analysecode und Eingänge sind im
abgeleiteten Bericht gehasht.

## Folgerung für die nächste Methodenentscheidung

1. Abschlussfehler und Aktionsfehler getrennt behandeln. Eine generell niedrigere
   Abschlussschwelle oder mehr Updates für alle Phasen ist nicht begründet.
2. Die Abschlusslogik auf falsches Verbleiben und verfrühtes Verlassen getrennt
   prüfen. Ein zusätzlicher geometrischer AND-Guard allein würde einen bereits
   unter 0,8 bleibenden Klassifikator nicht zum Weitergehen bringen.
3. Vor der Freigabe insbesondere Ablagebedingungen und Dynamik untersuchen;
   den unveränderten 50-Frame-Erfolg nicht erleichtern.
4. Neue Abschluss-/Aktionsregeln zunächst auf getrennten Pilot-/Kalibrierungs-
   familien und erfolgreichen Kontrollen entwickeln. Erst danach eine konkrete
   Intervention mit frischen Blindtests, bewertbarer Szenenschwierigkeit und
   größerer begründeter Trainingsseedzahl gemäß AGENTS.md prüfen.

Noch keine neue Policy, neue Trainingsfreigabe oder allgemeine Erfolgssteigerung.
Die Expertenübernahmen dienten ausschließlich der Ursachenprüfung.

## Ablage

- Lauf: `praxis/results/curriculum/residual_phase_diagnosis_v1/run_001`.
- `REPORT.md` / `groups.json`: alle Einzelvergleiche.
- `ANALYSIS.md` / `analysis.json`: Gesamtaufgabe, lokaler Fortschritt und Kontext.
- `traces/*.npz`, `trace_schema.json`: vollständige numerische Abläufe und Einheiten.
- `integrity.json`, `provenance.json`, `sources/`: Prüfungen und eingefrorene Eingänge.

Reine Auswertung ohne Simulator oder Training:
`praxis/.venv/Scripts/python.exe experiments/curriculum/residual_phase_diagnosis_v1/analyze.py --output praxis/results/curriculum/residual_phase_diagnosis_v1/run_001`.
