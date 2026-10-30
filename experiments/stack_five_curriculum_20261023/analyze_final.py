from pathlib import Path
import json,hashlib,datetime,collections,math,shutil
import numpy as np,torch
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
plan=read(OUT/'protocol.json');frozen=read(OUT/'final_test/selection.json');sources=read(OUT/'source_hashes.json')
assert all(sha(p)==v for p,v in sources.items())
original=ROOT/'experiments/additional_tasks/stack_two/data/image_demonstrations.hdf5';assert sha(original)==plan['original_sha256']
for name,v in frozen.items():assert sha(v['path'])==v['sha256'] and sha(v['source'])==v['sha256']
final={};paired={};cost=collections.defaultdict(lambda:dict(episodes=0,steps=0));datasets={};training={};traces=[]
for p in OUT.rglob('result.json'):
 d=read(p);category='final_test' if 'final_test' in p.parts else 'development_and_gates';cost[category]['episodes']+=len(d['rows']);cost[category]['steps']+=sum(r['frames'] for r in d['rows'])
 if category=='final_test':
  assert d['complete'];n=int(p.parent.name[-1]);expected=100 if n==5 else 50
  assert d['attempts']==expected and [r['seed'] for r in d['rows']]==list(range(360000+n*1000,360000+n*1000+expected))
  assert d['successes']==sum(r['success'] for r in d['rows']);final[p.parent.name]=d
assert len(final)==24
for seed in [1,2,3]:
 a=final[f'curriculum_seed{seed}_n5']['rows'];b=final[f'direct_seed{seed}_n5']['rows'];assert all(x['seed']==y['seed'] and x['initial_sha256']==y['initial_sha256'] for x,y in zip(a,b))
 paired[str(seed)]=dict(curriculum_only=sum(x['success'] and not y['success'] for x,y in zip(a,b)),direct_only=sum(y['success'] and not x['success'] for x,y in zip(a,b)))
for p in (OUT/'datasets').glob('*/manifest.json'):
 d=read(p);rows=d['rows'];assert d['complete'] and len(rows)==120;summary=dict(episodes=120,successes={},frames={},teachers={})
 for r in rows:
  k=r['split'];summary['successes'][k]=summary['successes'].get(k,0)+int(r['success']);summary['frames'][k]=summary['frames'].get(k,0)+(r['frames'] if r['success'] else 0)
  t=Path(r['teacher']).parent.name;key=f'{t}/{k}';v=summary['teachers'].setdefault(key,dict(attempts=0,successes=0));v['attempts']+=1;v['successes']+=int(r['success'])
  assert sha(r['teacher'])==r['teacher_sha256']
  cost['collection']['episodes']+=1;cost['collection']['steps']+=r['frames']
 assert not {r['initial_sha256'] for r in rows if r['split']=='train'} & {r['initial_sha256'] for r in rows if r['split']=='valid'}
 datasets[p.parent.name]=summary
for p in (OUT/'training').glob('curriculum*'):
 cfg=read(p/'config.json');ck=torch.load(p/'latest.pth',map_location='cpu',weights_only=False);best=torch.load(p/'best.pth',map_location='cpu',weights_only=False);parent=torch.load(cfg['parent'],map_location='cpu',weights_only=False)
 assert sha(cfg['parent'])==cfg['parent_sha256'];assert ck['update']==30000==best['update']
 assert all(torch.equal(ck['model'][k],best['model'][k]) for k in ck['model'])
 assert all(torch.isfinite(t).all() for t in ck['model'].values())
 delta=math.sqrt(sum(float((v-parent['model'][k]).double().square().sum()) for k,v in ck['model'].items()));assert delta>0
 optsteps=[float(v['step']) for v in ck['optimizer']['state'].values()];assert max(optsteps)==30000
 curve=read(p/'learning_curve.json');assert all(np.isfinite([r['actor_loss'],r['completion_loss']]).all() for r in curve)
 training[p.name]=dict(updates=30000,parameter_change_l2=delta,optimizer_step_range=[min(optsteps),max(optsteps)],curve=curve)
for p in (OUT/'final_test').glob('*_n5/*.npz'):
 with np.load(p) as a:
  drops=[]
  for j in np.flatnonzero(a['controller_event']==2):
   lower=int(a['stage'][j])+1;nextrows=a['prefix_valid'][j+1:min(j+41,len(a['p'])),lower-2]
   drops.append(dict(prefix=lower,within40_steps_validity_lost=bool(len(nextrows) and not nextrows.all())))
  traces.append(dict(name=p.parent.name,seed=int(p.stem),success=bool(np.all(a['valid'][-50:])) if len(a['valid'])>=50 else False,transition_diagnostics=drops))
summary=dict(final={k:dict(successes=v['successes'],attempts=v['attempts']) for k,v in final.items()},paired=paired,cost=dict(cost),datasets=datasets,training=training,trace_diagnostics=traces,hashes_verified=True,original_sha256=sha(original),completed_utc=read(OUT/'supervisor_status.json')['finished_utc'],elapsed_hours=(datetime.datetime.fromisoformat(read(OUT/'supervisor_status.json')['finished_utc'].replace('Z','+00:00')).timestamp()-plan['start'])/3600)
(OUT/'final_analysis.json').write_text(json.dumps(summary,indent=2))
if not (OUT/'RESULTS_AUTOMATIC.md').exists():shutil.copy2(OUT/'RESULTS.md',OUT/'RESULTS_AUTOMATIC.md')
print(json.dumps(dict(final=summary['final'],cost=summary['cost'],datasets=datasets,elapsed_hours=summary['elapsed_hours'],training_changes={k:v['parameter_change_l2'] for k,v in training.items()},traces=traces)))
