"""Q1 setup and gated training CLI. Preparing/preflight never trains a network."""
from pathlib import Path
import argparse,json
from q_protocol import HERE,prepare,verify,read,save,now

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','verify','preflight','start','monitor']);p.add_argument('--run',default='prepared_001');p.add_argument('--start-training',action='store_true');p.add_argument('--hours',type=float);args=p.parse_args()
    run=(HERE/args.run).resolve()
    if not run.is_relative_to(HERE) or run==HERE:raise ValueError('Run outside Q1 experiment')
    if args.action=='prepare':
        c=prepare(run);print(json.dumps(dict(status='prepared',parameters=c['model']['parameters'],training_started=False,planned_hours=c['planned_hours'])));return
    if args.action=='monitor':print(json.dumps(read(run/'status.json')));return
    cfg=verify(run)
    if args.action=='verify':print(json.dumps(dict(protocol_verified=True,training_started=False)));return
    from pipeline.locking import exclusive
    with exclusive(run):
        if args.action=='preflight':
            if (run/'head_freeze.json').exists():raise RuntimeError('Preflight cannot overwrite a trained run status')
            from q_data import collect,export
            from q_model import QualityModel,loss
            import torch,numpy as np
            collect(run,'development');d=export(run,'development');model=QualityModel().eval();count=sum(p.numel() for p in model.parameters());assert count==14788
            x=torch.as_tensor(d['x']);out=model(x)
            if not torch.isfinite(out['logits']).all() or not torch.isfinite(out['gain']).all():raise RuntimeError('Nonfinite untrained head forward')
            m=d['eligible']&d['labelled'];value=None
            if m.any():
                with torch.no_grad():value=float(loss(model,x[m],torch.tensor(d['classes'][m]),torch.tensor(d['gains'][m]),torch.ones(int(m.sum()))))
            result=dict(passed=True,parameters=count,families=cfg['splits']['development']['count'],examples=len(x),eligible_labelled=int(m.sum()),forward_finite=True,diagnostic_loss=value,optimizer_updates=0,training_started=False)
            save(run/'preflight.json',result);save(run/'status.json',dict(stage='prepared',time=now(),training_started=False,optimizer_updates=0));print(json.dumps(result));return
        if not args.start_training:raise ValueError('Training not authorized: explicit --start-training flag required after user approval')
        if not (run/'preflight.json').exists() or not read(run/'preflight.json')['passed']:raise RuntimeError('Successful preflight required')
        from pipeline.common import begin_budget
        if args.hours is not None and not 0<args.hours<=cfg['planned_hours']:raise ValueError('Budget must be within approved prepared maximum')
        begin_budget(run,args.hours)
        from q_data import collect,export
        from q_train import train
        from q_calibration import calibrate
        from q_evaluate import evaluate
        try:
            for split in ['request_train','request_validation','calibration/temperature','calibration/policy','calibration/audit']:
                collect(run,split);export(run,split)
            train(run);save(run/'status.json',dict(stage='calibrating',time=now(),training_started=True))
            if calibrate(run):
                collect(run,'reserved_test');export(run,'reserved_test');evaluate(run);outcome='complete_tested'
            else:outcome='calibration_gate_failed_test_untouched'
            save(run/'status.json',dict(stage=outcome,time=now(),training_started=True))
        except BaseException as error:
            save(run/'status.json',dict(stage='stopped' if isinstance(error,(TimeoutError,InterruptedError)) else 'error',error=repr(error),time=now(),training_started=(run/'checkpoints').exists()));raise

if __name__=='__main__':main()
