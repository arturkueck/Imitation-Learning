"""Numerical, prefix, calibration, resume and reference-path checks before launch."""
from pathlib import Path
import copy,json,time,sys
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
from preflight import settings
from model_prototype import ScenePerception as V2
from model_v3 import ScenePerception,context_arrays,tensor_context,predict
from learning import criterion
from data_v3 import PoseGenerator
from active_view.collision import ArmChecker,reference_world


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='preflight_002');parser.add_argument('--pilot',default='data_pilot_002');args=parser.parse_args()
    settings();out=HERE/args.name;out.mkdir(exist_ok=False);started=time.time()
    paths=sorted((HERE/args.pilot).glob('sample_*.npz'))
    if len(paths)<32:raise RuntimeError('Need 32 pilot samples')
    rows=[]
    for p in paths:
        with np.load(p) as z:rows.append({k:z[k] for k in z.files})
    data={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    old=V2().cuda().eval();new=ScenePerception().cuda().eval();new.load_state_dict(old.state_dict())
    b=tensor_context(context_arrays(data,[0,1],'M1'))
    with torch.inference_mode():
        a=old(b['images'].permute(0,1,4,2,3).float()/255,b['rays'],b['view_available']);c,_=predict(new,b)
        delta=max(float((a[k]-c[k]).abs().max()) for k in a)
    if delta>1e-6:raise RuntimeError('Three-view extension changed original forward')
    if sum(p.numel() for p in new.parameters())!=904112:raise RuntimeError('Parameter count changed')
    masked=tensor_context(context_arrays(data,[0,1],'M2',current=[1,1],history=[[1],[1]]))
    changed={k:v.clone() for k,v in masked.items()};changed['images'][:,3:]=255;changed['rays'][:,3:]=100
    with torch.inference_mode():
        a,_=predict(new,masked);c,_=predict(new,changed)
        if any(not torch.allclose(a[k],c[k],atol=1e-6,rtol=1e-6) for k in a):raise RuntimeError('Unavailable image leaked')
    try:context_arrays(data,[0],'M2',current=0,history=[[1]])
    except ValueError:pass
    else:raise RuntimeError('Future image leaked')
    del old,new
    benchmark={}
    parent=ROOT/'experiments/vision/visual_scene_v2_20261101/run_001/checkpoints/fixed_wrist_seed1_best.pth'
    for variant in ['M1','M2']:
        model=ScenePerception().cuda();model.load_state_dict(torch.load(parent,map_location='cuda',weights_only=False)['model'])
        opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)
        def step():
            model.train();opt.zero_grad(set_to_none=True);value=0.
            for at in range(0,32,4):
                arrays=context_arrays(data,np.arange(at,at+4),variant,epoch=1,training=True)
                batch=tensor_context(arrays);pred,av=predict(model,batch);loss,_,_=criterion(pred,batch,av)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
                (loss/8).backward();value+=float(loss.detach())/8
            torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);opt.step();return value
        initial=step()
        state=copy.deepcopy(dict(model=model.state_dict(),optimizer=opt.state_dict(),rng=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all()))
        expected=step();weights=copy.deepcopy(model.state_dict())
        model.load_state_dict(state['model']);opt.load_state_dict(state['optimizer']);torch.set_rng_state(state['rng']);torch.cuda.set_rng_state_all(state['cuda'])
        actual=step();difference=max(float((weights[k]-model.state_dict()[k]).abs().max()) for k in weights)
        if abs(expected-actual)>1e-7 or difference>1e-7:raise RuntimeError('Resume not exact')
        t=time.time();losses=[step() for _ in range(12)];torch.cuda.synchronize();duration=time.time()-t
        benchmark[variant]=dict(initial_loss=initial,final_loss=losses[-1],seconds_per_update=duration/12,
                                exact_resume=True,maximum_parameter_difference=difference)
        if not np.isfinite(losses).all():raise RuntimeError('Bad optimization')
        del model,opt
    # Recreate two families and independently check full native reference paths
    # against the cached conservative swept-envelope decisions.
    g=PoseGenerator();native_checks=0
    try:
        g.make_bank()
        for i in [0,3]:
            truth,selected=g.setup_family(9363001,i)
            g.d.qpos[g.qadr]=g.base_q;g.env.sim.forward()
            checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d))
            for j in selected:
                q=g.bank[j]['q']
                if not checker.edge(g.base_q,q):raise RuntimeError('Swept certificate disagrees with full checker')
                for alpha in np.linspace(0,1,17):
                    checker.set_q(g.base_q+(q-g.base_q)*alpha)
                    for contact in g.d.contact[:g.d.ncon]:
                        a=g.m.geom(int(contact.geom1)).name or '';b=g.m.geom(int(contact.geom2)).name or ''
                        ra=a.startswith(('robot0_','gripper0_'));rb=b.startswith(('robot0_','gripper0_'))
                        other=b if ra else a
                        if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:
                            raise RuntimeError('Native robot-world penetration')
                    native_checks+=1
    finally:g.close()
    report=dict(passed=True,parameters=904112,original_forward_max_difference=delta,
        unavailable_view_mask=True,prefix_only=True,benchmark=benchmark,native_motion_samples=native_checks,
        peak_gpu_gib=torch.cuda.max_memory_allocated()/2**30,elapsed_seconds=time.time()-started,
        scope='sim-reference collision checks, no hardware safety or active-view quality proof')
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
