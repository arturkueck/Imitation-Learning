from pathlib import Path
import json,datetime
out=Path('experiments/stack_five_curriculum_20261023').resolve();metrics={}
for arm in ['curriculum','direct']:
 for seed in [1,2,3]:
  name=f'{arm}_seed{seed}_n5';d=json.loads((out/'final_test'/name/'result.json').read_text());assert d['complete'] and d['attempts']==100;rr=d['rows']
  metrics[name]=dict(successes=d['successes'],attempts=100,ever_stable_prefix10=[sum(r['prefix_max_run'][j]>=10 for r in rr) for j in range(4)],failed_last_stage={str(k):sum(not r['success'] and r['last_stage']==k for r in rr) for k in range(1,5)},simulator_steps=sum(r['frames'] for r in rr))
for seed in [1,2,3]:
 ca=json.loads((out/'final_test'/f'curriculum_seed{seed}_n5/result.json').read_text())['rows'];da=json.loads((out/'final_test'/f'direct_seed{seed}_n5/result.json').read_text())['rows']
 assert all(a['seed']==b['seed'] and a['initial_sha256']==b['initial_sha256'] for a,b in zip(ca,da))
 metrics[f'paired_seed{seed}']=dict(curriculum_only=sum(a['success'] and not b['success'] for a,b in zip(ca,da)),direct_only=sum(b['success'] and not a['success'] for a,b in zip(ca,da)))
(out/'five_cube_endtest_analysis.json').write_text(json.dumps(metrics,indent=2))
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state=json.loads((out/'status.json').read_text()),processes=dict(supervisor=33904,worker=13720,alive_verified=True),updates=dict(curriculum_total=180000,direct=0),finding='All six reserved five-cube tests complete; same initial-state hashes paired between arms verified. Lower-height regression tests still running normally. No model changes or additional testing.',decision='Preserve frozen models, await coordinator completion and final report at next hourly check. No routine notification.',five_cube_results=metrics)
with (out/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(metrics))
