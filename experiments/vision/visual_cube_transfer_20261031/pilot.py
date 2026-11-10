"""Bounded RGB localization pilot; no policy or simulator dynamics claims."""
from pathlib import Path
import argparse, hashlib, json, sys, time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments/baselines/square/scripts'))
import runtime
import robosuite
import mujoco
import torch
from torch import nn
from PIL import Image, ImageDraw


def save(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    for attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 9: raise
            time.sleep(.05 * (attempt + 1))


def aim(env, name, position, target):
    idx = env.sim.model.camera_name2id(name)
    z = np.asarray(position) - target
    z /= np.linalg.norm(z)
    x = np.cross([0., 0., 1.], z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, np.column_stack([x, y, z]).ravel())
    env.sim.model.cam_pos[idx] = position
    env.sim.model.cam_quat[idx] = quat
    env.sim.model.cam_fovy[idx] = 45


def collect(out, smoke=False):
    np.random.seed(31000)
    meta = json.loads((ROOT/'experiments/baselines/additional_tasks/stack_two/task_info.json').read_text())
    kw = meta['environment']['env_kwargs']
    cameras = ['agentview', 'frontview', 'robot0_eye_in_hand']
    kw.update(camera_names=cameras, camera_heights=64, camera_widths=64,
              use_camera_obs=False, use_object_obs=False, hard_reset=False,
              has_renderer=False, has_offscreen_renderer=True)
    env = robosuite.make('StackTwo', **kw)
    datasets = {}
    try:
        env.reset()
        aim(env, 'agentview', np.array([.8, -.7, 1.5]), np.array([0., 0., .82]))
        aim(env, 'frontview', np.array([.8, .7, 1.5]), np.array([0., 0., .82]))
        save(out/'cameras.json', {name: dict(id=int(env.sim.model.camera_name2id(name)),
             body_id=int(env.sim.model.cam_bodyid[env.sim.model.camera_name2id(name)]),
             position=env.sim.model.cam_pos[env.sim.model.camera_name2id(name)].tolist(),
             quaternion=env.sim.model.cam_quat[env.sim.model.camera_name2id(name)].tolist()) for name in cameras})
        for split, size, seed in [('train',512,31001), ('valid',128,31002),
                                   ('test_cube',128,31003), ('test_cuboid',128,31004)]:
            rng = np.random.default_rng(seed)
            images, labels, dimensions = [], [], []
            for i in range(2 if smoke else size):
                dims = rng.uniform(.03,.06,(2,1)).repeat(3,axis=1)
                if split == 'test_cuboid':
                    for j in range(2):
                        while True:
                            dims[j] = rng.uniform(.03,.07,3)
                            if dims[j].max()/dims[j].min() >= 1.5: break
                xy = rng.uniform(-.14,.14,(2,2))
                while np.linalg.norm(xy[0]-xy[1]) < .10:
                    xy = rng.uniform(-.14,.14,(2,2))
                xyz = np.c_[xy, env.table_offset[2]+dims[:,2]/2]
                for j,cube in enumerate(env.cubes):
                    for geom_name in cube.contact_geoms + cube.visual_geoms:
                        gid = env.sim.model.geom_name2id(geom_name)
                        env.sim.model.geom_size[gid] = dims[j]/2
                    angle = rng.uniform(-np.pi,np.pi)
                    env.sim.data.set_joint_qpos(cube.joints[0], np.r_[xyz[j],np.cos(angle/2),0,0,np.sin(angle/2)])
                env.sim.forward()
                views = [np.ascontiguousarray(env.sim.render(width=64,height=64,camera_name=c)[::-1]) for c in cameras]
                images.append(views); labels.append(xyz); dimensions.append(dims)
                if i == 0:
                    panel = Image.new('RGB',(192,84),'white'); draw=ImageDraw.Draw(panel)
                    for j,frame in enumerate(views):
                        panel.paste(Image.fromarray(frame),(j*64,20))
                        draw.text((j*64+2,3), ['fixed A','fixed B','wrist'][j],fill='black')
                    panel.resize((768,336)).save(out/f'{split}_preview.png')
                if i % 64 == 0:
                    save(out/'status.json',dict(stage='render',split=split,completed=i,total=size))
            x = np.asarray(images,dtype=np.uint8)
            y = np.asarray(labels,dtype=np.float32)
            datasets[split]=(x,y)
            np.savez_compressed(out/f'{split}.npz', images=x, positions=y, dimensions=np.asarray(dimensions))
        return datasets
    finally:
        env.close()


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=nn.Sequential(nn.Conv2d(3,16,5,2,2),nn.ReLU(),
            nn.Conv2d(16,32,3,2,1),nn.ReLU(),nn.Conv2d(32,32,3,2,1),nn.ReLU(),
            nn.AdaptiveAvgPool2d((4,4)))
        self.head=nn.Sequential(nn.Flatten(),nn.Linear(3*32*4*4,128),nn.ReLU(),nn.Linear(128,6))
    def forward(self,x):
        n,v,c,h,w=x.shape
        return self.head(self.encoder(x.reshape(n*v,c,h,w)).reshape(n,v,-1)).reshape(n,2,3)


def metrics(pred, truth):
    delta=(pred-truth)*1000
    dist=np.linalg.norm(delta,axis=-1)
    return dict(mean_3d_mm=float(dist.mean()),p90_3d_mm=float(np.quantile(dist,.9)),
                mean_xy_mm=float(np.linalg.norm(delta[:,:,:2],axis=-1).mean()),
                mean_abs_z_mm=float(np.abs(delta[:,:,2]).mean()),within_10mm=float((dist<=10).mean()))


def train(out, data, development_only=False):
    device='cuda' if torch.cuda.is_available() else 'cpu'
    torch.set_num_threads(4)
    center=torch.tensor([0.,0.,.82],device=device)
    tensors={s:(torch.tensor(x.transpose(0,1,4,2,3),device=device,dtype=torch.float32)/255,
                (torch.tensor(y,device=device)-center)/.15) for s,(x,y) in data.items()}
    results=[]; curves=[]
    # Both arms selected on validation before any reserved test is evaluated.
    for seed in (1,2):
        for arm in ('fixed','fixed_wrist'):
            torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
            model=Model().to(device);opt=torch.optim.AdamW(model.parameters(),lr=3e-4)
            generator=np.random.default_rng(seed); best=float('inf');best_update=None
            x,y=tensors['train']; xv,yv=tensors['valid']
            def masked(z):
                if arm=='fixed':
                    z=z.clone();z[:,2]=0
                return z
            @torch.no_grad()
            def evaluate_mse(inputs, targets):
                model.eval()
                total=0.
                for start in range(0,len(inputs),128):
                    error=(model(masked(inputs[start:start+128]))-targets[start:start+128])**2
                    total+=float(error.sum())
                return total/targets.numel()
            curves.append(dict(seed=seed,arm=arm,update=0,
                train_mse=evaluate_mse(x,y),validation_mse=evaluate_mse(xv,yv),
                data_pass_equivalents=0.))
            for update in range(1,601):
                idx=generator.integers(0,len(x),32)
                model.train(); loss=((model(masked(x[idx]))-y[idx])**2).mean()
                if not torch.isfinite(loss): raise RuntimeError('nonfinite loss')
                opt.zero_grad();loss.backward();opt.step()
                if update % 25 == 0:
                    model.eval()
                    val=evaluate_mse(xv,yv)
                    curves.append(dict(seed=seed,arm=arm,update=update,batch_mse=float(loss.detach()),
                        train_mse=evaluate_mse(x,y),validation_mse=val,data_pass_equivalents=update*32/len(x)))
                    # Preserve original checkpoint-selection schedule for diagnostic replay.
                    if update % 100 == 0 and val<best:
                        best=val;best_update=update
                        torch.save(model.state_dict(),out/f'{arm}_seed{seed}.pth')
                    save(out/'status.json',dict(stage='train',arm=arm,seed=seed,update=update))
                    save(out/'curves.json',curves)
            results.append(dict(seed=seed,arm=arm,best_update=best_update,validation_mse=best))
    if development_only:
        return dict(device=device,results=results,development_only=True,
                    note='Same frozen training configuration; additional train/validation logging, no endtests.')
    for row in results:
        model=Model().to(device)
        model.load_state_dict(torch.load(out/f"{row['arm']}_seed{row['seed']}.pth",map_location=device,weights_only=True))
        model.eval()
        for split in ('test_cube','test_cuboid'):
            x,y=tensors[split]
            if row['arm']=='fixed': x=x.clone();x[:,2]=0
            with torch.no_grad(): pred=(model(x)*.15+center).cpu().numpy()
            row[split]=metrics(pred,data[split][1])
            np.savez_compressed(out/f"predictions_{row['arm']}_{row['seed']}_{split}.npz",pred=pred,truth=data[split][1])
    save(out/'curves.json',curves)
    mean_position=data['train'][1].mean(axis=0)
    baseline={s:metrics(np.broadcast_to(mean_position,y.shape),y)
              for s,(_,y) in data.items() if s.startswith('test_')}
    return dict(device=device,results=results,constant_training_mean_baseline=baseline)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--data-from',type=Path);parser.add_argument('--output-name')
    parser.add_argument('--development-only',action='store_true')
    args=parser.parse_args()
    out=HERE/(args.output_name or ('smoke' if args.smoke else 'run_001'));out.mkdir(exist_ok=False)
    started=time.time()
    save(out/'manifest.json',dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         protocol_sha256=hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),smoke=args.smoke,
         data_from=str(args.data_from) if args.data_from else None,development_only=args.development_only))
    try:
        if args.data_from:
            data={}
            for split in (('train','valid') if args.development_only else ('train','valid','test_cube','test_cuboid')):
                with np.load(args.data_from/f'{split}.npz') as f:
                    data[split]=(f['images'].copy(),f['positions'].copy())
        else:
            data=collect(out,args.smoke)
        result=dict(smoke=True) if args.smoke else train(out,data,args.development_only)
        result['elapsed_seconds']=time.time()-started
        save(out/'results.json',result);save(out/'status.json',dict(stage='complete'))
        print(json.dumps(result),flush=True)
    except Exception as exc:
        save(out/'status.json',dict(stage='error',error=repr(exc)));raise


if __name__=='__main__': main()
