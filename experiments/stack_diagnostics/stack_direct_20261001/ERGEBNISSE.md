# Diffusion versus direkter Action-Chunk-Regressor

**Einordnung: C für den abrupten Expert-Übergang; das Direktmodell ist bei der Gesamtaufgabe klar besser.** Die fehlende scharfe Lift→Transport-Umschaltung ist nicht spezifisch für Diffusion: Beide Modelle reagieren unmittelbar an der Expert-Grenze schwach und zeigen eine geglättete Übergangszone. Der direkte Predictor reagiert im Median stärker (1,65 % statt 0,62 % des Expert-Sprungs), startet aber auf allen 20 Expert-Validierungsverläufen zu früh, statt den Sprung nachzubilden. Gleichzeitig erreicht er 28/40 stabile Stacks gegenüber 0/40 bei Diffusion, mit 17/20 auf den bisherigen und 11/20 auf den zusätzlichen Starts. Im stabilen Expert-Transport trifft er die Richtung wesentlich zuverlässiger (mittlerer Cosinus 0,998 statt 0,506; falsche Richtung 0 % statt 19,6 %) und erzeugt stärkere XY-Aktionen (mediane Expert-Stärke 76,0 % statt 28,7 %). Die geringe Umschaltsensitivität lässt sich daher nicht allein durch das stochastische Diffusionsziel erklären. Für diese Aufgabe ist ein stochastisches Diffusionsmodell unter den getesteten Bedingungen nicht erforderlich. Der große Closed-Loop-Vorteil belegt die Brauchbarkeit der direkten Baseline, aber nicht, dass sie den abrupten Expert-Wechsel gelernt hat oder dass ausschließlich Diffusion die Ursache ist.

## Fragestellung und Kontrolle

Kann ein einfacher deterministischer Chunk-Predictor aus denselben zwei Rohframes den abrupten Lift→Transport-Wechsel besser abbilden? Kein Phasenclassifier, keine State Machine, kein separater Controller, keine Hierarchie, keine Dynamikfeatures, keine zusätzliche History, keine Phasenbalancierung und keine XY-Heuristik.

Die Diffusionsreferenz ist der ursprüngliche Scheduler-korrigierte Epoch-300-Checkpoint mit **30.000 Gradient Updates ab zufälliger Initialisierung**. Das Direktmodell trainiert ebenfalls von zufälliger Initialisierung für genau 30.000 Updates. Die 5.000-Update-Fortsetzungen der letzten Runde sind hierfür keine passenden Vergleichsbudgets und werden nicht verwendet. Vorhandene Diffusionsgewichte werden nicht neu trainiert.

Datensatz unverändert: 200 Demos, 180 Training / 20 Validierung, vorbestehende Splits. Beide trainieren nur auf den 180 Trainingsdemos, uniform mit Zurücklegen, Batch 8, insgesamt 240.000 Sample-Ziehungen. Seed 1 soweit zwischen Architekturen sinnvoll. Die exakte historische Diffusions-Ziehfolge wurde nicht gespeichert und lässt sich nicht als bitgleich nachweisen; Samplingverteilung und maximale Trainingsmenge stimmen überein. Die 62 Demos mit schwarzen Bildern bleiben unverändert, State-Inputs enthalten keine Bilder. Datensatz-SHA256 `5222cbf96dc6218389d491fe7b99449295dcfc9bceb3bab8f8776ffff19fe6f8`.

## Direktmodell

| Eigenschaft | Wert |
|---|---|
| Observation | object(6), EEF-Position(3), EEF-Quaternion(4), Fingerpositionen(2) |
| Dimension | 15 pro Frame; 2 Frames; flach 30 |
| Encoder | gleiche Rohfeature-Konkatenation; keine zusätzliche Observation-Normalisierung |
| Netzwerk | Input 30→2048; 8 Residualblöcke, je LayerNorm→Linear→SiLU→Linear, Residuum / √2; Output 2048→112, tanh |
| Parameter Direkt / Diffusion | 67,467,376 / 65,648,903 (+2.77 %) |
| Output | 112 = 16 × 7; vollständiger Action Chunk |
| Replanning | zwei ausgeführte Aktionen, Chunkindex 1 und 2 |
| Loss | ungewichteter MSE über Batch × 16 Zeitpositionen × 7 Komponenten |
| Action-Normalisierung | Identität, exakt wie Diffusion; Expert-Aktionen in [−1,1]; tanh begrenzt direkte Ausgabe |
| Optimizer | AdamW, LR 1e−4, Betas 0,9/0,999, eps 1e−8, Weight Decay 1e−6 |
| LR | 500 Warmup-Updates, danach Cosinus bis Update 30.000 |
| EMA | Power 0,75, gleiche Methode wie Diffusion; finale EMA für Evaluation |
| Auswahl | ausschließlich finaler Checkpoint, kein Tuning anhand der Rollouts |

Das Aktionsfenster eines Ankerframes i beginnt wie im tatsächlichen Robomimic-Loader bei i−1. Beide geben die Aktionen an Index 1/2 aus, also i/i+1. Randpadding ist identisch und gegen 40 reale SequenceDataset-Fenster überprüft. Observationen werden FP32 übergeben, keine Mischpräzision. Unterschiedliche Modelle und Losses verhindern gemeinsame Initialgewichte und einen numerisch identischen Optimierungspfad; identischer Seed ist keine Gleichheit dieser Pfade.

Direkter Expert-Chunk-MSE nach Training: Training 0.011013, Validierung 0.014607. Der MSE auf Actions ist nicht numerisch mit dem Diffusions-Epsilon-MSE vergleichbar. [Vollständige Direkt-Konfiguration](config.json), [ursprüngliche Diffusions-Konfiguration](diffusion_config.json), [Direkt-Checkpoint](model_final.pth). Diffusionscheckpoint: `C:\Users\artur\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_diagnostics\stack_followup_20261001\state_scheduler_fixed\runs\stack_two_state_scheduler_fixed\20261001133241\models\model_epoch_300.pth`, SHA256 `a2c2cca1cd087409261402f3b95f7b6592961e6aac92c276c72657dd436343f4`.

## Offline: identische Expert-Grenzbeobachtungen

Unverändertes gespeichertes Panel: 20 Validierungsdemos × 21 Frames, −0,5…+0,5 s um Expert-Transportbeginn. Diffusion DDIM10, zwei ausgeführte Aktionen, acht gespeicherte Draws je Panel-Frame und 32 Draws je unmittelbarem Grenzframe. Direktmodell deterministisch, je Zustand genau eine Ausgabe. Für die Grenzreaktion wird bei Diffusion das **identische Rauschen vor/nach** verwendet; so wird der Observation-Effekt von Zufallsstreuung getrennt. Direkt: 20 Paare, Diffusion: 20 × 32 Draw-Paare. Draws sind keine unabhängigen Demos.

Grenzreaktion = `||a_post − a_pre|| / ||Expert_post − Expert_pre||`, erste ausgeführte XYZ-Aktion. Zusätzlich Projektion der Reaktion auf den Expert-Sprung, damit falsche Änderungsrichtungen nicht als Verbesserung zählen. [Paarvergleiche](paired_boundary_comparisons.json), [Bootstrap über Demos](paired_demo_bootstrap.json), [Offline-Predictions](offline_predictions.npz). Für das Direktmodell wurden außerdem alle Frames der 200 Demos vorhergesagt und gespeichert, ohne Validierungsdaten für Updates zu verwenden.

| Offline-Metrik | Diffusion | Direkt |
|---|---:|---:|
| Grenzreaktion / Expert-Sprung, Median | 0.62 % | 1.65 % |
| Expertgerichtete Grenzreaktion, Median | 0.40 % | 1.24 % |
| Vorzeitiger Offline-Start (< −0,1 s) | 45.0 % | 100.0 % |
| Start innerhalb ±0,1 s | 25.0 % | 0.0 % |
| Verspäteter Start (> +0,1 s) | 3.8 % | 0.0 % |
| Kein Start im Fenster | 26.2 % | 0.0 % |
| Startzeit, Median der gefundenen Starts | -0.15 s | -0.38 s |

Startkriterium: XY > 0,25 und Zielcosinus > 0,5 für drei aufeinanderfolgende Frames. Früher als −2 Frames = vorzeitig, ±2 Frames = pünktlich, später als +2 = verspätet; kein Start im ±0,5-s-Fenster separat. Startzeit-Median nur unter gefundenen Starts. Die deterministische direkte Policy wird für diese Prozentwerte über 20 Demos bewertet, Diffusion über 160 Demo/Draw-Verläufe. Der Bootstrap aggregiert zuvor die Diffusionsdraws pro Demo; seine Unsicherheit beschreibt Validierungsdemos, nicht unbekannte Trainingsseed-Variation.

## Vier Phasenbereiche

Stabiler Lift: Offsets −10…−6; unmittelbar davor −2/−1; unmittelbar danach 0/1/2; stabiler Transport +6…+10. XY/Z in der Tabelle sind Mittelwerte. Der Richtungs-Cosinus und das XY/Expert-Verhältnis werden nur bei Expert-XY > 0,1 gemessen; bei Lift-Aktionen ist die Richtung kleiner XY-Komponenten kein sinnvoller Fehlerindikator. Klarer Lift: XY < 0,12, Z > 0,02, Gripper geschlossen. Klarer Transport: XY > 0,25, zum Ziel, Z < −0,05, geschlossen.

| Bereich | Modell | XY-Betrag | Z-Aktion | XY/Expert, Median | Richtungs-Cosinus | Lift-Modus | Transport-Modus |
|---|---|---:|---:|---:|---:|---:|---:|
| Stabiler Lift | diffusion | 0.349 | -0.010 | nicht definiert | nicht definiert | 36.8 % | 32.4 % |
| Stabiler Lift | direct | 0.270 | 0.172 | nicht definiert | nicht definiert | 40.0 % | 18.0 % |
| Unmittelbar davor | diffusion | 0.458 | -0.118 | nicht definiert | nicht definiert | 25.3 % | 45.6 % |
| Unmittelbar davor | direct | 0.618 | -0.225 | nicht definiert | nicht definiert | 0.0 % | 100.0 % |
| Unmittelbar danach | diffusion | 0.461 | -0.139 | 34.0 % | 0.610 | 24.0 % | 47.9 % |
| Unmittelbar danach | direct | 0.641 | -0.247 | 60.2 % | 0.995 | 0.0 % | 100.0 % |
| Stabiler Transport | diffusion | 0.298 | -0.041 | 28.7 % | 0.506 | 25.0 % | 27.0 % |
| Stabiler Transport | direct | 0.529 | -0.070 | 76.0 % | 0.998 | 0.0 % | 57.0 % |

[Aktionsprofile um den Umschaltpunkt](boundary_profiles.png) zeigen, ob die Ausgabe einen Sprung oder eine geglättete Übergangszone bildet. Ein größerer XY-Betrag oder ein guter durchschnittlicher Transportmodus allein ist noch kein korrekter Umschaltmechanismus. [Vollständige Zahlen einschließlich Richtungsfehler und Gripper-Öffnungen](analysis.json).

## Rollouts: 40 gemeinsame Startzustände

Seeds 46000–46019 bleiben erhalten; hinzu kommen 46020–46039. Alle 40 initialen Zustands-Hashes sind zwischen Modellen identisch. Die ersten 20 unveränderten Diffusions-Rollouts wurden bitgleich aus der bisherigen Diagnose übernommen, inklusive 500-Schritt-Horizont. Dort gibt es keinen nativen Stack-Erfolg, daher benötigt ein stabiler Stack keine zusätzliche Verifizierung. Neue Rollouts: höchstens 500 Schritte, bei Erfolg früher beendet, jeweils weitere 40 Policy-Schritte für zwei Sekunden Stabilitätsprüfung. Keine Aktionen korrigiert.

**Alle 40 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
| Greifen | 31/40 | 37/40 |
| Anheben | 24/40 | 37/40 |
| Expert-ähnliche volle Lift-Höhe | 4/40 | 10/40 |
| Transport begonnen | 15/40 | 37/40 |
| Vorzeitiger Transport | 17/40 | 27/40 |
| 3-cm-Zielbereich | 4/40 | 37/40 |
| Positioniert | 0/40 | 37/40 |
| Abgesenkt | 0/40 | 36/40 |
| Release | 0/40 | 30/40 |
| Stack, auch vorübergehend | 0/40 | 28/40 |
| Stabiler Stack, weitere 2 s | 0/40 | 28/40 |
| Volle Lift-Höhe vor Transportbeginn | 1/40 | 8/40 |

**Bisherige 20 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
| Greifen | 17/20 | 19/20 |
| Anheben | 13/20 | 19/20 |
| Expert-ähnliche volle Lift-Höhe | 3/20 | 6/20 |
| Transport begonnen | 9/20 | 19/20 |
| Vorzeitiger Transport | 10/20 | 13/20 |
| 3-cm-Zielbereich | 4/20 | 19/20 |
| Positioniert | 0/20 | 19/20 |
| Abgesenkt | 0/20 | 19/20 |
| Release | 0/20 | 18/20 |
| Stack, auch vorübergehend | 0/20 | 17/20 |
| Stabiler Stack, weitere 2 s | 0/20 | 17/20 |
| Volle Lift-Höhe vor Transportbeginn | 1/20 | 6/20 |

**Zusätzliche 20 Starts:**

| Stufe | Diffusion | Direkt |
|---|---:|---:|
| Greifen | 14/20 | 18/20 |
| Anheben | 11/20 | 18/20 |
| Expert-ähnliche volle Lift-Höhe | 1/20 | 4/20 |
| Transport begonnen | 6/20 | 18/20 |
| Vorzeitiger Transport | 7/20 | 14/20 |
| 3-cm-Zielbereich | 0/20 | 18/20 |
| Positioniert | 0/20 | 18/20 |
| Abgesenkt | 0/20 | 17/20 |
| Release | 0/20 | 12/20 |
| Stack, auch vorübergehend | 0/20 | 11/20 |
| Stabiler Stack, weitere 2 s | 0/20 | 11/20 |
| Volle Lift-Höhe vor Transportbeginn | 0/20 | 2/20 |

- **diffusion:** volle Lift-Höhe vor Transport 1/40; maximale Würfelhöhe pro Episode, Median 0.915 m, Maximum 1.082 m; Höhe beim Transportstart, Median 1.023 m; XY-Abstand beim Transportstart, Median 17.85 cm (n=15).
- **direct:** volle Lift-Höhe vor Transport 8/40; maximale Würfelhöhe pro Episode, Median 1.039 m, Maximum 1.050 m; Höhe beim Transportstart, Median 1.036 m; XY-Abstand beim Transportstart, Median 14.16 cm (n=37).

Anheben: B > 0,88 m. Volle Expert-ähnliche Höhe: gehaltenes B ≥ 1,045 m und EEF ≥ 1,049 m für drei Schritte. Transport: gehaltenes B > 0,98 m, XY-Geschwindigkeit > 0,02 m/s, Zielcosinus > 0,5 für drei Schritte. **Volle Höhe irgendwann erreicht ist kein korrekt getimter Lift**; zusätzlich oben „volle Höhe vor Transport“ und vorzeitige Bewegungen. Vorzeitige Bewegung prüft das Bewegungskriterium vor Erreichen beider Höhenschwellen bei B > 0,88 m. Positionierung <9 mm XY, Absenken 40±8 mm über Ziel, Release mit Würfelkontakt, nativer Stack und weitere zwei Sekunden Stabilität getrennt. [Individuelle Diffusions-Metriken](diffusion/rollouts/results.json), [Direkt-Metriken](direct/rollouts/results.json).

## Interpretation und Grenzen

Die fehlende scharfe Lift→Transport-Umschaltung ist nicht spezifisch für Diffusion: Beide Modelle reagieren unmittelbar an der Expert-Grenze schwach und zeigen eine geglättete Übergangszone. Der direkte Predictor reagiert im Median stärker (1,65 % statt 0,62 % des Expert-Sprungs), startet aber auf allen 20 Expert-Validierungsverläufen zu früh, statt den Sprung nachzubilden. Gleichzeitig erreicht er 28/40 stabile Stacks gegenüber 0/40 bei Diffusion, mit 17/20 auf den bisherigen und 11/20 auf den zusätzlichen Starts. Im stabilen Expert-Transport trifft er die Richtung wesentlich zuverlässiger (mittlerer Cosinus 0,998 statt 0,506; falsche Richtung 0 % statt 19,6 %) und erzeugt stärkere XY-Aktionen (mediane Expert-Stärke 76,0 % statt 28,7 %). Die geringe Umschaltsensitivität lässt sich daher nicht allein durch das stochastische Diffusionsziel erklären. Für diese Aufgabe ist ein stochastisches Diffusionsmodell unter den getesteten Bedingungen nicht erforderlich. Der große Closed-Loop-Vorteil belegt die Brauchbarkeit der direkten Baseline, aber nicht, dass sie den abrupten Expert-Wechsel gelernt hat oder dass ausschließlich Diffusion die Ursache ist.

**Expert-Timing ist hier nicht identisch mit Aufgabenlösbarkeit:** 19 der 28 stabilen Direkt-Stacks erreichen die volle Expert-ähnliche Höhenschwelle nicht und werden als vorzeitiger Transport gezählt. Diese Diagnosemarkierung darf bei einem anschließend stabilen Stack nicht automatisch als Fehler der Gesamtaufgabe interpretiert werden. Das Direktmodell nutzt einen kontinuierlicheren Übergang bei geringerer maximaler Höhe als der Expert. Es reproduziert also nicht exakt dessen Phasenwechsel, kann aber dennoch sicher genug platzieren und loslassen. Native Erfolge werden zusätzlich auf allen 40 Folgeschritten geprüft: keine gehaltenen Würfel, fortbestehender Würfelkontakt; [physische Erfolgskontrolle](success_tail_audit.json).

Als nächster Schritt erscheint eine Bestätigung dieser direkten Baseline mit mehreren **Trainingsseeds** sinnvoll, bevor neue Controller oder Hierarchien eingeführt werden. Die 70-%-Stackrate stammt von einem Trainingsseed; 85 % auf den bisherigen und 55 % auf den zusätzlichen Starts zeigen bereits eine relevante Abhängigkeit von der Startverteilung. Für die spezielle Umschaltfrage bleiben ein kontinuierlicherer Expert-Zielverlauf oder die präzise Abbildung des abrupten Action-Ziels Gegenstände weiterer isolierter Vergleiche; beides wurde hier nicht geändert. Der Befund rechtfertigt nicht, allein wegen der geglätteten Expert-Grenze ein komplexeres stochastisches Modell vorauszusetzen.

Dieser Versuch vergleicht **Modellstruktur und Lernziel gemeinsam**, nicht nur einen Loss bei identischer Architektur: Residual-MLP mit direktem Action-MSE versus bedingtes zeitliches UNet mit Epsilon-MSE und DDIM. Vergleichbare Kapazität, Inputs, Daten, Budget und Ausführung reduzieren andere Unterschiede, erlauben aber keine eindeutige kausale Zuordnung zu Diffusion allein. Ein Trainingsseed je Modell; zusätzliche Startzustände sind keine zusätzlichen Trainingsseeds. Auch EMA, tanh-Ausgabebegrenzung versus Diffusions-Clipping und die unbekannte historische Ziehfolge begrenzen die Isolation. Kein weiteres Modell und keine zusätzliche Methode wurde in diesem Versuch getunt.

## Gespeicherte Artefakte

Finaler Direkt-Checkpoint enthält Rohnetz, EMA, AdamW-Momente, LR-Scheduler, EMA-Step und vollständige Konfiguration. Diffusionsreferenz und deren Konfiguration bleiben unverändert verlinkt. Direkte Panel- und Gesamt-Datensatz-Predictions, gepaarte Grenzreaktionen, alle Rollout-Metriken und Simulatorzustände sind gespeichert. Neue Rollouts speichern zusätzlich die tatsächlich verwendeten Zwei-Frame-Observations. Videos sind Replays gespeicherter Zustände:

- Seed 46000: [Zustands-/Aktionsvergleich](rollout_pair_46000.png), [Diffusion-Video](diffusion/rollouts/46000.mp4), [Direkt-Video](direct/rollouts/46000.mp4).
- Seed 46001: [Zustands-/Aktionsvergleich](rollout_pair_46001.png), [Diffusion-Video](diffusion/rollouts/46001.mp4), [Direkt-Video](direct/rollouts/46001.mp4).
- Seed 46003: [Zustands-/Aktionsvergleich](rollout_pair_46003.png), [Diffusion-Video](diffusion/rollouts/46003.mp4), [Direkt-Video](direct/rollouts/46003.mp4).

[Isolationsprüfung](verification.json). Reproduktion mit `praxis/.venv/Scripts/python.exe` und Skripten in `experiments/stack_diagnostics/stack_followup_20261001/scripts`: `train_direct.py`, `offline_direct.py`, `evaluate_direct_comparison.py diffusion|direct`, `analyze_direct.py`, `verify_direct.py`, `artifacts_direct.py`, `report_direct.py`. Training verweigert das Überschreiben eines Endcheckpoints; für eine Replikation den Ausgabeordner wechseln.
