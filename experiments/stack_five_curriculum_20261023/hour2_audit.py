from pathlib import Path
import json,numpy as np,hashlib,datetime
out=Path('experiments/stack_five_curriculum_20261023').resolve()
manifest=json.loads((out/'datasets/curriculum_n4_cycle0/manifest.json').read_text());rows=manifest['rows'];assert manifest['complete'] and len(rows)==120
counts={};frames={};teacher=set();phase_hist=np.zeros(7,dtype=int)
for r in rows:
 with np.load(r['path']) as a:
  assert all(np.isfinite(a[k]).all() for k in a.files)
  assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
  rec=np.c_[(a['pre_obs'][:,12:15]-a['anchor'])/.1,a['pre_obs'][:,15:19],a['pre_obs'][:,19:21]/.04,np.minimum(a['phase_steps'],100)/20]
  assert np.allclose(rec,a['x'],rtol=1e-6,atol=1e-6)
  run=maximum=0
  for v in a['valid']:run=run+1 if v else 0;maximum=max(maximum,run)
  assert (maximum>=50)==r['success'];assert not a['a'][:,3:6].any()
  split=r['split'];counts[split]=counts.get(split,0)+int(r['success']);frames[split]=frames.get(split,0)+(len(a['x']) if r['success'] else 0)
  if r['success'] and split=='train':phase_hist+=np.bincount(a['p'],minlength=7)
 teacher.add(r['teacher'])
assert not {r['initial_sha256'] for r in rows if r['split']=='train'} & {r['initial_sha256'] for r in rows if r['split']=='valid'}
assert [r['seed'] for r in rows]==list(range(220000,220120))
results={}
for pat in ['gates/parent_n4*/result.json','training/curriculum_n4*/development/result.json','gates/post4*/result.json']:
 for p in out.glob(pat):
  d=json.loads(p.read_text());results[str(p.relative_to(out))]={k:d[k] for k in ['complete','successes','attempts']}
curves={}
for p in (out/'training').glob('curriculum_n4*/learning_curve.json'):
 curve=json.loads(p.read_text());assert all(np.isfinite([r['actor_loss'],r['completion_loss']]).all() for r in curve);curves[p.parent.name]=[{k:r[k] for k in ['update','actor_loss','completion_loss']} for r in curve]
audit=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),episodes=120,successes=counts,successful_frames=frames,teachers=sorted(teacher),successful_train_phase_frames=phase_hist.tolist(),pre_action_alignment=True,all_finite=True,split_disjoint=True)
(out/'dataset_audit_n4.json').write_text(json.dumps(audit,indent=2));(out/'hour2_analysis.json').write_text(json.dumps(dict(audit=audit,results=results,curves=curves),indent=2))
with (out/'DATASET_REPORT.md').open('a',encoding='utf-8') as f:f.write(f"\n\n## Vierer-Sammlung abgeschlossen\n\n120 feste Versuche (100 Training/20 Validierung), davon{counts['train']} erfolgreiche Trainingsepisoden und{counts['valid']} erfolgreiche Validierungsepisoden. Akzeptierte Frames:{frames}. Alle120 Dateien erneut auf endliche Werte, genaue zeitliche Verkettung, Inputrekonstruktion,50 stabile Frames und Splittrennung geprueft. Erfolgreiche Trainingsframes pro Phase:{phase_hist.tolist()}. Teacher ausschliesslich das auf Dreiern bestaetigte Seed1-Modell; kein anderer Seed wird deshalb als Gate-bestanden gewertet. Aktionsreproduktion erfolgte im Collector.\n")
check=dict(utc=audit['utc'],processes=dict(supervisor=33904,worker=13720,alive_verified=True),state=json.loads((out/'status.json').read_text()),updates={f'curriculum_seed{i}':dict(n3=30000,n4=30000,total=60000) for i in [1,2,3]},finding=dict(dataset=audit,development=results,finite_curves=True),decision='Continue existing coordinator and strict gates unchanged. Four-cube completed checkpoints have only13/50,13/50,10/50 development successes; no confirmed ascent to5 so far. Scientific weakness is not a technical failure; do not retrain or alter threshold.')
with (out/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(check)+'\n')
print(json.dumps(dict(audit=audit,results=results)))
