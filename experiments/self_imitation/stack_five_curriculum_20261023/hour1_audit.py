from pathlib import Path
import json,numpy as np,hashlib,datetime
out=Path('experiments/self_imitation/stack_five_curriculum_20261023').resolve()
source=json.loads((out/'source_hashes.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(8388608),b''):h.update(chunk)
 return h.hexdigest()
assert all(sha(p)==v for p,v in source.items())
d=json.loads((out/'datasets/curriculum_n3_cycle0/manifest.json').read_text());rows=d['rows'];assert d['complete'] and len(rows)==120
counts={};frames={}
for row in rows:
 with np.load(row['path']) as a:
  assert all(np.isfinite(a[k]).all() for k in a.files)
  assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
  e=9;rec=np.c_[(a['pre_obs'][:,e:e+3]-a['anchor'])/.1,a['pre_obs'][:,e+3:e+7],a['pre_obs'][:,e+7:e+9]/.04,np.minimum(a['phase_steps'],100)/20]
  assert np.allclose(rec,a['x'],rtol=1e-6,atol=1e-6)
  run=maximum=0
  for v in a['valid']:run=run+1 if v else 0;maximum=max(maximum,run)
  assert (maximum>=50)==row['success']
  assert not a['a'][:,3:6].any()
  key=row['split'];counts[key]=counts.get(key,0)+int(row['success']);frames[key]=frames.get(key,0)+(len(a['x']) if row['success'] else 0)
assert not {r['initial_sha256'] for r in rows if r['split']=='train'} & {r['initial_sha256'] for r in rows if r['split']=='valid'}
assert [r['seed'] for r in rows]==list(range(215000,215120))
audit=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),episodes=120,successes=counts,successful_frames=frames,all_finite=True,pre_action_alignment=True,split_disjoint=True,source_hashes_verified=True)
(out/'dataset_audit_n3.json').write_text(json.dumps(audit,indent=2))
(out/'DATASET_REPORT.md').write_text(f'''# Datensatzpruefung — Zwischenstand

Dreier-Sammlung vollstaendig:120 vorab getrennte Versuche, davon100 Training und20 Validierung. Erfolgreich:52/100 Training,10/20 Validierung. Nur vollstaendige stabile erfolgreiche Episoden werden als Actorziele benutzt; alle48+10 Fehlschlaege bleiben archiviert. Akzeptanzbias: Die erfolgreichen Starts sind keine repraesentative ungefilterte Zustandsverteilung.

Akzeptierte Frames: Training{frames['train']}, Validierung{frames['valid']}. Alle120 Dateien auf endliche Werte, zeitliche Verkettung Post-/Pre-action, Rekonstruktion der10 Inputs, Nullrotationen und50 zusammenhaengende stabile Frames geprueft. Train-/Valid-Anfangszustaende disjunkt; Seeds215000–215099/215100–215119 vorab getrennt. Vollstaendige Teacher-Aktionsreproduktion wurde bereits im Collector pro Episode geprueft.

Eingefrorene Quellen-/Datenarray-/Parentmanifest-Hashes unveraendert. Original-HDF5-Hash wird am Sessionende erneut geprueft. Sieben BC-Phasen, Completionlabels ausschliesslich aus Originaldaten. Neue Dreierdaten sind eigene erfolgreiche Modellaktionen, keine neuen Skriptexperten-Demos.

Vierer-Sammlung laeuft. Dieser Zwischenbericht behauptet keine abgeschlossene Vierer-/Fuenferdatenpruefung. Endgueltige Datenherkunft, Teacheranteile und weitere Stufen werden nach Abschluss ergaenzt.
''',encoding='utf-8')
state=json.loads((out/'status.json').read_text())
check=dict(utc=audit['utc'],phase=state,processes=dict(supervisor=33904,worker=13720,alive_verified_outside_sandbox=True),updates={f'seed{i}':30000 for i in [1,2,3]},finding='Three-cube stage complete with finite losses. Dev 37/50,33/50,28/50 vs parent34/50,31/50,27/50. Seed1 confirmed31/50; only seed1 passed ascent gate. Three-cube dataset120 episodes independently audited. Four-cube collection running.',decision='Continue existing coordinator unchanged; no duplicate training; next agent check hourly.')
with (out/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(check)+'\n')
print(json.dumps(dict(audit=audit,state=state)))
