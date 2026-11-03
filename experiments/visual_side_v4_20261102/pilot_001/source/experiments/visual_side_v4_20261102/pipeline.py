"""V4 pipeline CLI. Training requires a separate explicit launch flag and budget."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
os.environ.setdefault('OMP_NUM_THREADS','4')
from pathlib import Path
import argparse,json,sys
from pipeline.common import ROOT,EXPERIMENT,read,save,sha,begin_budget,check_stop,event

def execute(args,run):
    if args.action=='prepare' and (run/'config.json').exists():raise FileExistsError('Protocol already frozen; choose a new preparation directory')
    return perform(args,run)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','verify','smoke','collect','train','start','monitor'])
    parser.add_argument('--run',default='prepared_001');parser.add_argument('--split',default='train');parser.add_argument('--hours',type=float)
    parser.add_argument('--start-training',action='store_true');parser.add_argument('--generate-data',action='store_true');parser.add_argument('--resume',action='store_true')
    parser.add_argument('--workers',type=int,choices=[1,2,3,4],default=4)
    parser.add_argument('--pilot',action='store_true',help='Prepare explicitly authorized 1000/256-family pilot with 333 historical train replay families')
    parser.add_argument('--samples',type=int,default=4);parser.add_argument('--deep',action='store_true');args=parser.parse_args()
    run=(EXPERIMENT/args.run).resolve()
    if not run.is_relative_to(EXPERIMENT.resolve()):raise ValueError('Run outside experiment')
    if args.action in ['verify','monitor']:return execute(args,run)
    from pipeline.locking import exclusive
    with exclusive(run):
        if args.action=='prepare':
            with exclusive(ROOT/'monitor/vision-namespace'):return execute(args,run)
        return execute(args,run)

def perform(args,run):
    if args.action=='prepare':
        from pipeline.lineage import inventory
        from pipeline.protocol import prepare
        from pipeline.registry import register
        run.mkdir(exist_ok=True)
        if not (run/'history.sqlite').exists():inventory(run/'history.sqlite')
        result=prepare(run,pilot=args.pilot);result['monitor_id']=register(run);print(json.dumps(result));return
    if args.action=='monitor':
        from pipeline.monitor import check
        r=check(run)
        if r['changed'] or r['level'] in ['ERROR','WARNING']:print(json.dumps(r))
        return
    from pipeline.protocol import verify_protocol,verify_imports
    cfg=verify_protocol(run,full_sources=True)
    if args.action=='verify':
        if args.deep:verify_imports(cfg)
        print(json.dumps(dict(protocol_verified=True,historical_registry_verified=True,all_ancestor_arrays_verified=args.deep,training_started=False)));return
    if args.action=='smoke':
        if (run/'checkpoints/latest.pth').exists() or (run/'perception_freeze.json').exists():raise RuntimeError('Development smoke cannot overwrite the status of a started/frozen main training')
        if not 2<=args.samples<=8:raise ValueError('Development smoke bounded to 2..8 families')
        from pipeline.generate import collect,imports
        from pipeline.audit import audit
        from pipeline.samples import Store
        from pipeline.evaluate import evaluate
        from pipeline.reporting import geometry
        collect(run,'development',smoke_count=args.samples,workers=args.workers);result=audit(run,main=False);P=imports();import torch
        parent=cfg['parents'][0];model=P.ScenePerception().cuda().eval();model.load_state_dict(torch.load(ROOT/parent['file'],map_location='cuda',weights_only=False)['model'])
        store=Store(run,'development');metrics=evaluate(model,store,run);preview=run/'development_preview';preview.mkdir(exist_ok=True)
        geometry(preview,model,store,0,1,'frozen_V3',tag='development')
        result.update(forward_passed=True,loss=metrics['loss'],optimizer_updates=0,weights_promoted=False,main_training_eligible=False)
        save(run/'smoke_report.json',result);event(run,'prepared',training_started=False,step=0,development_smoke_passed=True);print(json.dumps(result));return
    if args.action in ['train','start'] and not args.start_training:raise ValueError('No launch: --start-training requires separate user training authorization')
    if args.action=='collect' and not args.generate_data:raise ValueError('No generation: use --generate-data explicitly')
    begin_budget(run,args.hours);check_stop(run)
    from pipeline.registry import register
    register(run)
    if args.action in ['start','collect']:
        from pipeline.generate import collect
        for split in (['train','validation'] if args.action=='start' else [args.split]):
            if split not in cfg['splits']:raise ValueError('Unknown immutable split')
            collect(run,split,workers=args.workers)
    if args.action in ['start','train']:
        from pipeline.train import train
        train(run,resume=args.resume and (run/'checkpoints/latest.pth').exists())

if __name__=='__main__':main()
