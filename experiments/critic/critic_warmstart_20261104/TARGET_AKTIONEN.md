# Konsistente Grenzen für verrauschte Targetaktionen

Änderung vom05.11.2026, vom Nutzer nach der Critic-Aktionsprüfung angefordert.
Sie ist eine deklarierte Änderung der Lernregel für künftige Versuche. Alte
Experimente, Gewichte, Konfigurationen und Berichte bleiben unverändert.

## Neue Regel

Der Critic erhält nach der bisherigen TD3-Aktionsglättung nur noch Aktionen
innerhalb desselben Bereichs wie Actor und Exploration. Maßgeblich ist der
eingefrorene Parent **an der nächsten Actoreingabe und nächsten Phase**, weil
das TD-Target den Folgezustand bewertet.

```text
p = frozen_parent(next_x, next_phase)
width_xyz = min(0.20, 0.5 * abs(p_xyz))
width_gripper = 0.02
noisy = clip(target_actor(next_x, next_phase) + clipped_noise, -1, 1)
target_action = clip(noisy, p - width, p + width), zusätzlich innerhalb [-1,1]
```

Actorgrenzen, Explorationsprojektion und Targetprojektion verwenden dieselbe
Funktion `project_relative`. Dadurch verschwinden XYZ-Korrekturen bei einer
Parentaktion null, XYZ-Richtungen bleiben erhalten, und der Greifer bleibt
innerhalb seiner eigenen Breite0.02. Rauschstandardabweichung, Rauschclip,
Gamma, Lossfunktionen, Learning Rates, Daten und Seeds wurden nicht zusätzlich
verändert.

## Versionierung und historische Läufe

- `target_action_projection="actor_bounds_v1"` aktiviert die neue Regel.
- Fehlender Schalter oder explizit `"legacy"` erhält die bisherige Targetregel.
  Ein Regressionstest prüft deren Targettensor und Generatorzustand bitgenau.
- Eine aktivierte Projektion ohne passenden Actorvertrag `project_action`
  führt vor einem Optimizerupdate zu einem Fehler statt zu einem stillen Fallback.
- Neue relative Learner und vorbereitete explorative Konfigurationen speichern
  den Schalter ausdrücklich; das Konfigurationsschema heißt jetzt
  `relative-exploratory-online-v2`.
- Alte Konfigurationen werden nicht heimlich umgedeutet. Neue Vorbereitungen
  protokollieren den Quellwechsel samt vorherigen Hashes und historischen
  Quellkopien. Vorhandene Starts mit alten Eingangshashes bleiben gegen
  unbeabsichtigtes Wiederverwenden geschützt.
- In der Trainingshistory stehen Projektionsmodus, geänderter Anteil und
  maximale Korrektur der Targetaktionen.

## Prüfung

Dieselben15 erreichten finalen Policyprobes und dieselben15000 Rauschziehungen
wie in der vorherigen Supportprüfung, ohne Optimizerupdates:

| | Bisherige Regel | Mit Projektion |
|---|---:|---:|
| Außerhalb der relativen Actorgrenzen | 12616/15000 | 0/15000 |
| Mindestens eine XYZ-Richtungsumkehr | 1333/15000 | 0/15000 |

Das sind synthetische Ziehungen an eingefrorenen Probes, keine neue Messung der
Aufgabenleistung und keine Rekonstruktion aller alten Trainingsbatches.
Der Vergleich liegt unter `target_projection_001/support_comparison.json`.

43 gezielte Tests bestanden. Darunter: tatsächliche Targetcritic-Eingaben im
Produktionsupdate, korrekte nächste Eingabe/Phase, Extremrauschen, Nullaktionen,
Greifergrenzen, fehlende Actorverträge, gespeicherter Konfigurationsschalter,
eingefrorene Referenz und historische Target-/RNG-Parität.

Zusätzlich prüft `pilot_target_projection_smoke_001` den vollständigen
Produktionspfad mit Supervisor, einer Onlineepisode, vier Criticupdates,
zwei Actorupdates und zwei Evaluationsrollouts. Er ist rein technisch und
kein neuer wissenschaftlicher Hauptlauf. Das Prüfergebnis wird separat unter
`target_projection_001/verification.json` festgehalten.

## Aussagegrenze

Die Korrektur beseitigt die gemessenen Bereichsverletzungen. Sie verbessert
keine bereits gespeicherten Criticgewichte und belegt noch keinen Lernvorteil.
Vor einer Leistungsbehauptung braucht es einen neuen, getrennten Vergleich
mit Aktionsrankingprüfung und identischem Lernbudget.
