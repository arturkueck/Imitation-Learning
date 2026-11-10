from pathlib import Path
p=Path('experiments/self_imitation/stack_five_curriculum_20261023/supervisor.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("plan=json.loads((OUT/'protocol.json').read_text());deadline=plan['deadline'];process=None", "plan=json.loads((OUT/'protocol.json').read_text());deadline=plan['deadline'];process=None\n    with (OUT/'supervisor_started.json').open('x') as lock:json.dump(dict(pid=os.getpid(),started=time.time()),lock)")
s=s.replace("ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);write(OUT/'supervisor_status.json',info)","info['wake_lock_released']=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000000));info['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());write(OUT/'supervisor_status.json',info)")
p.write_text(s,encoding='utf-8')
p=Path('experiments/self_imitation/stack_five_curriculum_20261023/runner.py');s=p.read_text();s=s.replace("paths=[Path(p['path']) for p in plan['parents']]", "for source,expected in json.loads((OUT/'source_hashes.json').read_text()).items():assert digest(source)==expected,source\n    paths=[Path(p['path']) for p in plan['parents']]")
p.write_text(s,encoding='utf-8')
import hashlib,json
out=p.parent
manifest=json.loads((out/'source_hashes.json').read_text())
for q in [p,out/'supervisor.py']:manifest[str(q.resolve())]=hashlib.sha256(q.read_bytes()).hexdigest()
(out/'source_hashes.json').write_text(json.dumps(manifest,indent=2))
