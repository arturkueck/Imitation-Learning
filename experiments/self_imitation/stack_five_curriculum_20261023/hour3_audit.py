from pathlib import Path
import json,numpy as np,datetime,hashlib
out=Path('experiments/self_imitation/stack_five_curriculum_20261023').resolve();p=out/'datasets/direct_n5_cycle0/manifest.json';d=json.loads(p.read_text());rows=d['rows'];assert d['complete'] and len(rows)==120
counts={};frames={};steps=0
for r in rows:
 with np.load(r['path']) as a:
  assert all(np.isfinite(a[k]).all() for k in a.files)
  assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
  rec=np.c_[(a['pre_obs'][:,15:18]-a['anchor'])/.1,a['pre_obs'][:,18:22],a['pre_obs'][:,22:24]/.04,np.minimum(a['phase_steps'],100)/20]
  assert np.allclose(rec,a['x'],rtol=1e-6,atol=1e-6)
  run=maximum=0
  for v in a['valid']:run=run+1 if v else 0;maximum=max(maximum,run)
  assert (maximum>=50)==r['success'];assert not a['a'][:,3:6].any()
  counts[r['split']]=counts.get(r['split'],0)+int(r['success']);frames[r['split']]=frames.get(r['split'],0)+(len(a['x']) if r['success'] else 0);steps+=len(a['x'])
assert not {r['initial_sha256'] for r in rows if r['split']=='train'} & {r['initial_sha256'] for r in rows if r['split']=='valid'}
assert [r['seed'] for r in rows]==list(range(275000,275120))
audit=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),episodes=120,successes=counts,successful_frames=frames,simulator_steps=steps,pre_action_alignment=True,all_finite=True,split_disjoint=True)
(out/'dataset_audit_direct_n5.json').write_text(json.dumps(audit,indent=2))
sel=json.loads((out/'final_test/selection.json').read_text())
for name,v in sel.items():assert hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256']
for i in [1,2,3]:
 assert 'curriculum_n3' in sel[f'curriculum_seed{i}']['source']
 assert sel[f'direct_seed{i}']['sha256']==json.loads((out/'protocol.json').read_text())['parents'][i-1]['sha256']
with (out/'DATASET_REPORT.md').open('a',encoding='utf-8') as f:f.write(f"\n\n## Direkter Fuenferpfad und eingefrorene Auswahl\n\n120 feste Versuche auf Starts275000–275119: Training{counts['train']}/100 und Validierung{counts['valid']}/20 vollstaendig stabil erfolgreich. Akzeptierte Frames:{frames}; insgesamt{steps} Sammelschritte. Alle120 Episoden erneut auf endliche Werte, genaue Pre-action-Ausrichtung, Splittrennung und vollstaendige50-Frame-Stabilitaet geprueft. Mindestzahl nicht erreicht; kein direkter Fuenfer-Optimizerlauf gestartet.\n\nCurriculum-Fuenferstufe wird wegen Vierer-Gate15/50,13/50,12/50 nicht betreten. Endauswahl vor reservierten Tests eingefroren und alle6 Hashes geprueft: Curriculum nutzt Dreier-Checkpoints, Direktarm unveraenderte Parentmodelle. Viererkandidaten blieben verworfen. Keine Modellwahl anhand laufender Endtests.\n")
check=dict(utc=audit['utc'],processes=dict(supervisor=33904,worker=13720,alive_verified=True),state=json.loads((out/'status.json').read_text()),updates=dict(curriculum_each_seed=60000,curriculum_total=180000,direct=0,five_cube_curriculum=0),finding=dict(direct_dataset=audit,frozen_model_hashes_verified=True,four_gate=[15,13,12],endtests_in_progress=True),decision='Training ended by scientific gates, not technical failure. Preserve decisions and frozen models; let existing worker finish reserved tests. No additional training or threshold change; next check hourly.')
with (out/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(check)+'\n')
print(json.dumps(audit))
