import json,hashlib,time,tomllib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;O=S/'method_reference_001';ROOT=S.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json');status=read(S/'status.json');pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30 and session['deadline_unix']==status['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
assert tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())['status']=='ACTIVE'
assert all(status['progress'][arm]['optimizer_updates']==2000 for arm in ['B0','B1']) and status['progress']['evaluation']['episodes_completed']==104
processes={}
for p in [O,O/'preflight_001',O/'verification_001']:
    sup=read(p/'supervisor_result.json');launch=read(p/'launch.json');identity=dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])
    assert not alive(sup['worker']) and not alive(identity) and sup['returncode']==0 and sup['worker_job_closed'] and launch['deadline_unix']<=session['deadline_unix']
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_identity=identity,both_exited=True,worker_job_closed=True,elapsed_seconds=sup['elapsed_seconds'])
r=read(O/'result.json');v=read(O/'verification_001/result.json');pref=read(O/'preflight_001/result.json')
assert r['state']=='REFERENCE_IMPLEMENTATION_AND_EXPLORATORY_AUDIT_COMPLETE' and v['state']=='NUMPY_FORMULA_CACHE_AND_ACTION_SUPPORT_VERIFIED' and v['main_result_sha256']==sha(O/'result.json')
for name,digest in read(O/'source_hashes.json').items():assert sha(O/name)==digest,name
production=read(S/'attempts/attempt_002/source_hashes.json')
for name in ['praxis/src/robomimic_ext/contraction_bc.py','praxis/src/robomimic_ext/sensor_bc.py']:assert production[str(Path(name))]==sha(ROOT/name)
assert r['initial_parameter_sha256']==r['final_parameter_sha256'] and r['checkpoint_sha256_before']==r['checkpoint_sha256_after'] and r['dataset_sha256_before']==r['dataset_sha256_after']
assert r['counts']['optimizer_constructions']==r['counts']['optimizer_updates']==r['counts']['physics_steps']==0 and all(x['state']=='VERIFIED' for x in r['finite_difference']['checks'].values())
featuremax={k:max(x['feature_absolute_errors'][k] for x in r['rows']) for k in r['policy_feature_keys']}
semanticmax={k:max(x['sensor_vs_physical_feature_errors'][k] for x in r['rows']) for k in r['policy_feature_keys']}
physical_error=max(x['physical_action_reproduction_error'] for x in r['rows']);semantic_error=max(x['sensor_vs_physical_action_max_difference'] for x in r['rows'])
cache=sum(x['cache_identification_available'] for x in r['rows']);mapping=sum(x['feature_mapping_passed'] for x in r['rows']);region=sum(x['action_region_cases'] for x in r['rows'])
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',trigger_utc='2026-10-04T12:39:46.985Z',
           utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,coordinator_identity=pid,coordinator_alive=True,deadline_unix=session['deadline_unix'],heartbeat_status='ACTIVE',
           optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,processes=processes,reference_state=r['state'],verification_state=v['state'],
           new_policy_updates=0,new_response_fits=0,new_physics_steps=0,cache_available_frames=cache,planned_frames=12,feature_mapping_passed=mapping,
           region_cases=region,planned_cases=72,summaries=r['summaries'],parameter_sha256_unchanged=r['final_parameter_sha256'],production_algorithms_unchanged=True,
           hashes={n:sha(O/n) for n in ['loss_reference.py','result.json','source_hashes.json','verification_001/result.json']},
           decision='Isolated algorithm reference implemented and numerical/parameter-gradient/NumPy checks passed; full features map12/12 but local response cache only8/12 after privileged physics. Empirical envelope still fails transfer, no training approval. Prepare final synthesis; keep coordinator/heartbeat ACTIVE to exact original deadline.')
table='\n'.join(f"| {name} | {x['weighted_perturbations']}/72 | {x['active_perturbations']}/72 | {x['batch_mean_loss']:.7g} | {x['global_norm_ratio_to_BC']:.4f} | {x['global_cosine_to_BC']:.4f} |" for name,x in r['summaries'].items())
report=f'''# Isolierter Algorithmusentwurf: Rechenbarkeit und praktische Voraussetzungen

Stand {event['berlin']}. [Reine Tensorreferenz](loss_reference.py), [fixiertes Protokoll](PROTOCOL.md), [Eingangs-/Sourcehashes](selection.json), [exploratives Audit](result.json). **Kein Policytraining, keine neue Simulatoraktion und keine produktive Algo-Registrierung.** Bestehender Kontraktions- und Sensor-BC-Code sind gegen die ursprünglichen Pilotquellen unverändert. Wiederverwendung der bereits gesehenen error_margin_001-Daten ist ein Implementationsaudit, keine frische wissenschaftliche Bestätigung oder neuer Seed der Policy.

## Konkrete Änderung im Forschungsentwurf

L=L_BC+lambda/N * sum_i w_i relu((||delta_i A_i+DeltaAction_i B_i||/||delta_i||+epsilon_i)^2-rho^2), rho0.99. Volle7D-Aktionsdifferenz, lokale3D-Positionsantwortmatrix B_i7×3, getrennte offene Zustandsantwort A_i3×3, konstante Gültigkeitsannotation/Fehlerhülle. Alle Annotationen detached, Gradienten nur über Policyaktionen. Fehlende/nullgewichtete Cacheeinträge werden vor Norm/Matrixmultiplikation ausgeschlossen; NaN*0 wird vermieden. Ganzer geplanter Batchnenner, kein Hochskalieren durch Teilen nur durch gültige Fälle. Controllerseitiges Aktionsclipping und komponentenweise Identifikationsregion werden explizit berücksichtigt. BC bleibt das offizielle unclipped Expertenziel; lambda1 dient ausschließlich der Skalenmessung, kein hier gewählter Trainingswert.

Das ist eine implementierte Referenz eines vorgeschlagenen BC-Zusatzlosses. Sie liefert keine allgemeine Stabilität und setzt keine fachliche Trainingsfreigabe voraus. Die verwendete endliche empirische Fehlermarge **scheiterte zuvor** auf zehn von48 neuen gültigen Antworten; Formelkorrektheit macht sie nicht gültig. Im alten produktiven Loss ist diese Referenz nicht aktiv.

## Numerische und Gradientenkontrollen

Zehn reine Checks: undefined Cache bei Nullgewicht, konstante Annotationen ohne Gradient, unabhängige NumPyformel/voller Batchnenner,7D-Aktionsableitung, Rotations-/Gripperspalten, komplett maskierter Batch mit endlichen Nullgradienten, Ablehnung von Nullperturbation/nichtfinitem aktivem B/negativem epsilon, alle7Achsen der Aktionsregion. [Vorprüfung](preflight_001/result.json) bestanden; zufällige Aktionsrichtungsableitung Fehler5.83e-12. Die synthetische Gripperableitung prüft nur Implementationsfähigkeit, nicht physische Gripperwirksamkeit.

Richtungsableitung des eingefrorenen B0 auf vorab festem demo_38,t4: vier Varianten **4/4 VERIFIED**, Float64-Klon, eps1e-5, maximaler relativer Fehler {max(x['relative_error'] for x in r['finite_difference']['checks'].values()):.3g}, kein Kink zwischen den Prüfpunkten; Klon exakt restauriert, Hauptmodell unverändert. Unabhängig frisch geladene Policy plus NumPyformel rekonstruiert12Frames×4Varianten/72geplante Perturbationen, Masken/Featurezuordnung/Aktionsregion; maximaler Verlustunterschied {v['maximum_loss_difference']:.3g}, Ratiounterschied {v['maximum_ratio_difference']:.3g} durch Float32- versus NumPyrechnung, [Nachweis](verification_001/result.json).

## Cache, Featuresemantik und Abdeckung

Tatsächlich verwendete Policykeys: {', '.join(r['policy_feature_keys'])}. Vollständige Zuordnung der nominalen Features zum HDF5 an **{mapping}/12** Frames innerhalb vorab1e-6; maximale absolute Abweichungen {json.dumps(featuremax)}. Andere Simulatorobservables wie Jointvelocity sind hier keine Policyinputs. Lokale B-Matrix nur an **{cache}/12** Frames vorhanden, nach privilegierter vollständiger physischer Validierung; vier späte Kontaktframes haben fehlenden Cache. Dies ist zusätzliche Simulatorkalibrierung und kein vorher verfügbarer unabhängiger Sensorfilter.

Die getrennten nominalen M0/M2-Masken werden vor dem Loss berechnet. **Gewichte im Audit kombinieren diese Masken ausdrücklich mit Cacheverfügbarkeit aus dem früheren physikalischen Gate.** Dadurch wird die M0-Fehlannahme nicht zum brauchbaren M0-Filter umgedeutet: an diesem angenommenen ungültigen Frame fehlt B und die effektive Cachemaske ist null. Kosten, vollständiger Coverage-Nenner und Herkunft dieses privilegierten Labels bleiben offen ausgewiesen.

Komponentenweise Region um tatsächliche ±0.1nominalen Identifikationsaktionen: **{region}/72** Sensorperturbationen innerhalb; alle48Cachefälle innerhalb, zwei späte Fälle außerhalb. Die Prüfung gilt für den eingefrorenen B0, nicht für während Training veränderte Aktionen. Sensor- versus echte physische Perturbation der vier verwendeten Eingangsfeatures: maximale absolute Abweichungen {json.dumps(semanticmax)}, maximale Aktionsdifferenz {semantic_error:.3g}; unabhängig reproduzierte gespeicherte physische Aktionen maximal {physical_error:.3g} abweichend. Kleine Differenzen unter dieser kontrollierten Ersatzgeschichte sind kein Nachweis korrekter Recoverylabels oder Originalexpertgeschichte. Sensoraugmentation behält dieselbe Aktion bei; physische Recovery verlangt eine andere Label-/Dynamikbegründung.

## Wirksame Gradienten, lambda1 nur Diagnostik

| Variante | Gewichtete / geplante Fälle | Aktiver Loss / geplant | Batchloss | Gradientennorm / BC | Kosinus zu BC |
|---|---:|---:|---:|---:|---:|
{table}

Die feste Marge aktiviert zusätzliche Regularisierungsfälle, Maske und Cacheabdeckung verändern die Stärke. Die globalen Gradienten sind Mittelwerte über alle12Frames, nicht Normmittelwerte über nur gültige Beispiele. Kein daraus gewähltes lambda, keine Task-/Robustheits-/Konvergenzaussage. Späte ausgeschlossene Fälle behalten ihren BC-Loss; nur dieser Zusatzloss fehlt dort.

## Kosten und Status

Vorprüfungsworker {pref['elapsed_seconds']:.3f}s / Supervisor {processes['preflight_001']['elapsed_seconds']:.3f}s; Primärworker {r['elapsed_seconds']:.3f}s / Supervisor {processes['method_reference_001']['elapsed_seconds']:.3f}s; unabhängiger Worker {v['elapsed_seconds']:.3f}s / Supervisor {processes['verification_001']['elapsed_seconds']:.3f}s. Hauptauditcounts {json.dumps(r['counts'])}; unabhängige NumPygegenprüfung zusätzlich24Policyforwardbatches/84Inputs. Keine Optimizerkonstruktionen, Updates, Physiksteps oder neuen Antwortfits. Bestehende Kalibrierkosten gehören weiterhin zum Gesamtmethodenaufwand.

Alle Worker/-Supervisoren per PID plus Erzeugungszeit beendet, Jobs geschlossen. Parameter-SHA256 **{r['final_parameter_sha256']}**, Endcheckpoint **{r['checkpoint_sha256_after']}**, Dataset **{r['dataset_sha256_after']}**, jeweils unverändert. Code-SHA256 `{sha(O/'loss_reference.py')}`; Audit `{sha(O/'result.json')}`; Gegenprüfung `{sha(O/'verification_001/result.json')}`.

Fachliche Entscheidung: konkreter Lossentwurf jetzt implementiert und rechnerisch geprüft; preiswerte breite Cacheversorgung, dynamische Gültigkeit, übertragbare Fehlermarge, Skalenkontrolle und replizierter Trainingsnutzen weiterhin nicht etabliert. Kein ungeplanter neuer Trainingslauf. Sessioncoordinator/Heartbeat bleiben ACTIVE bis exakt15:11:19 Berlin. Nächster letzter Agentauftrag: [SESSION_CLOSEOUT.md](../SESSION_CLOSEOUT.md), Gesamtevidenz getrennt synthetisieren und erst nach tatsächlichem Deadlineende alle Prozesse/Wachhaltemodus prüfen und Automation pausieren.
'''
with (O/'RESULT.md').open('x',encoding='utf-8') as out:out.write(report)
closeout='''# Letzter Check und Abschluss der unveränderten Sechs-Stunden-Session

Der Algorithmusentwurf method_reference_001 ist abgeschlossen; kein weiterer Policytrainingslauf. Zuerst PILOT_INTERPRETATION und die letzten RESULTs lesen. Tatsächlichen Check mit UTC/Berlin und Prozessidentität protokollieren. Noch vor Deadline Session/Coordinator/ACTIVE und Pilot2000/2000Updates/104Episoden prüfen. Alte Quellen und alle Negative erhalten.

Bis zur fixierten Deadline04.10.2026,15:11:19.697Berlin (=13:11:19.697UTC) ACTIVE lassen. Der nächste Trigger ist voraussichtlich15:09:47Berlin, also **vor Deadline**: nicht vorschnell pausieren. Keine neue wissenschaftliche Jobkette mit nur90Sekunden Restfenster. Stattdessen abschließende Dataset-/Source-/Checkpoint-/Batch-/Start-/Update-/Episodenverifikation und Gesamtbericht SESSION_RESEARCH_REPORT.md in separatem Pfad schreiben; alten PilotRESULT.md erhalten. Primärliteratur, historischer Taskgewinn, ein Sensorpilotseed, lokale Dynamikdiagnosen und Lossimplementierung strikt getrennte Evidenz. Alle technischen Fehlversuche/Metadatenreparaturen und zusätzliche Simulator-/Kalibrierkosten bilanzieren. Hypothesenledger priorisieren und minimalen nächsten Versuch empfehlen, keine neue robuste Verbesserung behaupten.

Bei vorzeitigem Coordinatorfehler Ursache/Logs prüfen, keinen abgelaufenen Coordinator neu starten. Nach Deadline session_result.json und status.json müssen WINDOW_FINISHED, awake_request_released:true/coordinator_exiting:true melden; tatsächliche PID plus Erzeugungszeit des Coordinators und aller Sessionworker/-Supervisoren müssen beendet sein. Auch Launcheridentität prüfen. Keep-awake-API-Aufruf in Coordinatorfinally ist dokumentiert, Prozessende zusätzlich prüfen. Restprozesse nur eindeutig identifizierte Sessionprozesse innerhalb Autorisierung beenden, Logs erhalten. Keine fremden Prozesse beenden.

Bei nötigem Warten höchstens30–60Sekunden pro Toolcall und zwischenzeitlich knapp kommentieren. Ablauf der Zeit ist keine Zustimmung und keine Berechtigung zur Verlängerung. Nach tatsächlichem Ende final_verification/agent_checks/statusbericht sichern, dann bestehende Automation bc-forschung-fortschritt-und-trainings-pr-fen über automation_update mit unveränderten übrigen Feldern auf PAUSED setzen. Falls Appupdate blockiert, technische Einschränkung und lokalen abgeschlossenen Status klar protokollieren; keine manuellen TOML-Workarounds.

Minimale nächste Forschung außerhalb dieser Session: auf neuen Demos bei gleicher B_local-Identifikation **lokal physisch identifiziertes A versus bisher eingefrorenes A** testen, gleiche Antwortzweige und alte feste Fehlerhülle, Policyprüfzweige vom Fit getrennt. Die gespeicherten sechs A-Aktionszweige erlauben Identifikation ohne zusätzliche Aufgabenrollouts; neue Gegenprüfungsdemos/Quelle vorher fixieren, kein Retuning der gescheiterten Grenze. Das prüft die verbleibende Zustandsantwort statt erneuten unveränderten Modelltrainings. Erst nach Domain-/Fehler-/Kosten-/Aktionsregion-/Skalengates einen vorab budgetierten, gepaarten replizierten Methodenvergleich planen; nicht innerhalb der verbleibenden Session unautorisiert starten.
'''
with (S/'SESSION_CLOSEOUT.md').open('x',encoding='utf-8') as out:out.write(closeout)
event['closeout_protocol_sha256']=sha(S/'SESSION_CLOSEOUT.md')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
paragraph=f"**Elfter Check, Trigger14:39Berlin:** [Lossreferenz und Cacheaudit](method_reference_001/RESULT.md) abgeschlossen: konkrete reine7D-/A-/B_local-/w-/epsilon-Tensorfunktion implementiert, keine produktive Registrierung/Trainingsupdates. Numerische Vorprüfung und vier Float64-Parameterableitungen bestanden, NumPygegenprüfung12Frames×4Varianten. Features12/12 passend, B_cache8/12 nach privilegierter Physik; Aktionsregion{region}/72, Cachefälle48/48 darin. M0gewichtete48/72 versus M2 42/72, Marge aktiviert zusätzliche Lossfälle und ändert Stärke. Parameter/Checkpoint/Dataset unverändert; wissenschaftlich gescheiterte Fehlerhülle bleibt gescheitert. Worker/-Jobs beendet, Coordinator/Heartbeat ACTIVE bis Originaldeadline15:11:19. Letzter konkrete Auftrag [SESSION_CLOSEOUT.md](SESSION_CLOSEOUT.md): Gesamtevidenz und Prozess-/Wachhalteende verifizieren, erst nach Deadline pausieren. Kein weiterer Trainingslauf."
p=S/'PILOT_INTERPRETATION.md';txt=p.read_text(encoding='utf-8');marker='Diese Fortsetzung ist ein Arbeitsauftrag an den aktiven Agent-Trigger.';assert txt.count(marker)==1;p.write_text(txt.replace(marker,marker+'\n\n'+paragraph),encoding='utf-8')
p=ROOT/'FORSCHUNGSPLAN.md';txt=p.read_text(encoding='utf-8');marker='## 8. Aktueller Status und nächste fachliche Arbeit';assert txt.count(marker)==1
prefix='experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/'
p.write_text(txt.replace(marker,marker+'\n\n'+paragraph.replace('(method_reference_001/RESULT.md)','('+prefix+'method_reference_001/RESULT.md)').replace('(SESSION_CLOSEOUT.md)','('+prefix+'SESSION_CLOSEOUT.md)')),encoding='utf-8')
with (S.parent/'RESEARCH_STATUS.md').open('a',encoding='utf-8') as out:out.write('\n\n## Elfter Check: konkreter Lossentwurf, keine Trainingsfreigabe\n\n'+paragraph.replace('(method_reference_001/RESULT.md)','(supervised_6h_20261004_0904/method_reference_001/RESULT.md)').replace('(SESSION_CLOSEOUT.md)','(supervised_6h_20261004_0904/SESSION_CLOSEOUT.md)')+'\n')
print(json.dumps(dict(event=event,feature_maxima=featuremax,sensor_physical_feature_maxima=semanticmax,sensor_physical_action_max_difference=semantic_error,physical_action_reproduction_max_error=physical_error),indent=2))
