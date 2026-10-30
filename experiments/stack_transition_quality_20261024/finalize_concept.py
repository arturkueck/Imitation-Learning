from pathlib import Path
import json,hashlib,re,subprocess,sys,datetime
out=Path('experiments/stack_transition_quality_20261024').resolve()
p=out/'IMPLEMENTATION_VALIDATION.md';s=p.read_text(encoding='utf-8').replace('Historische Experimente wurden nicht verändert.','Historische Rohdaten, Checkpoints und Produktionsskripte wurden nicht verändert. Der Hauptagent hat historische Berichte separat um die dokumentierte Messkorrektur ergänzt.')
s+='\n\n## Abschließende Integration durch den Hauptagenten\n\nDie17Tests wurden nach dem letzten Gewichtvalidierungsfix unabhängig erneut ausgeführt(root_unit_tests.log). training_plan.json und TRAINING_RUN_PLAN.md verwenden dieselbe tatsächlich implementierte Scoreversion(.50Erhaltkonstante/.25Ruhe/.25Zentrierung). Die alte fünfteilige Darstellung ist ein späterer Vorschlag, kein vorgetäuschter aktueller Score.\n\nAUDIT_SIGNOFF.md bestätigt Daten-/Lernkern und Produktionssperre unabhängig. Für vollständige vorbereitete Replays fehlen ausdrücklich Sequencer.pair und interner Roboter-/OSC-Controllerzustand. Die bestandene Positions-/Kontaktrestauration ist deshalb keine Behauptung identischer nächster Controlleraktionen. Weitere gültige Native-Daten, Onlineevaluation/Devselektion und Produktionsaufsicht bleiben offen.\n'
p.write_text(s,encoding='utf-8')
p=out/'TRAINING_RUN_PLAN.md';s=p.read_text(encoding='utf-8').replace('erste Aktion und nächster Zustand müssen im technischen Replay identisch rekonstruierbar sein.','erste Aktion und nächster Zustand müssen im technischen Replay identisch rekonstruierbar sein. Der aktuelle Collector speichert noch nicht Sequencer.pair und sämtliche internen Roboter-/OSC-Controllerzustände; seine bestandene physische Zustandsrekonstruktion allein erfüllt diese Replayabnahme daher noch nicht.');p.write_text(s,encoding='utf-8')
plan=json.loads((out/'training_plan.json').read_text());assert not plan['production_enabled']
assert sum(plan['score']['components'].values())==1
assert len(plan['parents'])==3 and plan['arms']==['B0','B']
for q in plan['parents']:assert hashlib.sha256(Path(q['path']).read_bytes()).hexdigest()==q['sha256']
res=subprocess.run([sys.executable,str(out/'transition_pilot.py'),'--train','--plan',str(out/'training_plan.json')],capture_output=True,text=True,timeout=20)
assert res.returncode!=0 and 'BLOCKED' in res.stderr+res.stdout
for doc in ['README.md','TRAINING_RUN_PLAN.md','IMPLEMENTATION_VALIDATION.md','AUDIT_SIGNOFF.md']:
 for link in re.findall(r'\]\(([^)]+)\)',(out/doc).read_text(encoding='utf-8')):
  if not link.startswith(('http:','https:')):assert (out/link).exists(),(doc,link)
artifact_names=['README.md','TRAINING_RUN_PLAN.md','training_plan.json','transition_pilot.py','native_collector.py','enrich_grasp.py','test_transition_pilot.py','AUDIT_FINDINGS.md','AUDIT_SIGNOFF.md','IMPLEMENTATION_VALIDATION.md']
check=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CONCEPT_AND_TECHNICAL_CORE_VALIDATED_NOT_PRODUCTION_READY',agents=['transition_concept_audit','transition_implementation'],root_independent_unit_tests=17,unit_tests_passed=True,production_train_flag_blocked_verified=True,production_enabled=False,long_training_started=False,native_smoke=json.loads((out/'native_collector_smoke_v4/validation.json').read_text()),paid_smoke_steps_per_arm=3,smoke_data='superseded proxy, technical loss/serialization test only; not scientific efficacy',historical_action_audit_episodes=240,strict_historical_accepted_sections=0,outstanding=plan['blocked_until']+['Sequencer.pair and complete robot/OSC internal state for identical prepared replay'],artifact_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in artifact_names})
(out/'FINAL_VALIDATION.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in check.items() if k in ['status','root_independent_unit_tests','unit_tests_passed','production_train_flag_blocked_verified','long_training_started']}))
