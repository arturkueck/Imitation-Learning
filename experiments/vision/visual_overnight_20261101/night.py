"""Time-bounded paired RGB localization training; no robot actions or LEGO assembly."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import argparse, ctypes, hashlib, json, subprocess, sys, time, traceback
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]
import site
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))


def stamp(): return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2),encoding='utf-8')
    for attempt in range(10):
        try: tmp.replace(path);return
        except PermissionError:
            if attempt==9:raise
            time.sleep(.05*(attempt+1))


def atomic_checkpoint(path, value, torch):
    tmp=path.with_suffix('.tmp');torch.save(value,tmp)
    for attempt in range(10):
        try:tmp.replace(path);return
        except PermissionError:
            if attempt==9:raise
            time.sleep(.05*(attempt+1))


def independence():
    from ctypes import wintypes
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=wintypes.HANDLE
    k.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
    k.IsProcessInJob.restype=wintypes.BOOL
    flag=wintypes.BOOL();ok=k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(flag))
    return dict(pid=os.getpid(),query_ok=bool(ok),in_job=bool(flag.value),time=stamp())


def worker(run, smoke=False):
    import numpy as np
    sys.path.insert(0,str(ROOT/'experiments/vision/visual_cube_transfer_20261031'))
    from pilot import Model,aim,metrics
    import robosuite, torch
    from PIL import Image
    torch.set_num_threads(4);torch.manual_seed(91101);np.random.seed(91101)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no CPU fallback')
    cfg=json.loads((run/'config.json').read_text());deadline=cfg['deadline_unix']
    stop_train=deadline-(10 if smoke else 600)
    status=dict(stage='initializing',pid=os.getpid(),time=stamp(),deadline_unix=deadline)
    def update(**extra):
        status.update(extra);status['time']=stamp();status['heartbeat_unix']=time.time()
        save(run/'status.json',status)
    update()
    envkw=json.loads((ROOT/'experiments/baselines/additional_tasks/stack_two/task_info.json').read_text())['environment']['env_kwargs']
    envkw.update(use_camera_obs=False,use_object_obs=False,hard_reset=False,
                 has_renderer=False,has_offscreen_renderer=True,camera_heights=128,camera_widths=128)
    env=robosuite.make('StackTwo',**envkw)
    try:
        env.reset()
        aim(env,'agentview',np.array([.8,-.7,1.5]),np.array([0.,0.,.82]))
        aim(env,'frontview',np.array([.8,.7,1.5]),np.array([0.,0.,.82]))
        cameras=['agentview','frontview','robot0_eye_in_hand']
        save(run/'runtime.json',dict(torch=torch.__version__,numpy=np.__version__,
             gpu=torch.cuda.get_device_name(),parameters=sum(p.numel() for p in Model().parameters()),
             camera_names=cameras,arm_qpos=env.sim.data.qpos.tolist(),
             cameras={c:dict(position=env.sim.model.cam_pos[env.sim.model.camera_name2id(c)].tolist(),
                            quaternion=env.sim.model.cam_quat[env.sim.model.camera_name2id(c)].tolist()) for c in cameras}))
        geomids=[[env.sim.model.geom_name2id(g) for g in cube.contact_geoms+cube.visual_geoms] for cube in env.cubes]
        def collect(split, seed, count, cuboid=False):
            rng=np.random.default_rng(seed);images=[];labels=[];sizes=[]
            for i in range(count):
                if time.time()>deadline:raise TimeoutError('session deadline during data generation')
                dims=rng.uniform(.03,.06,(2,1)).repeat(3,axis=1)
                if cuboid:
                    for j in range(2):
                        while True:
                            dims[j]=rng.uniform(.03,.07,3)
                            if dims[j].max()/dims[j].min()>=1.5:break
                xy=rng.uniform(-.14,.14,(2,2))
                while np.linalg.norm(xy[0]-xy[1])<.10:xy=rng.uniform(-.14,.14,(2,2))
                xyz=np.c_[xy,env.table_offset[2]+dims[:,2]/2]
                for j,cube in enumerate(env.cubes):
                    for gid in geomids[j]:env.sim.model.geom_size[gid]=dims[j]/2
                    angle=rng.uniform(-np.pi,np.pi)
                    env.sim.data.set_joint_qpos(cube.joints[0],np.r_[xyz[j],np.cos(angle/2),0,0,np.sin(angle/2)])
                env.sim.forward()
                views=[np.ascontiguousarray(env.sim.render(width=128,height=128,camera_name=c)[::-1]) for c in cameras]
                images.append(views);labels.append(xyz);sizes.append(dims)
                if i%32==0:update(stage='render',split=split,rendered=i,render_total=count)
            x=np.asarray(images,dtype=np.uint8);y=np.asarray(labels,dtype=np.float32)
            path=run/'data'/f'{split}.npz'
            np.savez_compressed(path,images=x,positions=y,dimensions=np.asarray(sizes))
            with (run/'data_manifest.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(dict(split=split,seed=seed,count=count,cuboid=cuboid,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))+'\n')
            if split=='train_initial':
                Image.fromarray(np.concatenate(x[0],axis=1)).save(run/'camera_preview.png')
            return x,y
        n=16 if smoke else 512
        validation=collect('validation',7000000,n)
        initial=collect('train_initial',6000000,n)
        probe=initial
        replay=[initial]
        center=torch.tensor([0.,0.,.82],device='cuda')
        def inputs(x):return torch.tensor(x.transpose(0,1,4,2,3),device='cuda',dtype=torch.float32)/255
        def targets(y):return (torch.tensor(y,device='cuda')-center)/.15
        vx,vy=inputs(validation[0]),targets(validation[1])
        px,py=inputs(probe[0]),targets(probe[1])
        models={};curves=[]
        for seed in (1,2,3):
            for arm in ('fixed','fixed_wrist'):
                torch.manual_seed(seed)
                model=Model()
                # At 128px the final feature map is 16x16. Fixed 4x4 pooling
                # equals adaptive 4x4 output, with a deterministic CUDA backward.
                model.encoder[-1]=torch.nn.AvgPool2d(4,stride=4)
                model=model.cuda()
                models[(seed,arm)]=dict(model=model,opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=.01),
                    updates=0,best=float('inf'),best_cycle=None)
        def mask(x,arm):
            if arm=='fixed':x=x.clone();x[:,2]=0
            return x
        @torch.no_grad()
        def evaluate(model,x,y,arm):
            model.eval();total=0.;pred=[]
            for start in range(0,len(x),32):
                p=model(mask(x[start:start+32],arm));total+=float(((p-y[start:start+32])**2).sum())
                pred.append((p*.15+center).cpu().numpy())
            return total/y.numel(),np.concatenate(pred)
        def validation_round(cycle,train_x=None,train_y=None):
            train_x=px if train_x is None else train_x
            train_y=py if train_y is None else train_y
            for (seed,arm),member in models.items():
                train_loss,_=evaluate(member['model'],train_x,train_y,arm)
                probe_loss,_=evaluate(member['model'],px,py,arm)
                val,pred=evaluate(member['model'],vx,vy,arm)
                if not np.isfinite([train_loss,val]).all():raise RuntimeError('nonfinite evaluation')
                row=dict(time=stamp(),elapsed_seconds=time.time()-cfg['started_unix'],cycle=cycle,
                    seed=seed,arm=arm,updates=member['updates'],train_mse=train_loss,validation_mse=val,
                    train_probe_mse=probe_loss,active_training_scenes=len(train_x),
                    validation_mm=metrics(pred,validation[1])['mean_3d_mm'])
                curves.append(row)
                checkpoint=dict(model=member['model'].state_dict(),optimizer=member['opt'].state_dict(),
                    updates=member['updates'],cycle=cycle,seed=seed,arm=arm,torch_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all(),numpy_rng=np.random.get_state(),config=cfg)
                path=run/'checkpoints'/f'{arm}_seed{seed}'
                atomic_checkpoint(path.with_name(path.name+'_latest.pth'),checkpoint,torch)
                if val<member['best']:
                    member['best']=val;member['best_cycle']=cycle
                    atomic_checkpoint(path.with_name(path.name+'_best.pth'),checkpoint,torch)
                update(stage='validation',cycle=cycle,model=f'{arm}_seed{seed}',step=member['updates'],loss=val,
                       latest_metrics=row)
            save(run/'curves.json',curves)
            plot(curves,run/'loss.png')
        validation_round(0)
        cycle=0;data_bytes=sum(p.stat().st_size for p in (run/'data').glob('*.npz'))
        stop_reason='time_budget'
        while time.time()<stop_train:
            cycle+=1
            fresh=collect(f'train_{cycle:06d}',6000000+cycle,16 if smoke else 256)
            replay.append(fresh);replay=replay[-8:]
            bankx=np.concatenate([r[0] for r in replay]);banky=np.concatenate([r[1] for r in replay])
            x,y=inputs(bankx),targets(banky)
            for step in range(2 if smoke else 100):
                if time.time()>=stop_train:break
                for seed in (1,2,3):
                    # Same sampled examples, initialization and update counts within each paired arm.
                    rng=np.random.default_rng(np.random.SeedSequence([seed,cycle,step]))
                    idx=rng.integers(0,len(x),32)
                    for arm in ('fixed','fixed_wrist'):
                        member=models[(seed,arm)];m=member['model'];m.train()
                        loss=((m(mask(x[idx],arm))-y[idx])**2).mean()
                        if not torch.isfinite(loss):raise RuntimeError('nonfinite training loss')
                        member['opt'].zero_grad();loss.backward()
                        norm=torch.nn.utils.clip_grad_norm_(m.parameters(),10.,error_if_nonfinite=True)
                        member['opt'].step();member['updates']+=1
                if step%10==0:update(stage='train',cycle=cycle,step=models[(1,'fixed')]['updates'],loss=float(loss.detach()))
            validation_round(cycle,x,y)
            del x,y
            data_bytes+=(run/'data'/f'train_{cycle:06d}.npz').stat().st_size
            if data_bytes>30*1024**3:stop_reason='30GiB_dataset_budget';break
            if smoke:stop_reason='smoke_complete';break
        # Select and freeze all six models before opening either reserved split.
        frozen=[]
        for (seed,arm),member in models.items():
            path=run/'checkpoints'/f'{arm}_seed{seed}_best.pth'
            frozen.append(dict(seed=seed,arm=arm,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               best_validation_mse=member['best'],best_cycle=member['best_cycle'],updates_paid=member['updates']))
        save(run/'selection.json',dict(time=stamp(),models=frozen))
        tests={}
        for split,cuboid,seed in [('test_cube',False,8000000),('test_cuboid',True,8000001)]:
            test=collect(split,seed,16 if smoke else 512,cuboid)
            tx,ty=inputs(test[0]),targets(test[1]);rows=[]
            for row in frozen:
                m=models[(row['seed'],row['arm'])]['model']
                m.load_state_dict(torch.load(row['path'],map_location='cuda',weights_only=False)['model'])
                _,pred=evaluate(m,tx,ty,row['arm'])
                rows.append(dict(seed=row['seed'],arm=row['arm'],metrics=metrics(pred,test[1])))
                np.savez_compressed(run/f"{split}_{row['arm']}_{row['seed']}_predictions.npz",predictions=pred,truth=test[1])
            tests[split]=rows
        save(run/'results.json',dict(time=stamp(),stop_reason=stop_reason,cycles=cycle,models=frozen,tests=tests,
                                     elapsed_seconds=time.time()-cfg['started_unix']))
        update(stage='complete',cycle=cycle,stop_reason=stop_reason)
    finally:env.close()


def plot(curves,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,2,figsize=(10,9),sharex=True,layout='constrained')
    for seed in (1,2,3):
        for j,arm in enumerate(('fixed','fixed_wrist')):
            rows=[r for r in curves if r['seed']==seed and r['arm']==arm]
            ax=axes[seed-1,j];x=[r['updates'] for r in rows]
            ax.plot(x,[r['train_mse'] for r in rows],label='Training (gesamter aktiver Replaypuffer)')
            ax.plot(x,[r['validation_mse'] for r in rows],label='Validation (vollständig)')
            ax.plot(x,[r['train_probe_mse'] for r in rows],label='Feste Trainingsprobe',alpha=.65,linestyle=':')
            ax.set_yscale('log');ax.set_title(f'{arm} | Seed {seed}');ax.grid(alpha=.2)
            ax.set_xlabel('Optimizerupdates');ax.set_ylabel('Normierter XYZ-MSE');ax.legend(fontsize=7)
    fig.suptitle('Visuelle Würfel-Lokalisierung | 128×128 | keine Montage')
    temp=path.with_suffix('.tmp.png');fig.savefig(temp,dpi=130);plt.close(fig)
    for attempt in range(10):
        try:temp.replace(path);break
        except PermissionError:
            if attempt==9:raise
            time.sleep(.1)


def supervise(run, smoke):
    proof=independence();save(run/'independence.json',proof)
    if not smoke and (not proof['query_ok'] or proof['in_job']):raise RuntimeError('Supervisor inside process job')
    k=ctypes.windll.kernel32
    if not k.SetThreadExecutionState(0x80000001):raise RuntimeError('Cannot inhibit automatic system sleep')
    cfg=json.loads((run/'config.json').read_text())
    try:
        with (run/'worker.log').open('w',encoding='utf-8') as log:
            command=[sys._base_executable,str(HERE/'night.py'),'worker',str(run)]+(['--smoke'] if smoke else [])
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            save(run/'supervisor.json',dict(pid=os.getpid(),worker_pid=child.pid,started=stamp(),deadline_unix=cfg['deadline_unix']))
            reason=None
            while child.poll() is None:
                time.sleep(2 if smoke else 15)
                now=time.time()
                if now>cfg['deadline_unix']+120:reason='hard_deadline';break
                state=run/'status.json'
                if state.exists() and now-state.stat().st_mtime>1200:reason='no_heartbeat_20_minutes';break
            if reason:
                child.terminate();child.wait(timeout=30)
                save(run/'status.json',dict(stage='error',reason=reason,time=stamp()))
            save(run/'supervisor_exit.json',dict(returncode=child.returncode,reason=reason,time=stamp()))
    finally:k.SetThreadExecutionState(0x80000000)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['launch','supervise','worker'])
    parser.add_argument('run',type=Path);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    run=args.run.resolve()
    if args.mode=='launch':
        run.mkdir(exist_ok=False);(run/'data').mkdir();(run/'checkpoints').mkdir()
        start=time.time()
        save(run/'config.json',dict(started=stamp(),started_unix=start,deadline_unix=start+(180 if args.smoke else 36000),
            hours=10,smoke=args.smoke,lr=.0003,weight_decay=.01,batch=32,seeds=[1,2,3],
            images=128,train_shapes='cubes_only',validation_seed=7000000,test_seeds=[8000000,8000001],
            replay_shards=8,updates_per_cycle=100,train_probe=512,validation=512,
            gradient_clip=10,loss='normalized_xyz_mse',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        (run/'source.py').write_bytes(Path(__file__).read_bytes())
        (run/'pilot_source.py').write_bytes((ROOT/'experiments/vision/visual_cube_transfer_20261031/pilot.py').read_bytes())
        if args.smoke:
            supervise(run,True)
            print(json.dumps(dict(run=str(run),smoke=True)),flush=True)
            return
        command=[sys._base_executable,str(HERE/'night.py'),'supervise',str(run)]+(['--smoke'] if args.smoke else [])
        with (run/'supervisor.log').open('w') as log:
            flags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            if not args.smoke:flags|=subprocess.CREATE_BREAKAWAY_FROM_JOB
            p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        save(run/'launch.json',dict(pid=p.pid,time=stamp()));print(json.dumps(dict(pid=p.pid,run=str(run))),flush=True)
    elif args.mode=='supervise':supervise(run,args.smoke)
    else:
        try:worker(run,args.smoke)
        except Exception as exc:
            save(run/'status.json',dict(stage='error',error=repr(exc),time=stamp()));traceback.print_exc();raise


if __name__=='__main__':main()
