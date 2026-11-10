from pathlib import Path
p=Path('experiments/self_imitation/stack_five_curriculum_20261023/runner.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace('env.sim.forward();env.sim.step();env.sim.forward();positive=old.prefix_valid(env,n);assert positive', 'env.sim.forward()\n        for _ in range(250):env.sim.step()\n        env.sim.forward();positive=old.prefix_valid(env,n);assert positive')
s=s.replace('rows,earlier,steps,deadline):','rows,earlier,steps,deadline,smoke=False):')
s=s.replace("score=evaluate(folder/'latest.pth',count,list(range(310000+count*1000,310050+count*1000)),folder/'development',deadline)","score=0 if smoke else evaluate(folder/'latest.pth',count,list(range(310000+count*1000,310050+count*1000)),folder/'development',deadline)")
s=s.replace("write(OUT/'preflight.json',dict(state='PASSED'", "legacy=json.loads((prior.OUT/'dataset_manifest.json').read_text())['rows']\n    train(Path(json.loads((OUT/'protocol.json').read_text())['parents'][0]['path']),99,'technical_smoke',3,0,legacy,legacy,5,time.time()+120,smoke=True)\n    corrupted={k:v.copy() for k,v in a.items()};corrupted['a'][0,0]+=.1\n    try:audit_episode(corrupted,m,5)\n    except AssertionError:pass\n    else:raise AssertionError('Corruption audit failed to reject')\n    write(OUT/'preflight.json',dict(state='PASSED'")
p.write_text(s,encoding='utf-8')
