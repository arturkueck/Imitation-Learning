"""Bounded physical, learning, calibration and exact-resume checks."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import json,time,copy
import numpy as np,torch
from scene_data import Generator,stack
from model_prototype import ScenePerception
from learning import initialize,tensor_batch,run_model,criterion,decode

HERE=Path(__file__).resolve().parent


def settings():
    torch.set_num_threads(4);torch.manual_seed(61101);np.random.seed(61101)
    torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cuda.enable_flash_sdp(False);torch.backends.cuda.enable_mem_efficient_sdp(False)


def stats(model,batch):
    model.eval()
    with torch.no_grad():
        out,av=run_model(model,batch,'fixed_wrist');loss,_,matches=criterion(out,batch,av);d=decode(out)
        error=[];counts=[]
        for i,(p,g) in enumerate(matches):
            if len(p):error.extend(torch.linalg.vector_norm(d['position'][i,p]-batch['positions'][i,g],dim=-1).cpu().numpy()*1000)
            counts.append(int((d['probability'][i]>=.5).sum())==len(g))
    return dict(loss=float(loss),position_mm=float(np.mean(error)),count_accuracy=float(np.mean(counts)))


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='preflight_002');args=parser.parse_args()
    settings();out=HERE/args.name;out.mkdir(exist_ok=False)
    g=Generator();t=time.time()
    try:
        rows=[g.scene(910001,i,force_count=i%4) for i in range(32)]
        # Additional five-object samples test geometry/calibration, not the tiny training targets.
        extra=[g.scene(910002,i,force_count=5) for i in range(16)]
        data=stack(rows);np.savez_compressed(out/'tiny_data.npz',**data)
        generation=time.time()-t;rejected=g.rejections.copy()
    finally:g.close()
    model=initialize(ScenePerception()).cuda();opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    batch=tensor_batch(data,np.arange(32));history=[];first=stats(model,batch)
    def step(m,o):
        m.train();o.zero_grad();prediction,av=run_model(m,batch,'fixed_wrist');loss,_,_=criterion(prediction,batch,av)
        if not torch.isfinite(loss):raise RuntimeError('nonfinite preflight loss')
        loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);o.step();return float(loss.detach())
    began=time.time();resume_ok=False
    for update in range(1,2401):
        if update==801:
            for group in opt.param_groups:group['lr']=.0002
        step(model,opt)
        if update==25:
            state=copy.deepcopy(dict(model=model.state_dict(),opt=opt.state_dict(),rng=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all()))
            expected_loss=step(model,opt);expected=copy.deepcopy(model.state_dict())
            model.load_state_dict(state['model']);opt.load_state_dict(state['opt']);torch.set_rng_state(state['rng']);torch.cuda.set_rng_state_all(state['cuda'])
            actual_loss=step(model,opt)
            difference=max(float((model.state_dict()[k]-expected[k]).abs().max()) for k in expected)
            if abs(expected_loss-actual_loss)>1e-7 or difference>1e-7:raise RuntimeError(f'Resume not exact: {difference}')
            resume_ok=True
        if update%50==0:
            row=dict(update=update,**stats(model,batch));history.append(row)
            (out/'progress.json').write_text(json.dumps(dict(initial=first,history=history,elapsed_seconds=time.time()-began),indent=2))
            print(json.dumps(row),flush=True)
            if row['position_mm']<=7 and row['count_accuracy']>=.90 and row['loss']<first['loss']*.25:break
    final=stats(model,batch)
    torch.save(model.state_dict(),out/'tiny_model.pth')
    passed=final['position_mm']<=7 and final['count_accuracy']>=.90 and resume_ok
    report=dict(passed=passed,initial=first,final=final,updates=update,seconds_per_update=(time.time()-began)/update,
        exact_resume=resume_ok,generation_scenes=48,generation_seconds=generation,rejections=rejected,
        projection_segmentation_checks='passed_for_every_visible_object',peak_gpu_gib=torch.cuda.max_memory_allocated()/2**30,
        diagnostic_learning_rate=.001,production_learning_rate=.0003)
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    if not passed:raise RuntimeError('Tiny-set learning acceptance not met; production is not authorized by this check')


if __name__=='__main__':main()
