"""Original trainers, only learning change = training seed; record fresh initialization."""
import argparse,json,time
from pathlib import Path
from replication_common import OUT,ROOT,folder,weight_digest
p=argparse.ArgumentParser();p.add_argument('kind',choices=['direct','diffusion']);p.add_argument('seed',type=int,choices=[2,3]);args=p.parse_args();dest=folder(args.kind,args.seed);assert not (dest/'training_complete.json').exists();start=time.monotonic()
if args.kind=='direct':
    import direct_common
    original=direct_common.DirectChunk
    class AuditedDirect(original):
        def __init__(self):
            super().__init__();(dest/'initialization.json').write_text(json.dumps(dict(training_seed=args.seed,fresh_random_initialization=True,initial_weights_sha256=weight_digest(self)),indent=2))
    direct_common.DirectChunk=AuditedDirect;direct_common.OUT=dest
    path=Path(__file__).with_name('train_direct.py');code=path.read_text()
    prefix='random.seed(1);np.random.seed(1);torch.manual_seed(1)';assert code.count(prefix)==1;code=code.replace(prefix,f'random.seed({args.seed});np.random.seed({args.seed});torch.manual_seed({args.seed})')
    for token in ('seed=1,','default_rng(1)'):
        assert code.count(token)==1,token;code=code.replace(token,token.replace('1',str(args.seed)))
    exec(compile(code,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
else:
    import torch
    from scheduler_fix import install
    install()
    from robomimic.config import config_factory
    from robomimic.utils.torch_utils import get_torch_device
    from robomimic.scripts.train import train
    import robomimic.utils.train_utils as TU
    original=TU.run_epoch
    def audited_epoch(model,*a,**kw):
        if not (dest/'initialization.json').exists():
            assert all(int(v['step'])==0 for v in model.optimizers['policy'].state.values());(dest/'initialization.json').write_text(json.dumps(dict(training_seed=args.seed,fresh_random_initialization=True,initial_weights_sha256=weight_digest(model.nets)),indent=2))
        result=original(model,*a,**kw)
        steps={int(v['step']) for v in model.optimizers['policy'].state.values()};assert len(steps)==1;(dest/'status.json').write_text(json.dumps(dict(updates=next(iter(steps)),total=30000,elapsed_seconds=time.monotonic()-start,phase='train' if model.nets.training else 'validation'),indent=2));return result
    TU.run_epoch=audited_epoch;c=json.loads((dest/'config.json').read_text());assert c['experiment']['ckpt_path'] is None;cfg=config_factory(c['algo_name'],dic=c);cfg.lock();train(cfg,device=get_torch_device(try_to_use_cuda=True),resume=False)
(dest/'training_complete.json').write_text(json.dumps(dict(seed=args.seed,model_class=args.kind,updates=30000,elapsed_seconds=time.monotonic()-start),indent=2))
