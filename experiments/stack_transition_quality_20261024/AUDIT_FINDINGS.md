# Unabhängiges Konzept- und Codeaudit

Stand: 24.10.2026. Read-only-Prüfung des Plans und der historischen Implementierungen; ausschließlich dieses Auditdokument neu geschrieben. Kein Training, keine neuen reservierten Tests. Ziel: ausführbarer B0/B-Pilot mit unverändertem Actor und Controller; C bleibt ein separater nächster Faktor.

## Geprüfte Evidenz

- `README.md` dieses Ordners, insbesondere Zeilen49–94 und102–133.
- `../stack_five_curriculum_20261023/runner.py`, insbesondere34–64,81–125,127–135 und180–224.
- `../stack_self_imitation_20261023/pipeline.py`, insbesondere15–67,106–121 und123–165.
- `../stack_phased_8h_20261023/method.py:23–24,54–74` und `../stack_composition_20261023/run.py:58–71`.
- Tatsächlich geöffnet: Sammlungsdatei `curriculum_n4_cycle0/220001.npz` und zugehöriges Manifest. Kein Endtesttrace zur Datenerzeugung verwendet.

Die geöffnete Rohdatei enthält1500Frames: x[1500,10], a[1500,7], pre_obs/post_obs[1500,21], pre_state[1500,71], prefix_valid[1500,3], velocities[1500,24], contacts[1500,3], fingers[1500,4]. Es gibt keine separaten Cubequaternionen, grasp-Bools oder post_state. Positionen stammen aus obs; post_state kann für t<T-1 aus pre_state[t+1] gewonnen werden, der letzte Zustand ist so nicht vorhanden.

## P0: vor jedem Pilotlauf schließen

### P0.1 Quellenallowlist und Familientrennung statt glob über Experimente

**Risiko:** Altordner enthalten Training, Validierung, Entwicklungs- und reservierte Testdaten. Gleiche Seeds mit mehreren Teachern oder Verzweigungen müssen dieselbe Startfamilie behalten. Initialzustandshashes allein trennen nicht semantisch gleiche Starts bei verschiedenen Simulationshöhen. Datasetmanifest aus erfolgreicher Sammlung ist zulässig; final_test, gates, preflight399001 und alte Tests sind es nicht.

**Behebung:** Explizite Liste erlaubter Sammlungmanifeste mit Hashes; Split aus Herkunft unverändert übernehmen; episode_id aus Quellenmanifest+Seed; family_id aus experimentellem Startnamespace+Höhe+Seed oder explizit geerbter Verzweigungsfamilie. Keine Zuweisung anhand Erfolg, Qualität oder Teacher. Deduplikation zusätzlich per Initialhash.

**Abnahme:** Weder Pfad noch Namespace aus denylist kann akzeptiert werden; synthetische gleichfamiliäre Train/Valid-Dateien werden zurückgewiesen. Quellhashes und ausgesperrte Tests im Auditbericht. Heldout-Ergebnisse beeinflussen keine Scoreparameter oder Modellwahl.

### P0.2 Ereignisse haben Post-action-Semantik; keine um einen Frame verschobene Extraktion

`runner.py:50–60`: x/pre_obs/pre_state sind vor Aktion; prefix_valid/velocities/contacts/fingers und controller_event nach Aktion. event1 resettiert Policy erst für die nächste Aktion; event2 setzt stage erst für das nächste Frame. Reales Beispiel220001: event1 bei139(stage1,phase6,retreatFalse); event2 bei140(stage1,phase0,retreatTrue). Der neue stage2 beginnt erst141. `pipeline.py:34–43` hat dieselbe zeitliche Richtung.

**Behebung:** Fensterbeginn nach tatsächlichem stable-release-Ereignis definieren und nachfolgende Aktionsframes korrekt aufnehmen. Quelle beim Übergang nach stage s ist Würfelindex s+1; geschützter Turm sind Indizes0..s. Nicht unverändert stage als Quellindex für Retreat verwenden: Retreat referenziert noch den zuletzt platzierten Würfel.

**Abnahme:** Kleiner synthetischer Eventtrace mit expliziten Indizes; event1,event2 und erster neue-source-Frame stimmen. Prefix-validity für unteren Turm hat Index prefix_count-2. Letzte Episodeframes ohne genügend Nachlauf werden abgelehnt, nicht als vollständig behandelt.

### P0.3 Zehn Freigabeframes nicht aus dem Controllerzähler behaupten

`runner.py:37–42` zählt gültige Präfixframes bereits vor Phase6. Event1 allein beweist daher nicht zehn Freigabeframes in Phase6. Strenge Präfixgültigkeit enthält Fingerfreiheit, aber der Freigabe-/Releasebezug muss zusätzlich eindeutig sein.

**Behebung:** Historische Rohsignale rückwärts auf zehn unmittelbar aufeinanderfolgende gültige Post-action-Zustände prüfen; Releasephase/Quellenfreigabe explizit dokumentieren. Den historischen Controller im B0/B-Vergleich unverändert lassen.

**Abnahme:** Unterbrochene oder zu kurze Gültigkeitsserie wird abgelehnt. Der referenzierte Zustand liegt am Fensterbeginn, nicht nach dem zukünftigen Pickup.

### P0.4 Physisch erfolgreiche nächste Aufnahme definieren

Im Rohschema fehlt ein grasp-Bool. `p>=3` oder Teachercompletion beweist weder Griff noch Anheben. Neue Quelle kann bereits später abgesetzt worden sein, wenn man blind50Frames an das Ende des Fensters hängt.

**Behebung:** Pickup braucht Quellkontakt/Greifernachweis plus messbare Anhebung relativ zur Quellhöhe vor Beginn; Mindestdauer, Höhe und maximaler Zeithorizont vorab festschreiben. Bestehende Daten können nötigenfalls aus pre_state und passendem model.xml gezielt rekonstruiert werden. Ohne sicheren Griffnachweis nur explizit benannte Kontakt-plus-Lift-Proxy nutzen, keinen echten grasp behaupten. Nachlauf bezieht sich auf das geschützte untere Präfix; Aktionstrainingsfenster endet am bestätigten Pickup, nicht automatisch erst nach50 weiteren Transportframes.

**Abnahme:** Quelle nur berührt, ohne Kontakt hochfliegend, oder Phase3 ohne Lift sind Negativfälle. Nachlauf50 am Episodenende unvollständig → zensiert/abgelehnt. Erfolgreicher lokaler Übergang bleibt akzeptiert, wenn die Episode erst deutlich später scheitert. Nachlauf darf nicht unbemerkt den begonnenen nächsten Stack als zusätzliches Trainingsziel hineinziehen.

### P0.5 Eigener Übergangssampler nötig

`pipeline.py:106–120` erwartet alle sieben Phasen. Rückzug/Anflug/Pickup enthalten hauptsächlich0..3, gegebenenfalls6, nicht zwingend4/5. Wiederverwendung führt zu Assertion oder künstlich eingefügten Fremdframes.

**Behebung:** Vorhandene Phasen → geeigneter Abschnitt → Frame; Section-/Family-Längen dürfen nicht implizit Gewicht erzeugen. B0 undB bekommen exakt dieselben Sampleindizes in gleicher Reihenfolge, nur die Gewichte unterscheiden sich. Original32+Replay16+Transition16 bleibt gleich.

**Abnahme:** Datensatz nur mit Phase0 und3 ist samplbar; jede gezogene Phase ist tatsächlich vorhanden; zwei Läufe gleicher Seeds produzieren identische Frameids. Unterschiedliche Abschnittslängen erzeugen keine proportionalen Abschnittshäufigkeiten.

### P0.6 Gewichtung darf Replayanteile nicht verändern oder doppelt wirken

README:88–94 verlangt Gewichte nur im neuen Viertel. Ein global gewichteter64erLoss oder zusätzlicher Qualitätssampler ändert gleichzeitig Mischanteile. Batchnormalisierung kann bei fast konstanten Qualitätswerten die Intervention praktisch wirkungslos machen.

**Behebung:** `L=.5*mean(original_mse)+.25*mean(replay_mse)+.25*sum(w*transition_mse)/sum(w)+.1*original_bce`. MSE vor Gewichtung pro Frame über4 aktive Aktionskomponenten mitteln. Ein Gewicht pro Abschnitt; kein Q-Sampling. Gewichtungsdispersion, ESS und Beitrag pro Teacher/Familie melden.

**Abnahme:** Alle Gewichte1 → numerisch identischer B0-Loss/Gradient; Multiplikation aller neuen Gewichte mit Konstante ändert Loss nicht; Veränderung der Übergangslänge ändert nicht implizit Abschnittsgewicht. Großer Originalfehler wird durch neue Gewichte nicht anders skaliert.

### P0.7 Freiraum ist in den Rohdaten nicht gemessen

README:74–80 ist korrekt vorsichtig. EEF-Turm-Distanz ist kein Abstand der Fingergeometrie. Kontakte geben keine Millimeterabstände. Fehlende Cubequaternions machen reine obs-Geometrie zusätzlich unsicher.

**Behebung:** B0/B-Pilot nutzt ausdrücklich eine Scoreversion ohne Clearance und renormalisiert dokumentierte übrige Koeffizienten. Kein geänderter Sicherheitscontroller. Erst später geeignete MuJoCo-Geometriedistanzen aus restauriertem Zustand oder neuem Collector validieren.

**Abnahme:** Scoremanifest nennt ausgeschlossene Komponente und tatsächliche Gewichte mit Summe1. Keine Zahl wird als Clearance bezeichnet, die bloß EEF-Abstand ist. Zukunftsgrößen aus quality_metadata können nicht als Actorinput geladen werden.

## P1: Aussagekraft und Interpretation

### P1.1 Selbstkopiegradient / Datenangebot vorab messen

`method.py:54–62` ist deterministischer Actor; exakt eigene Labels ergeben anfangs praktisch null MSE. Erhebliche Gewichtsvarianz alleine erzeugt kein Lernsignal. n4-Sammlung hat nur einen Teacher(`runner.py:193` mit confirmed ready-Liste); mehrere Studentseeds sind deshalb keine mehreren Datengeneratoren.

**Maßnahme:** Vor Training je Student und Teacher sowie pro Phase ungewichtete/gewichtete Action-MSE, Aktionsunterschiede und Gradientnorm des neuen Anteils messen. Trainingsdaten nicht aufgrund eines nachträglich gesehenen Testgewinns auswählen. Minimalzahlen verschiedener akzeptierter Familien und Validierungsübergänge vorab festlegen. Wenn Score fast konstant oder Actiongradient praktisch null, Pilot als wenig informativ melden und begrenzt stoppen statt längere Runs als Lösung empfehlen. Numerische Gates anhand Implementationsrauschen/Trainingsdaten begründen, nicht behaupten, eine universelle Schwelle zu kennen.

**Abnahme:** Datasetreport enthält diese Zahlen vor Optimierung; keine Erfolgsprognose aus Datenmenge allein.

### P1.2 Completionkopf kann trotz Original-only BCE durch Actortraining driften

`PhaseNet` hat je Phase gemeinsame zwei Hiddenlayer und5erOutput. Actorgradient verändert Hiddenfeatures, auf denen der Completionlogit beruht. Original-BCE bedeutet nicht unveränderte Completion auf höheren Zuständen.

**Maßnahme:** Unveränderte Architektur/BCE in beiden Armen lassen, aber Completionprobabilitäten, Phasezeiten und frühe/späte Umschaltungen separat messen. Keine Pseudo-y aus erfolgreichen eigenen Episoden still als Expertcompletion übernehmen. Ein eingefrorener Completionteacher wäre eine weitere explizite Ablation.

**Abnahme:** Modellidentität vor Update, originale Validierung und simulierte Phase-/Retreatdauer je Checkpoint; Bericht nennt mögliche indirekte Completionänderung.

### P1.3 Kontrollierter Vergleich und unabhängige Startfamilien

README:114 benennt korrekt B0/B als kleinsten sauberen Versuch. A/B ändern gleichzeitig Daten und Gewichtung. Existierender runner train:120–124 evaluiert nur das letzte Update; das soll nicht übernommen werden.

**Maßnahme:** Drei gepaarte Parents, B0/B mit identischem Datensatz/Sampler/Optimizer/Budget; Update0 und mehrere feste Zwischencheckpoints. Auswahl auf frischen Entwicklungsstarts mit unverändertem Tie-break; Parent ist auswählbarer Nullupdatekandidat. Ein gemeinsames vorbereitetes Übergangspanel aus erlaubten Sammlungszuständen muss Familien-disjunkt von Training sein. Simulation frisch aus pre_state starten erfordert Controllerzustand(anchor,steps,phase,stage,retreat) und korrekte Simulator-/Controllerrestauration; bloß cube positions zu teleportieren erzeugt anderen Benchmark.

**Abnahme:** Gleiches Modell+Start rekonstruieren zunächst denselben nächsten Zustand/Action im technisch reservierten Replay. Benchmarkfailures beim Erzeugen vorbereiteter Starts als Coverage melden, nicht verschwinden lassen. Gesonderte vollständige3er/4erRollouts auf neuen Starts; keine90%-Behauptung aus Übergangserfolg. Testpanel wird genau einmal nach Freeze genutzt.

### P1.4 Gates für Durchgängigkeit nicht tautologisch machen

Hart alle Frames streng gültig zu verlangen macht die Erhaltkomponente bei allen akzeptierten Fenstern1; Variation muss dann von Ruhe/Zentrierung/Kontakt kommen. Umgekehrt erlaubte Ausfälle brauchen vorab feste Dauer/Geometriegrenzen, sonst subjektive nachträgliche Erfolgserweiterung.

**Maßnahme:** Für kleinen Pilot bevorzugt strenge eindeutige Akzeptanz, konstanten Erhaltterm offen melden; alternativ klar getrennte strukturelle und dynamische Gültigkeit. Verteilung sämtlicher Scorekomponenten ausweisen. Herkunft des Referenzzustands unveränderlich speichern. Falls keine sinnvolle Gewichtungsdispersion, H1 ist mit diesem Datensatz nicht prüfbar.

**Abnahme:** Jede Ablehnung hat maschinenlesbaren Grund; stabiles Ende nach zwischenzeitlichem Einsturz wird nicht akzeptiert. Native vollständige Erfolgsmetrik bleibt unverändert.

## P2: nächster Faktor C, nicht vorgetäuscht im Pilot

Historische pre_obs hat nur Positionen+EEFpose+gripper. velocities/contacts/fingers sind POST-action. Für neues Inputmodell dürfen sie nicht an denselben t-Input gehängt werden; t-1 ist kausal, aber erste Frames und Reset müssen korrekt sein und es bleibt kein unmittelbarer aktueller Kontakt. Bestehende Simzustände erlauben rekonstruierte aktuelle Features, erst nach Replay-Audit.

Neue Turmfeatures benötigen Prefix-/Quellmaske, richtige Quellzuordnung während Retreat und relative Geometrie; Policy muss sie online tatsächlich erhalten. Residualpfad mit Nullinitialisierung muss Outputgleichheit vor Update nachweisen. Originalexpertframes müssen sinnvolle kompatible Turmfeatures erhalten oder der neue Pfad für sie ausdrücklich maskiert bleiben. C vorerst zurückstellen, bis Features/Onlinepfad/Masken und identische Initialaktionen getestet sind. Ebenso neue Rückzugsphasen und Geometriecontroller separat halten.

## Empfohlenes Freigabepaket

1. Extraktor + Scoreversion ohne Clearance + Schema + Manifestallowlist.
2. Echte Dateninventur einschließlich abgelehnter/unvollständiger Fenster und Train/Valid-Familien.
3. Identischer B0/B-Sampler und korrekt normalisierter Loss mit zielgerichteten Positiv-/Negativtests.
4. Preflight mit Originalhash, Quellen-/Teacherhash, korrumpierter Aktion, Off-by-one-Fällen, Splitkonflikt und Ausgangsgradienten; nur kurze technische Optimizersteps.
5. Laufprotokoll mit neuem Seedregistry,30k-Cap oder bewusst kleinerem Pilotbudget, Entwicklungszeitpunkten, Auswahlregel, Zeit-/Diskcaps, Abbruch/Resumeverhalten und Endtestfreeze. Kein automatischer langer Trainingsstart allein aufgrund dieses Audits.

Das Konzept ist als kleiner B0/B-Test grundsätzlich brauchbar. Ein nachweislich kausaler Übergangsdatensatz, ausreichende Vielfalt und ein funktionierender unabhängiger Benchmark sind Voraussetzungen; gute Qualitätsscores sind kein Ersatz für diese Prüfungen.

## Addendum: bestätigter P0-Kontaktmessfehler im historischen Collector

Unabhängig an der tatsächlichen N3-Umgebung geprüft: `env.robots[0].gripper` ist ein Dictionary mit Schlüssel `right`. Das zugehörige GripperModel enthält die Kontaktgeometrien `gripper0_right_hand_collision`, `gripper0_right_finger1_collision`, `gripper0_right_finger1_pad_collision`, `gripper0_right_finger2_collision`, `gripper0_right_finger2_pad_collision`.

`env._check_grasp` unterstützt Dictionaries ausdrücklich und ruft sich rekursiv für die einzelnen GripperModels auf. `env.check_contact` beziehungsweise `robosuite.utils.sim_utils.check_contact` unterstützt dagegen nur Geomnamen, Geomlisten und MujocoModel. Bei einem Dictionary werden die Kontaktgeomnamen per `geomname in geoms_1` unter den Dictionaryschlüsseln gesucht. Da dort nur `right` steht, entstehen falsche Negative.

Betroffene historische Stellen:

- `stack_five_curriculum_20261023/runner.py:58`: `fingers`-Logs.
- `stack_self_imitation_20261023/pipeline.py:33`: ältere `fingers`-Logs.
- `stack_composition_20261023/run.py:67`: zusätzliche Fingerkontaktfreiheit der nativen Präfixgültigkeit. Der vorhergehende `_check_grasp` bleibt wirksam, aber einzelne Finger-/Handkontakte ohne vollständigen Griff wurden durch diese zusätzliche Zeile nicht korrekt ausgeschlossen.

**Konkreter gespeicherter Witness:** `stack_five_curriculum_20261023/datasets/curriculum_n3_cycle0/215000.npz`, `pre_state[193]`, neue Quelle cubeC im Lift. Nach Restaurieren und `sim.forward()` ergibt sich am identischen restaurierten Zustand:

- `env.check_contact(env.robots[0].gripper, cubeC) == False`;
- `any(env.check_contact(g, cubeC) for g in env.robots[0].gripper.values()) == True`;
- `env._check_grasp(env.robots[0].gripper, cubeC) == True`.
- Historisches `fingers[193] == [False, False, False]`.

Die erneute Forwardberechnung verschiebt die aus body_xpos gelesenen Positionen gegenüber dem historischen pre_obs um maximal0,465mm; dies ist eine zusätzliche Replay-/Integrationsfrage. Der Vergleich der beiden Kontaktaufrufe am selben restaurierten Zustand beweist den Dictionaryfehler unabhängig davon eindeutig. Der historische fingers-Eintrag gehört außerdem zur Post-action-Seite, der Witness ist ein Pre-state: daraus wird keine exakte framegleiche ursprüngliche Kontaktanzahl behauptet.

**Konsequenz für diesen Pilot:** Historische `fingers` dürfen keinen Qualitätswert Kontaktfreiheit bestätigen. Historisches `prefix_valid` enthält weiterhin Geometrie-, Nachbarkontakt-, Geschwindigkeits- und native Graspprüfungen, aber nicht die behauptete vollständige zusätzliche Fingerkontaktfreiheit. Eine unverifizierte Übernahme darf daher nicht als durchgehend strenger Turmerhalt gelten. Historische Rohdateien, Zahlen und Reports unverändert bewahren; neue Resultate müssen den Messfehler und ihre korrigierte Definition explizit benennen.

**Behebung und Abnahme:** Ein zentraler neuer Helper vereinheitlicht Dictionaryeinträge zu GripperModels/Contactgeoms, fail-closed bei unbekannten Typen. Positivtest mit echtem Kontakt und negativem Dictionaryaltaufruf; Negativtest mit eindeutig kontaktfreiem Zustand; Tests mit einzelnen Finger-/Handkontakten ohne vollständigen Griff. Neuer Collector und Onlinebenchmark verwenden den Helper. Für alte Daten entweder Kontaktinformationen nach kontrolliertem Replay rekonstruieren und versioniert separat speichern oder betroffene Qualitätskomponente/harte Gültigkeit als unverifiziert markieren und Training weiter blockieren. Geometrie-/Integrationsabweichungen beim Replay messen und nicht durch großzügige Toleranz still überdecken.
