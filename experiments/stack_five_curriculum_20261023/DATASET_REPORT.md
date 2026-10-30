> **Messkorrektur24.10.2026:** Die zusätzliche Prüfung vollständiger Fingerkontaktfreiheit war wegen eines Gripper-Dictionary-Fehlers unwirksam. Historische Quoten gelten für die damalige implementierte Metrik. [Details und Grenzen](MEASUREMENT_CORRECTION.md).

# Datensatzbericht — abgeschlossen



Alle drei vorab begrenzten Sammlungen vollständig, keine zusätzliche Curriculum-Fünfersammlung nach gescheitertem Vierergate. Nur stabile vollständige Episoden als Actorziele, keine neuen Skriptexpertenaktionen. Originalsplit180/20 Demos bleibt unverändert.



| Sammlung | Versuche Train/Valid | Erfolge Train/Valid | akzeptierte Frames Train/Valid |

|---|---:|---:|---:|

| curriculum_n3_cycle0 |100/20|52/10|17069/3336|

| curriculum_n4_cycle0 |100/20|27/8|12858/3838|

| direct_n5_cycle0 |100/20|6/3|3829/1901|



## Herkunft und Auswahlbias



### curriculum_n3_cycle0

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed1.pth / train: 18/34 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed2.pth / train: 18/33 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed3.pth / train: 16/33 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed2.pth / valid: 7/7 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed3.pth / valid: 2/7 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed1.pth / valid: 1/6 vollständig erfolgreich

### curriculum_n4_cycle0

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_five_curriculum_20261023\training\curriculum_n3_c0_seed1\best.pth / train: 27/100 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_five_curriculum_20261023\training\curriculum_n3_c0_seed1\best.pth / valid: 8/20 vollständig erfolgreich

### direct_n5_cycle0

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed1.pth / train: 4/34 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed2.pth / train: 1/33 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed3.pth / train: 1/33 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed2.pth / valid: 0/7 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed3.pth / valid: 2/7 vollständig erfolgreich

- F:\Desktop\Programmieren\IT\Imitation Learning\experiments\stack_self_imitation_20261023\final_test\C_seed1.pth / valid: 1/6 vollständig erfolgreich



Alle Fehlschläge bleiben mit vollständigen Pre-action-Inputs archiviert; im Training werden ausschließlich erfolgreiche Episoden verwendet. Das bevorzugt leichtere Starts und erfolgreiche Aktionssequenzen. Zyklische Teacherzuordnung vor Ergebnissen, aber keine Gleichverteilung der akzeptierten erfolgreichen Teacherbeiträge garantiert. Vierer-Teacher ist ausschließlich das bestätigte neue DreiermodellSeed1; daraus folgt kein Gatebestehen der anderen Lernseeds. Die9 erfolgreichen direkten Fünferepisoden werden wegen nur6 Trainingserfolgen nicht für ein Training verwendet.



## Integrität, Splits und Labels



Alle360 Episoden wurden im Collector auf exakte Einzelbild-Aktionsreproduktion des jeweiligen Teachers geprüft. Unabhängige Dateiaudits in den stündlichen Kontrollen prüften endliche Werte, genaue Post-/Pre-action-Verkettung, Rekonstruktion der10 Modelleingaben, Nullrotationen und Übereinstimmung von Erfolgsflag und mindestens50 durchgängigen stabilen Frames. Initialzustandshashes innerhalb jeder Höhe Train/Valid disjunkt. Technikepisode399001 und vorbereitete Türme sind keine Trainingsdaten.



Neue Sammlung:3er215000–215099 Training,215100–215119 Validierung;4er220000–220099/220100–220119;direkte5er275000–275099/275100–275119. Entwicklung310000+1000*N+[0,49], Bestätigung320000+1000*N+[0,49], reservierte Tests360000+1000*N+[0,99] für5 bzw.[0,49] sonst. Keine alten84000/85000/125000/126000-Endtests als neue Trainingsdaten. Bereits vorhandener3er-Replay stammt aus der vorigen explizit freigegebenen Sammlung, deren Manifest ebenfalls eingefroren ist.



Batch64 enthält32 Originalexpertframes,16 frühere Höhen und16 neue Höhe; phasen-/episodenbalanciert. Frühere Höhen werden zunächst gleichverteilt gewählt. Auf dieser Session wurden nur3er/4er-Optimierungen ausgeführt. Neue y-Abschlussflags sind Teacher-Pseudolabels zur Diagnose; BCE lernt ausschließlich Originalexpertlabels. Kein RL.



## Dateien und unveränderte Quellen



NPZ enthält x,a,p,y,phase_steps,anchor,stage,retreat,pre_obs,post_obs,pre_state,initial,prob,valid2,valid,prefix_valid,velocities,contacts,fingers,controller_event. Manifest enthält Seed,Höhe,Split,Erfolg,Frames,Teacherpfad/-hash,Initialzustandshash und Pfad. Daten sind Zustands-/Aktionsdaten, keine neuen RGB-Demos. Alle vollständigen Sammlungen bleiben unter datasets/ mit model.xml und manifest.json.



Original-HDF5-SHA256:5222cbf96dc6218389d491fe7b99449295dcfc9bceb3bab8f8776ffff19fe6f8. Quellen-/Arrays-/Parentmanifest-Hashes und Teacherhashes am Abschluss erneut geprüft. Detailaudits:dataset_audit_n3.json,dataset_audit_n4.json,dataset_audit_direct_n5.json; vollständige Herkunft und Kosten in final_analysis.json.



Die ursprünglichen Zweiwürfeldaten und historischen Vortrainingskosten bleiben notwendig; der aktuelle Versuch enthält bereits eigene Dreierdaten und ist kein Nachweis ausschließlich aus Zweierdaten. Vollständige Endergebnisse und Grenzen stehen in RESULTS.md.