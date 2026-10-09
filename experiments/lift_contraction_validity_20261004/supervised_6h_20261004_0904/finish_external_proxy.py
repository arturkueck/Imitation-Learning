import json, hashlib, time, tomllib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import psutil

S=Path(__file__).resolve().parent; O=S/'external_proxy_001'; ROOT=S.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try: return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess: return False

session=read(S/'session.json'); status=read(S/'status.json'); pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())
assert auto['status']=='ACTIVE'
assert all(status['progress'][arm]['optimizer_updates']==2000 for arm in ['B0','B1'])
assert status['progress']['evaluation']['episodes_completed']==104
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    for line in (S/name).read_text(encoding='utf-8').splitlines():
        if line: json.loads(line)
processes={}
for p in [O,O/'preflight_001',O/'query_verification_001']:
    sup=read(p/'supervisor_result.json'); launch=read(p/'launch.json')
    supervisor=dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])
    assert not alive(sup['worker']) and not alive(supervisor)
    assert sup['worker_job_closed'] and sup['returncode']==0 and launch['deadline_unix']<=session['deadline_unix']
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_identity=supervisor,both_exited=True,
                           elapsed_seconds=sup['elapsed_seconds'],returncode=sup['returncode'],worker_job_closed=True)
r=read(O/'result.json'); a=read(O/'analysis_verification.json'); f=read(O/'filter_analysis.json')
q=read(O/'query_verification_001/result.json'); pref=read(O/'preflight_001/result.json'); sel=read(O/'selection.json')
assert a['raw_sha256']==f['raw_sha256']==q['raw_sha256']==sha(O/'result.json')
assert q['filter_analysis_sha256']==sha(O/'filter_analysis.json') and q['state']=='NATIVE_FILTER_QUERIES_INDEPENDENTLY_REPRODUCED'
assert a['source_hashes_verified'] and a['eligible_anchors']==8 and a['executed_branches']==336
assert r['policy_training_updates']==r['fit_updates']==0
assert f['masks']['M0']['true_accept']==8 and f['masks']['M0']['false_accept']==0
assert f['masks']['M2']['true_accept']==7 and f['masks']['M2']['false_accept']==0 and f['masks']['M2']['false_reject']==1
assert f['external_mask_development_gate_passed']
wrong=[x for x in f['rows'] if not x['masks']['M2'] and x['dynamic_domain_eligible']]
assert len(wrong)==1
now=time.time(); dt=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',
           automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',trigger_utc='2026-10-04T11:37:45.990Z',
           utc=dt.isoformat(),berlin=dt.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],
           optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,processes=processes,
           worker_state=r['state'],audit_state=a['state'],mask_state='LOCAL_DEVELOPMENT_GATE_PASSED_WITH_NO_ADVANTAGE_OVER_M0',
           native_query_reproduction_state=q['state'],executed_branches=336,planned_anchors=12,eligible_anchors=8,
           masks=f['masks'],new_policy_updates=0,new_fits=0,
           hashes={n:sha(O/n) for n in ['result.json','analysis_verification.json','filter_analysis.json','source_hashes.json','query_verification_001/result.json']},
           worker_elapsed_seconds=r['elapsed_seconds'],
           decision='External rule passes small predeclared development gate but loses one valid state versus perfect M0 on this fresh set; no demonstrated incremental benefit or general dynamic validity. All actual self contacts retained. No training or threshold sweep; freeze error-margin diagnosis and keep monitoring ACTIVE to original deadline.')

report=f'''# Externe Nähe: frische Gegenprüfung ohne Policytraining

Stand {event['berlin']}. Seed **4100411**, vier neue Train-Demos {', '.join(sel['selected_demos'])}; zwölf vorab festgelegte H_reset-Anker bei 10/50/85%, **336/336** Simulatorzweige. Ein eingefrorener B0-Endcheckpoint, null Policyupdates, null neue Fits. [Vorabprotokoll](PROTOCOL.md), [Auswahl/Dataset-/Checkpointhashes](selection.json), [Originaldaten](result.json), [physischer Audit](analysis_verification.json), [Maskenaudit](filter_analysis.json).

## Ergebnis der Masken

| Vor Antwortaktion verfügbare Regel | Akzeptiert / 12 | Richtig akzeptiert | Falsch akzeptiert | Falsch verworfen | Richtig verworfen |
|---|---:|---:|---:|---:|---:|
| M0: nominal kein Robotkontakt | 8 | 8 | 0 | 0 | 4 |
| M1: zusätzlich keine Robotnähe, alle Paare | 0 | 0 | 0 | 8 | 4 |
| M2: zusätzlich keine externe Robotnähe | 7 | 7 | 0 | 1 | 4 |

Technische Herstellung **12/12** korrekt; dynamische kontaktfreie Domain **8/12**. Alle vier späten Anker liegen wegen tatsächlicher Kontakte außerhalb der fixierten Domain. Alle tatsächlichen Robot-/Selbstkontakte vor/während/nach jedem Zweig bleiben im Label. Wissenschaftlicher Rohstatus **DOMAIN_GATE_FAILED**, unabhängig bestätigt; kein Retrygrund.

M2 erfüllt die vorab fixierte kleine Entwicklungsregel (null Fehlannahmen, mindestens vier richtig angenommene Anker). **Kein inkrementeller Vorteil gegenüber M0 auf diesem neuen Satz**: M0 klassifiziert hier alle zwölf richtig, M2 verwirft zusätzlich {wrong[0]['demo']} bei Frame {wrong[0]['t']} (50%), obwohl alle geprüften Antwortzweige kontaktfrei sind. Frühe M2-Abdeckung 4/4, mittlere 3/4, späte 0/4. M1 bleibt wegen interner Nähe ohne Abdeckung. Frühere M0-Gegenbeispiele bleiben gültig; der neue kleine Satz beweist auch für M0 keine allgemeine Gültigkeit. Keine nachträgliche Änderung von 15-mm-Query, Scope oder Label.

Die unterstützte Aussage ist technische Verfügbarkeit einer vor Loss berechenbaren externen Nähemaskierung unter kontrollierter Ersatzgeschichte. Die Daten etablieren weder eine bessere Domainvorhersage gegenüber M0 noch universelle kontaktfreie Folgezustände, Stabilität oder bessere trainierte BC-Robustheit. Native Näheliste ist keine bewiesene exakte Clearancegrenze. Margin-/Kontaktsemantik folgt dem tatsächlich verwendeten [MuJoCo 3.2.3](https://mujoco.readthedocs.io/en/3.2.3/XMLreference.html#body-geom-margin); das begründet die Implementierung, keine Garantie für diesen Projektfilter.

## Verifikation und Kosten

Die sieben nominalen Aktionsachsen, physischen Zustandsperturbationen und vollen Policyantworten werden weiterhin kontrolliert. Query auf separater Modellkopie/MjData mit je 0,015 m Margin/Gap, ohne Integration oder Änderung des Originalzustands; sämtliche physikalisch definierten Model-/Datafelder und vollständige Controller-/Hilfszustände geprüft. Die bereits dokumentierten konditional nicht berechneten nativen Insel-/Dual-Arbeitsarrays werden weiterhin separat ausgewiesen. Keine neue technische Reparatur in diesem Versuch.

Vorprüfung: sechs bekannte synthetische Boxcases plus ein alter Kontrollframe, {pref['elapsed_seconds']:.3f} s Worker / {processes['preflight_001']['elapsed_seconds']:.3f} s Supervisor; sechs originale synthetische Forwards, sieben Queryforwards und eine Recorded-Rekonstruktion, keine Integrations-/Antwortaktionen. Neue Primärdemos werden erst danach verwendet. Unabhängige frische Neuherstellung reproduziert alle zwölf nominalen Zustände, Kontaktlisten und M0/M1/M2 exakt; [separater Nachweis](query_verification_001/result.json), {q['elapsed_seconds']:.3f} s Worker / {processes['query_verification_001']['elapsed_seconds']:.3f} s Supervisor, zwölf Rekonstruktionen/Queryforwards, keine Policy-/Antwortaktionen oder Integration. Weitere Setupforwards sind nicht vollständig instrumentiert.

Primärworker **{r['elapsed_seconds']:.3f} s**, Supervisor **{processes['external_proxy_001']['elapsed_seconds']:.3f} s**. Zähler: 336 Resets, 336 Antwortaktionen, 8.400 Physiksteps, null Expertprefixaktionen, 288 IK-Iterationen, 84 Policycalls, zwölf explizite Queryforwards; weitere Setupforwards nicht vollständig instrumentiert. Kalibrier-/Filteraufwand zählt zu späteren Methodenkosten und darf nicht hinter Trainingszeit verschwinden. Sämtliche drei Worker und Supervisoren sind anhand PID plus Erzeugungszeit beendet, Windows-Jobs geschlossen. Sessioncoordinator und 30-Minuten-Heartbeat bleiben bis **15:11:19 Berlin** aktiv.

## Unveränderte Forschungsentscheidung

Kein Kontraktionstraining aus diesem Ergebnis. Priorität: Entscheidungsfehlermarge auf neuen Demos statt weiterer Kontaktfilterparameter. [Nächstes fixiertes Protokoll](../NEXT_ERROR_MARGIN.md). Der frühere Sensorpilot bleibt ein einzelner Seed mit kleinem Trade-off, ohne Robustheits-/Konvergenznachweis. Literatur, alte Taskgewinne und neue lokale Diagnosen bleiben getrennte Evidenz.

SHA-256: Rohdaten `{event['hashes']['result.json']}`; physischer Audit `{event['hashes']['analysis_verification.json']}`; Filteraudit `{event['hashes']['filter_analysis.json']}`; Querygegenprüfung `{event['hashes']['query_verification_001/result.json']}`. Alle effektiven Quellen vor Primärlaunch eingefroren in [source_hashes.json](source_hashes.json); Dataset und unveränderter Endcheckpoint separat in selection.json.
'''
with (O/'RESULT.md').open('x',encoding='utf-8') as out: out.write(report)

# Freeze an empirical vector-error envelope from OLD train data only. It is
# deliberately not a theorem or a bound selected from new outcomes.
calpath=S/'local_response_001/local_identification.json'; old=read(calpath)
assert len(old['conditional_policy_raw'])==48 and old['policy_training_updates']==0
errors=[x['models']['A_B7_local']['vector_error_m']/np.linalg.norm(x['delta_m']) for x in old['conditional_policy_raw']]
epsilon=float(max(errors)); assert epsilon>0 and np.isfinite(epsilon)
excluded=set(sel['excluded_prior_demos'])|set(sel['selected_demos'])
train=read(S/'attempts/attempt_002/dataset_manifest.json')['train_demos']
chosen=np.random.default_rng(4100412).choice(sorted(set(train)-excluded),4,replace=False).tolist()
nextspec=dict(seed=4100412,selected_demos=chosen,excluded_prior_demos=sorted(excluded),
              anchor_fractions=[.1,.5,.85],planned_anchors=12,planned_branches=336,history='H_reset',
              threshold=.99,empirical_normalized_vector_error_max=epsilon,calibration_cases=48,
              calibration_source=str(calpath.relative_to(S)),calibration_source_sha256=sha(calpath),
              calibration_raw_sha256=sha(S/'local_response_001/result.json'),
              fixed_response_calibration_sha256=sha(O/'calibration.json'),
              dataset_sha256=sel['dataset_sha256'],checkpoint_sha256=sel['checkpoint_sha256'],
              empirical_bound_is_not_general_guarantee=True,policy_updates=0,
              primary='Same frozen A and locally identified full B7: raw ratio versus raw ratio plus frozen empirical vector-error envelope; all dynamically eligible held Pfull cases.',
              secondary='Report fixed M0/M2 domain-mask coverage separately, no claimed M2 advantage; no threshold tuning.',
              development_gate=dict(empirical_bound_violations=0,false_safe=0,minimum_true_safe=1),
              fixed_session_deadline_unix=session['deadline_unix'])
with (S/'NEXT_ERROR_MARGIN.json').open('x',encoding='utf-8') as out: json.dump(nextspec,out,indent=2,allow_nan=False)
nextreport=f'''# Entscheidungsfehlermarge: nächster minimaler Mechanismustest

Vor neuen Outcomeproben am {event['berlin']} fixiert. Lokales B7 verbessert Vorhersagen, lässt aber eine falsche enge 0,99-Freigabe im alten local_response_001 zu. Der aktuelle externe Domainfilter liefert keinen Vorteil gegenüber M0 auf seinen neuen Demos; keine weiteren Filter-/Marginsweeps. Forschungsfrage: verhindert eine **aus älteren Trainproben fixierte empirische Vektorfehlermarge** solche falschen Freigaben auf neuen Demos, bei welcher Abdeckung und welchen Kosten?

1. Beim nächsten autorisierten Agentcheck Session/Prozesse/Deadline/ACTIVE prüfen und tatsächlichen Check protokollieren. Frischer `error_margin_001`, pro Job maximal20 Minuten und unverändert 15:11:19 Berlin. Quellen/effektive Konfiguration vor Primärlaunch einfrieren, technischer Preflight auf bereits bekannten Frames, keine neuen Trainingsupdates oder Checkpointauswahl.
2. [Vorab fixierte Werte/Hashes](NEXT_ERROR_MARGIN.json): Seed **4100412**, neue Train-Demos **{', '.join(chosen)}**, alle früheren Diagnose-/Audit-Demos ausgeschlossen, gleicher180/20-Split, je floor(10/50/85%×(L−1)), H_reset, zwölf Anker/336 Zweige. Eingefrorenes B0 und A; keine Expertlabels ändern.
3. Nominale14 ±0,1-Aktionszweige identifizieren je gültigem Anker B_local (7×3), tatsächliche geklippte Aktionsdifferenzen verwenden, Rang/Condition berichten. Identifikationszweige sind kein unabhängiger Gütenachweis. Die sechs physischen Pfull-Zweige mit jeweils ±5mm EEF sind davon getrennte Gegenprüfung; alle bisherigen Geometrie-/History-/Auxiliary-/Wiederholungs-/Kontaktgates einschließlich tatsächlicher Selbstkontakte bleiben unverändert. Rangversagen/Domainfehler nicht ersetzen oder lockern.
4. Primär gleicher A/localB7: p=δA+ΔaB_local, r_hat=||p||/||δ||. Alte48 gültige Pfull-Trainfälle local_response_001 liefern **epsilon_train=max ||observed−p||/||δ|| = {epsilon:.17g}**. Quellhash oben fixiert. Kein neuer Fit an Gegenprüfungs-Policyantworten, kein Sicherheitsfaktor-/Quantiltuning. Primäre neue Freigabe r_hat+epsilon_train<0,99 gegen ungesicherte r_hat<0,99; beobachtet ||δ_next||/||δ||<0,99. Die Dreiecksungleichung rechtfertigt eine obere Ratio **nur wenn die echte Fehlergrenze gilt**; endliches empirisches Maximum ist gerade keine allgemeine Grenze.
5. Gegenprüfung auf allen dynamisch gültigen neuen Pfull-Fällen, geplanten72 im Nenner: normalisierter Vektorfehler, tatsächliche Überschreitungen epsilon_train, falsche Freigaben, unnötige Verwerfungen, richtig freie Fälle/Abdeckung, abschnittsweise und vollständig. MaskenM0/M2 als festes sekundäres Coverage-Audit, nicht nachträglich primäres Subset wählen. Jeder vor Loss als gültig angenommene, dynamisch ungültige Anker separat als Domainfehlannahme zählen. Kleine Entwicklungsregel: **null Fehlergrenzenverletzungen, null falsche Freigaben und mindestens eine richtig freigegebene Prüfung**; selbst bestanden keine allgemeine Garantie und kein Trainingsgate. Bei Fehlschlag nicht epsilon aus neuen Ergebnissen vergrößern oder Seeds sweepen.
6. Unabhängig lokale Fits, gespeicherte physische Antworten/Ratio-/Vektorrechnung und Quellen/Hashes prüfen. Worker/Job/Supervisorende sowie Zeiten/Resets/Forwards/Physik/IK/Policy/Fitkosten protokollieren, RESULT und Hypothesenledger aktualisieren. Technische Ausfälle nachvollziehbar in frischen Pfaden reparieren; wissenschaftliche Negativergebnisse erhalten. Danach konkreten Losskandidaten und offene Trainingsgates dokumentieren, kein ungeplanter Methoden-Trainingslauf im laufenden Pilotbudget.

Die lokale Identifikation benötigt privilegierte Simulatorzustände,14 nominale Aktionen pro Frame und bekannten Controllerzustand. Antworten wurden um eine eingefrorene Policy kalibriert; spätere trainierte Aktionen können die lokale Region verlassen. Deshalb sind Cache-/Kosten-/Aktionsregion-/Domain-/Skalenkontrolle noch praktische Gates. Der eigentliche Methodenkandidat wäre L_BC+lambda×batch_mean(w×relu((||δA+ΔaB_local||/||δ||+epsilon)^2−rho^2)), mit expliziten Perturbationslabels und normalisiertem vollen Batchnenner. Das ist ein konkreter zu prüfender Vorschlag, kein bereits wirksam trainierter oder als neu bewiesener Algorithmus. Endliche empirische epsilon-Werte liefern keine Stable-BC-Garantie.
'''
with (S/'NEXT_ERROR_MARGIN.md').open('x',encoding='utf-8') as out: out.write(nextreport)
event['next_protocol_sha256']=sha(S/'NEXT_ERROR_MARGIN.md'); event['next_spec_sha256']=sha(S/'NEXT_ERROR_MARGIN.json')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as out: out.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
paragraph='**Neunter Check, Trigger 13:37 Berlin:** [Frische externe Nähegegenprüfung](external_proxy_001/RESULT.md), 336 Zweige, Herstellung12/12, Domain8/12. M2 erfüllt kleines vorab fixiertes Entwicklungsgate (7 richtig akzeptiert, null falsch akzeptiert), verwirft aber einen gültigen Fall zusätzlich; M0 ist auf diesem neuen Satz8/8 richtig akzeptiert und ebenfalls ohne Fehlannahme. Damit kein zusätzlicher Filtervorteil belegt; alte M0-Gegenbeispiele bleiben bestehen. Keine Threshold-/Scopeanpassung und kein Training. Alle nativen Masken/Zustände unabhängig12/12 reproduziert, alle Diagnoseworker/-jobs beendet. [NEXT_ERROR_MARGIN.md](NEXT_ERROR_MARGIN.md) fixiert einen neuen Entscheidungsfehlermargenvergleich auf vier weiteren Demos; empirische Marge ausschließlich aus alten Trainproben, kein allgemeiner Sicherheitsbeweis. Sessioncoordinator/Heartbeat ACTIVE bis unveränderte Deadline15:11:19 Berlin. Ältere konkrete Aufträge unten sind erledigte Historie.'
p=S/'PILOT_INTERPRETATION.md'; text=p.read_text(encoding='utf-8'); marker='Diese Fortsetzung ist ein Arbeitsauftrag an den aktiven Agent-Trigger.'
assert text.count(marker)==1; p.write_text(text.replace(marker,marker+'\n\n'+paragraph),encoding='utf-8')
p=ROOT/'FORSCHUNGSPLAN.md'; text=p.read_text(encoding='utf-8'); marker='## 8. Aktueller Status und nächste fachliche Arbeit'
assert text.count(marker)==1
rootpara=paragraph.replace('(external_proxy_001/RESULT.md)','(experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/external_proxy_001/RESULT.md)').replace('(NEXT_ERROR_MARGIN.md)','(experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/NEXT_ERROR_MARGIN.md)')
p.write_text(text.replace(marker,marker+'\n\n'+rootpara),encoding='utf-8')
p=S.parent/'RESEARCH_STATUS.md'
with p.open('a',encoding='utf-8') as out:
    out.write('\n\n## Neunter Check: externer Proxy ohne belegten Vorteil\n\n'+paragraph.replace('(external_proxy_001/RESULT.md)','(supervised_6h_20261004_0904/external_proxy_001/RESULT.md)').replace('(NEXT_ERROR_MARGIN.md)','(supervised_6h_20261004_0904/NEXT_ERROR_MARGIN.md)')+'\n\nPriorität1: Unsicherheit der engen Ratioentscheidung (lokalesB7 vorher56,12% besser, aber eine falsche Freigabe). Priorität2: praktische lokale Antwort/Cache und Aktionsregion bei veränderter Policy. Priorität3: Gradientenskala und erst danach replizierter Task-/Robustheitsvergleich. Externe Nähe ist verfügbar, aber gegenüber M0 hier ohne Nutzen und mit geringer Abdeckung; weitere Nähetunings haben derzeit keine Priorität. Unveränderte Hauptaussage: keine robuste neue BC-Algorithmusverbesserung etabliert.\n')
print(json.dumps(dict(event=event,next_spec=nextspec,false_rejected=wrong[0]['demo']),indent=2))
