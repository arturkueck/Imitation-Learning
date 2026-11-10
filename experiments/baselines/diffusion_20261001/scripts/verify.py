"""Test real Windows file locking and all DP train/checkpoint/rollout paths."""
import ctypes
from ctypes import wintypes
import json, re, subprocess, sys, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
SHARED=ROOT/'experiments/baselines/square/scripts'
sys.path.insert(0,str(SHARED))
from atomic_json import write_json
EXP=ROOT/'experiments/baselines/diffusion_20261001'
TEST=EXP/'smoke'; TEST.mkdir(exist_ok=True)
target=TEST/'lock_test.json'; write_json(target,{'before':True})
kernel=ctypes.windll.kernel32
kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
    wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
kernel.CreateFileW.restype=wintypes.HANDLE
kernel.CloseHandle.argtypes=[wintypes.HANDLE]
handle=kernel.CreateFileW(str(target),0x80000000,0,None,3,0,None)
assert handle!=ctypes.c_void_p(-1).value
timer=threading.Timer(.25,lambda:kernel.CloseHandle(handle)); timer.start()
started=time.monotonic(); write_json(target,{'after':True}); timer.join()
assert json.loads(target.read_text())=={'after':True}
assert time.monotonic()-started>=.2
print('WINDOWS_SHARING_RETRY_OK',flush=True)
manifest=json.loads((EXP/'manifest.json').read_text())
completed=[]
for job in manifest['jobs']:
    name=job['name']; folder=TEST/name; folder.mkdir(exist_ok=True)
    cfg=json.loads(Path(job['config']).read_text())
    cfg['experiment']['name']=name+'_smoke'
    cfg['experiment']['epoch_every_n_steps']=3
    cfg['experiment']['validation_epoch_every_n_steps']=2
    cfg['experiment']['save']['every_n_epochs']=1
    cfg['train'].update(num_epochs=1,output_dir=str(folder/'runs'))
    cfg['algo']['optim_params']['policy']['learning_rate']['warmup_steps']=1
    path=folder/'config.json'; path.write_text(json.dumps(cfg,indent=2))
    with (folder/'training.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(SHARED/'train_model.py'),str(path)],
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    checkpoint=next(folder.glob('runs/**/models/model_epoch_1*.pth'))
    text=(folder/'training.log').read_text(errors='replace')
    losses=[json.loads(v)['Loss'] for v in re.findall(r'(?:Train|Validation) Epoch 1\s*(\{.*?\})',text,re.S)]
    assert len(losses)==2 and all(0<x<100 for x in losses),losses
    with (folder/'evaluation.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(SHARED/'evaluate.py'),str(checkpoint),name,
            '--output-root',str(TEST),'--episodes','1','--horizon','16','--video-episodes','1'],
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    result=json.loads((TEST/'evaluation'/name/'evaluation_results.json').read_text())
    assert result['video_layout']=='collage' and result['video_tail_seconds']==2
    completed.append(name)
    print('DIFFUSION_SMOKE_OK',name,losses,flush=True)
    write_json(TEST/'validation.json',dict(windows_sharing_retry=True,models=completed,
        technical_test_only=True))
