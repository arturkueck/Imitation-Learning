"""Document the validated protocol before sealing and background evaluation."""
import ast,json,platform,importlib.metadata
from pathlib import Path
OUT=Path(__file__).resolve().parent
read=lambda p:json.loads((OUT/p).read_text())
assert read('unet_config_fix_verified.json')['passed']
assert read('anchor_preflight_v3/complete.json')['episodes']==30
controls=read('anchor_preflight_v3/results.json')
assert len(controls)==30 and all(r['sustained_success'] and r['exact_saved_physical_state'] and r['saved_state_sha256']==r['replayed_state_sha256'] for r in controls)
assert read('preflight_v3/complete.json')['episodes']==3
for p in OUT.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))

p=OUT/'DIAGNOSE.md';text=p.read_text(encoding='utf-8')
text=text.replace('Betrag/Dauer beeinflussen die Fingerstellung.','Der Panda-Gripper verwendet das Vorzeichen (`np.sign`) und die Dauer des Kommandos; dessen Betrag ist hier keine proportionale Greiferposition.')
text=text.replace('Anker und Zwei-Frame-History kommen aus dem reproduzierten Expert-Prefix, anschließend ausschließlich Live-Observations.','Nach dem Prefix wird der exakte gespeicherte physikalische Ankerzustand eingesetzt, OSC auf achieved-goal aktualisiert und die gespeicherte History t−1,t installiert. Anschließend ausschließlich Live-Observations. So bleiben Gripper-Erinnerung und die exakte Expert-Geometrie kontrolliert.')
text+='''

## Neuer Audit und abgeschlossene technische Kontrollen

Aus den vorhandenen 40 C-Rollouts je Modell, ohne neue Policy-Leistungsbewertung:

- Gripper-Vorzeichenwechsel pro Episode, Median: C-Diffusion **18**, C-Direct **2**. Insgesamt 32/37 Grasp-Verlustereignisse; davon 29/6 außerhalb der gültigen Release-Geometrie. Von den 29 irregulären Diffusionsereignissen haben 24 gleichzeitig ein Öffnungskommando und 20 einen Zielabstand >3cm. Direct: 31/37 Verlustereignisse liegen in gültiger Release-Geometrie; Verlust allein ist kein Fehlerindikator.
- Bei gehaltenem Lift und klar außerhalb der Release-Region nur 30/3099 Diffusionsframes mit Öffnungskommando, Direct 0/2827. Die vielen gesamten Vorzeichenwechsel dürfen daher nicht mit einem ständig öffnenden, gehaltenen Transport gleichgesetzt werden. Diagnose der Öffnung muss Ereignis und Region berücksichtigen.
- Geometrischer Abstand zum nächsten Trainings-Expertframe (B−A, EEF−B und Fingerstellung, train-standardisiert): 797/3099 Diffusionsframes mit gehaltenem Lift überschreiten das 95%-Quantil der Validierungs-Expertabstände, Direct 135/2827. Das ist **25,7% gegenüber 4,8%**, ein Hinweis auf geometrische Verteilungsabweichung. Einzel-Frame-Nachbarschaft, unterschiedliche Phasenfrequenzen und erfolgreiche abweichende Direct-Verläufe begrenzen jede OOD-/Recovery-Interpretation. Rohwerte in geometric_coverage.json.
- **58** zufällige/Übergangsfenster stimmen mit dem tatsächlichen SequenceDataset überein: Observation-Fehler <1e−7, Action-Fehler 0. Drei Expert-Sequenzbilder zeigen pre-action-Observationen, Actions und sämtliche Phasengrenzen. Kein nachgewiesener Off-by-one.
- **0** antipodale Quaternion-Vorzeichenwechsel in allen 200 Demos. Einheitenlänge geprüft. Objektneigung ist separat aus gespeicherten Simulatorquaternionen ausgewertet, aber weiterhin kein Policy-Input.
- Trainings-Frameanteile: approach 12,77%, descent-to-grasp 15,98%, grasp 13,18%, lift 18,74%, transport inklusive alignment 13,52%, lowering 15,38%, release 10,43%, retreat 0%. Es gibt keine separate Alignment-/Stabilization-Phase im Expert-FSM; keine erfundenen unabhängigen Labels. Das Ende enthält kurze Release-/Stabilisierungsschritte, aber keinen vollständigen Retreat. Phasen zählen Ankerframes, nicht die effektive Loss-Masse aller überlappenden 16er-Chunks.
- Der separate Config-Fix besteht den Default-Initialgewichtsvergleich bitgenau und die echte Algo-Konstruktion mit abweichender kleiner Testarchitektur. Aktuelle C-Architektur/Weights unverändert.
- Restore-Vorversuche dokumentiert: erste reine Expert-Validierung fehlte Observation-Utils-Initialisierung; nach Korrektur scheiterte reines Prefix-Replay an 4,884mm EEF-Abweichung in demo_22. Keine Präzisionstoleranz erweitert. V3 rekonstruiert Controller-/Gripper-Erinnerung per Prefix, setzt danach exakt state[k] ein und installiert die aufgezeichnete History. **Alle 30 Anker physikalisch bitgleich mit den gespeicherten Zuständen; Expert-Kontrolle 30/30 stabil erfolgreich.**
- V3-Smoke prüft dieselbe Restore-Methode, C-Normalisierung und Diffusions-Chunk/Queue/Inversionsparität für einen Anker und zwei Policy-Hauptschritte plus Tail. Das ist ausdrücklich keine Qualitätsschätzung von Direct/Diffusion.

Nächste Ausführung: ausschließlich Exp0-Reproduktion und Exp1-Phasenvergleich, eigener Hintergrundprozess; danach Prozessende. Aktuell noch keine neuen belastbaren Policy-Ergebnisse und keine Trainingsänderung gewählt.
'''
p.write_text(text,encoding='utf-8')
p=OUT/'README.md';text=p.read_text(encoding='utf-8')
text=text.replace('Gültigkeit erfordert initialen Grasp, Position-/Fingerabweichung <2mm gegenüber Demo und identische replayte Start-Hashes zwischen Modellen.','Nach Rekonstruktion der Controller-/Gripper-Erinnerung wird exakt der gespeicherte state[k] wiederhergestellt, der OSC-achieved-goal aktualisiert und die gespeicherte t−1,t-History eingesetzt. Gültigkeit erfordert initialen Grasp, Position-/Fingerabweichung <2mm gegenüber Demo und bitidentische gespeicherte/aktive Start-Hashes zwischen Modellen.')
text=text.replace('`preflight/` ist ein technischer Test','`preflight_v3/` ist ein technischer Test')
text+='\nAlle 30 Expert-Kontrollen in `anchor_preflight_v3/` abgeschlossen und stabil erfolgreich. Ältere technische Vorversuche (`preflight/`, `anchor_preflight/`, `anchor_preflight_v2/` und zugehörige Logs/Fehler) bleiben erhalten; sie gelten nicht als finale Vorprüfung. `object_orientation_audit.json` und `geometric_coverage.json` ergänzen die statische Diagnose.\n'
p.write_text(text,encoding='utf-8')
old=read('validate_anchors_failed.json');old['attempt']='pure_prefix_replay_v2';old['superseded_by']='anchor_preflight_v3/complete.json';old['policy_failure']=False
(OUT/'validate_anchors_failed.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
versions={name:importlib.metadata.version(name) for name in ('torch','robomimic','robosuite','diffusers','mujoco','numpy','h5py','scipy')}
(OUT/'environment_versions.json').write_text(json.dumps(dict(python=platform.python_version(),packages=versions),indent=2),encoding='utf-8')
result=dict(passed=True,training=False,expert_anchor_controls_passed=30,exact_saved_state_restores=30,smoke_completed=True,normalization_and_chunk_queue_inversion_checked=True,random_and_transition_loader_checks=58,unet_default_initial_weight_parity=True,previous_failed_technical_attempts_retained=True,automatic_followup=False)
(OUT/'preparation_verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
