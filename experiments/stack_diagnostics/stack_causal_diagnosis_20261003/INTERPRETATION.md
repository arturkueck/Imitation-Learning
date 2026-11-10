# Interpretation von Exp0 und Exp1

Die Ergebnisse stützen zwei Engpässe: unzuverlässige Transport-/Zielsteuerung und ein zusätzlicher Fehler beim Release bzw. Erhalten des bereits gebildeten Stacks. Ein ausschließlich durch frühe Rollout-Fehler verursachtes Versagen ist als hinreichende Erklärung geschwächt. Keine neue Trainingsmethode ist hier bestätigt.

## Gültigkeit und Reproduktion

Alle 381 beim Abschluss gesicherten Dateihashes, beide Checkpoints und der Datensatz geprüft. 40 Baseline-Rollouts und 90 Phasenfortsetzungen vollständig vorhanden. Für alle 30 Demo/Phasen-Gruppen sind die drei physikalischen Anfangszustände untereinander und mit dem HDF5 bitgleich; die initialen Zwei-Frame-Histories entsprechen exakt den gespeicherten Observationen. Expert-Kontrollen: 30/30 stabile Stacks. 9.816 Phase-Actions endlich und innerhalb der Controllergrenzen; 2.052 Diffusionschunks stimmen positionsgenau mit der Ausführung überein; 90 vollständige 40-Frame-Tails geprüft. Details: interpretation_verification.json.

Exp0 reproduziert **2/40 stabile Stacks**, dieselben erfolgreichen Start-IDs 46000 und 46004 sowie sämtliche ursprünglichen C-Phasenzahlen: Greifen 27, Lift 24, Transport 24, Position 12, Absenken 5, Release 3. Das bestätigt die Ergebnis-Reproduktion; eine bitidentische gesamte Trajektorienreproduktion wird hier nicht behauptet.

## Vollständige stabile Stacks aus Expert-Ankern

| Anfangsphase | Expert | C-Direct | C-Diffusion |
|---|---:|---:|---:|
| Nach Greifen | 5/5 | 1/5 | 0/5 |
| Nach vollständigem Lift | 5/5 | 2/5 | 0/5 |
| Mitte Transport | 5/5 | 4/5 | 1/5 |
| Ende Transport | 5/5 | 5/5 | 2/5 |
| Vor Absenken | 5/5 | 5/5 | 2/5 |
| Vor Release | 5/5 | 5/5 | 2/5 |

D/E sind zu Beginn bereits in der Positioniertoleranz; F ist zusätzlich bereits korrekt abgesenkt. Ihre 5/5 Positionierungen sind daher kein Nachweis neu gelernter Positionierung. Die nativen Stack-/Nachlaufergebnisse bleiben aussagekräftig, weil die Objekte initial noch gehalten werden.

## Engpass 1: Transport ist auch aus guten Expert-Zuständen unzuverlässig

Nach vorgegebenem vollständigem Expert-Lift erreicht Diffusion in **0/5** Fällen die gehaltene Positioniertoleranz; Direct erreicht diese in 5/5. Die minimalen gehaltenen XY-Abstände der Diffusion liegen bei 15,7–43,4mm, gegenüber der 9mm-Toleranz. Der Median der ersten XY-Action relativ zur Expert-Action beträgt 26,8%; bei Direct 38,0%. Diese erste Action ist eine Grenzreaktion, kein Vergleich über den vollständigen Transport; aus der Mitte des Transports beträgt dasselbe Verhältnis 89,0%/87,5%, während die stabilen Abschlüsse trotzdem 1/5 bzw. 4/5 sind. Eine einzelne plausible Action genügt somit nicht.

Der schlechte vollständige Ablauf entsteht nicht ausschließlich beim Greifen oder durch einen vorher zu niedrigen Lift. Auch mit originalen Expert-Liftzuständen/Histories ist die Fortsetzung schwach. Nach Mitte Transport bleibt Diffusion bei 1/5 gehaltenen Positionierungen und 1/5 stabilen Stacks; Direct bei 5/5 Positionierungen und 4/5 stabilen Stacks.

## Engpass 2: Release und anschließende Stabilität sind eigenständige Probleme

Selbst unmittelbar vor Release erreicht Diffusion nur **2/5 stabile Stacks**, obwohl alle fünf Fälle initial korrekt positioniert und abgesenkt sind. Expert und Direct schaffen 5/5. Diffusion erreicht vier gültige Release-Ereignisse und vier native Stack-Erfolge; zwei davon gehen im Nachlauf verloren.

Die Einzelverläufe zeigen unterschiedliche Fehler:

- demo_20: Start-XY 4,64mm innerhalb der Toleranz; kein gültiger Release. Beim ersten Grasp-Verlust nach 2,7s bereits 13,09mm XY-Abstand; später Wiederaufnahme/Weiterhalten und 65,85mm Abstand nach 6s. 26 Gripper-Vorzeichenwechsel. Der bereits gute Ausgangszustand wird verlassen.
- demo_7: gültiger Release nach 0,8s, nativer Stack anschließend erreicht. Im Tail bleibt B ungegriffen und Würfelkontakt besteht in allen 40 Frames, aber Success fällt aus. Beim ersten Ausfall beträgt die Winkelgeschwindigkeit des Basiswürfels 0,377rad/s, oberhalb der nativen 0,3rad/s-Grenze. Der Stack muss nicht sichtbar auseinanderfallen, um das definierte Stabilitätskriterium zu verlieren.
- demo_24: gültiger Release nach 1,3s und anschließend nativer Stack. Im Tail ebenfalls durchgehend Kontakt und kein B-Grasp; am ersten Success-Ausfall liegen A-Winkelgeschwindigkeit bei 0,306rad/s und B-Translationsgeschwindigkeit bei 0,0311m/s, oberhalb 0,3rad/s bzw. 0,03m/s.
- demo_22 und demo_29: vollständiger Stack und alle 40 Nachlaufframes erfolgreich.

Die Geschwindigkeitsüberschreitungen erklären die Verletzung des Erfolgskriteriums, aber noch nicht ihre isolierte physische Ursache. Eine Verursachung durch Arm-/Gripperkontakt, Rotation oder konkrete letzte Commands erfordert eine getrennte Intervention. Der Trace speichert nur B-Grasp, nicht den zusätzlichen nativen Grasp-Check für A.

Direkt vor Release: median **7** Gripper-Vorzeichenwechsel bei Diffusion, **0** bei Direct/Expert. Erste gültige Releases in den vier Diffusionsfällen nach 0,4–1,3s; bei Direct nach 0,3–0,6s (Median 0,3s). Ein zusätzlicher Timing-/Modusfehler ist damit gestützt. Allerdings sind die beiden Tail-Verluste gerade keine erneuten B-Grasps und kein Kontaktverlust; eine reine Öffnungssperre darf deshalb nicht als Lösung aller späten Fehler vorausgesetzt werden.

## Einordnung der Hypothesen

- Grundsätzlich defekte Action-/Normalisierungs-/Queue-Schnittstelle: durch Reproduktion, Checks und echte C-Erfolge weiter geschwächt. Das schließt andere Lern-/Implementierungsprobleme nicht generell aus.
- Ausschließlich früh entstandene State-Distribution-/Compounding-Fehler: als alleinige Erklärung geschwächt. Expert-Lift- und Prä-Release-Starts beseitigen das Versagen nicht. Abweichungen im Verlauf können weiterhin beitragen.
- Unzuverlässige bedingte Transport- und späte Steuerung: durch den Phase-Vergleich gestützt. Welcher Anteil auf UNet-Konditionierung, Epsilon-Lernziel, Datengewichtung oder Action-Repräsentation entfällt, bleibt offen.
- Gripper-Timing/Neusampling-Inkohärenz: durch Vorzeichenwechsel und verspätete Releases gestützt, aber noch nicht kausal isoliert.
- Skalierung als alleinige Erklärung: weiterhin nicht gestützt; C-Verbesserung ist real, aber selbst nahe am Ziel bleiben Fehler.

Auch Direct scheitert aus frühen Expert-Ankern häufiger als in seiner normalen vollständigen Evaluation. Daraus folgt keine Widerlegung der bisherigen Direct-Erfolgsrate: andere Starts/Expert-Verteilung, nur fünf ausgewählte Validierungsdemos, andere History/Controller-Übergabe und 120 statt 500 Hauptschritte. Dieser Befund mahnt zur vorsichtigen Interpretation besonders von A/B. Die späten Expert/Direct-Erfolge zeigen trotzdem, dass die späten Anker ausführbar sind.

## Kleinster nächster Test

Gemäß vorab vereinbarter Reihenfolge zuerst **Exp2 als isolierte C-Gripper-Diagnose**, ohne Training und ohne Armaktionsersatz: Öffnen nur bei bereits sicher gehaltenem Objekt und eindeutig vor dem Releasebereich unterdrücken. Release am Ziel bleibt möglich. Gleiche Anker/Starts und Noise-Seeds wie Kontrollarm; native vollständige Stack-Stabilität als Primärmetrik, gehaltene Zielannäherung und irreguläre Grasp-Verluste ergänzend. Noch kein binärer Head und keine neue Trainingsrepräsentation.

Wenn die Positionierung bzw. vollständige Erfolgsrate nicht deutlich steigt, ist die getestete vorzeitige Öffnung keine hinreichende Erklärung. Wenn sie steigt, zeigt dies einen Gripper-Beitrag; eine spätere separate Lernänderung benötigt anschließend mehrere Trainingsseeds. Die beiden dokumentierten Tail-Instabilitäten können durch diesen Test unverändert bleiben und benötigen dann eine eigene Diagnose. Exp3 execute1/2/4 erst danach, gleiche Gewichte und sonst identische Konfiguration.

Fünf Demos pro Phase, dieselben Demos über alle Phasen, ein Trainingsseed und je ein Noise-Verlauf: keine unabhängigen 30 Wiederholungen, keine robuste Erfolgsraten- oder Signifikanzbehauptung. 120 Hauptschritte entsprechen 6s; längere erfolglose Fälle sind zeitlich zensiert. **2/5 aus späten Expert-Zuständen ersetzt niemals die 2/40-Gesamterfolgsrate.**

Diese Interpretation wertet ausschließlich gespeicherte Ergebnisse aus. Kein Training, keine neuen Simulatorrollouts und kein Folgeexperiment gestartet. Einzelwerte: interpretation_details.json; reproduzierbare Prüfung: interpret_results.py.
