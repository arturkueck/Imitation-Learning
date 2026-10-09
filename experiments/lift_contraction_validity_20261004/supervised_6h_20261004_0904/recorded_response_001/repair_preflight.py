from pathlib import Path
import shutil,json,time,hashlib
O=Path(__file__).resolve().parent;S=O.parent;old=O/'preflight_001';new=O/'preflight_002'
new.mkdir();shutil.copy2(old/'supervise.py',new/'supervise.py')
source=(old/'run.py').read_text(encoding='utf-8')
helper='''def history_changes(a,b,path=""):
    if isinstance(a,dict) and isinstance(b,dict):
        rows=[]
        for k in sorted(set(a)|set(b)):rows += history_changes(a.get(k),b.get(k),path+"/"+k)
        return rows
    if a is None or b is None:
        return [] if a is b else [dict(field=path,change="presence",prefix_value=a,reset_value=b)]
    if isinstance(a,(str,bool)) or isinstance(b,(str,bool)):
        return [] if a==b else [dict(field=path,change="categorical",prefix_value=a,reset_value=b)]
    x,y=np.asarray(a),np.asarray(b)
    if x.shape!=y.shape:return [dict(field=path,change="shape",prefix_shape=x.shape,reset_shape=y.shape)]
    error=float(np.max(np.abs(x-y),initial=0))
    return [dict(field=path,change="numeric",max_absolute_difference=error)] if error else []
'''
source=source.replace('start=time.monotonic();',helper+'\nstart=time.monotonic();')
source=source.replace("h.difference(snapshots[0]['controllers'],snapshots[1]['controllers'])","history_changes(snapshots[0]['controllers'],snapshots[1]['controllers'])")
with (new/'run.py').open('x',encoding='utf-8') as f:f.write(source)
event=dict(actor='agent',event='recorded_response_preflight_repair',unix=time.time(),
           reason='Preflight geometry/history/canonical-state assertions passed, but summary subtraction could not compare intentionally numeric-vs-None torque fields. Preserve first failed preflight. Fresh preflight_002 reports categorical presence/shape and numeric changes; no state/control gate relaxed or response probe repeated.',
           prior='recorded_response_001/preflight_001',fresh='recorded_response_001/preflight_002',
           repair_source_sha256=hashlib.sha256((new/'run.py').read_bytes()).hexdigest(),policy_updates=0,response_probe_steps=0,
           coordinator_training_repair_not_requested=True)
with (S/'repairs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
print('Fresh preflight built; original failed summary/source/logs retained.')
