"""One bounded production session, requiring the user's hash-bound release.

Default is inspection only. No approval token is created by this program.
"""
from pathlib import Path
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
import traceback
from transition_pilot import sha, dump

HERE=Path(__file__).resolve().parent
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'numba_cache'))


def write_report(run):
    """Truthful automatic inventory; scientific interpretation remains separate."""
    run=Path(run);lines=['# Automatischer B0/B-Laufbericht',
        'Qualitätsgewichtung gegen Einheitsgewichtung; kein Fünfertraining und keine Erfolgsprognose.']
    for filename in ('session.json','status.json','supervisor_status.json','training/status.json'):
        path=run/filename
        if path.exists():lines.extend([f'## {filename}','```json',path.read_text(),'```'])
    lines.extend(['## Vollständige und teilweise Endauswertungen',
                  '| Modell/Split | Metrik | Erfolge | Versuche | vollständig |',
                  '|---|---|---:|---:|---|'])
    for path in sorted((run/'final_test').glob('*.json')):
        data=json.loads(path.read_text())
        if not isinstance(data,dict):continue
        for key,value in data.items():
            if isinstance(value,dict) and 'attempts' in value and 'successes' in value:
                lines.append(f"| {path.stem} | {key} | {value['successes']} | {value['attempts']} | {value.get('complete',False)} |")
    lines.append('Fehlende Tests sind ungemessen. Nicht abgeschlossene Starts werden weder als Erfolg noch als Misserfolg erfunden. In evaluation_progress liegen inkrementelle Teilresultate; reservierte Starts werden nicht automatisch wiederholt.')
    if (run/'final_test/selection.json').exists():
        lines.append('Die Auswahl wurde vor Bestätigung/Endtest gemeinsam eingefroren; Einzelheiten und Vollständigkeit stehen in final_test/selection.json.')
    else:
        lines.append('Ein gemeinsamer Modellfreeze ist noch nicht dokumentiert. Fehlende Auswahl oder Endtests werden nicht als abgeschlossen ausgegeben.')
    lines.append('Historische Quoten mit fehlerhafter Fingerkontaktprüfung sind keine direkte Referenz für diese korrigierte Metrik.')
    (run/'REPORT_AUTOMATIC.md').write_text('\n\n'.join(lines),encoding='utf-8')


def verify_ready(plan_path,release_path):
    from production_train import release_check
    release=release_check(plan_path,release_path)
    plan=json.loads(Path(plan_path).read_text())
    assert plan.get('production_enabled') is True,'plan not ready'
    bundle=plan['ready_bundle']
    manifest_path=Path(bundle['dataset_manifest'])
    assert sha(manifest_path)==bundle['dataset_manifest_sha256'],'frozen dataset manifest changed'
    manifest=json.loads(manifest_path.read_text())
    assert manifest['production_ready'] and manifest['all_native'],'data not ready'
    for path,expected in bundle['code_hashes'].items():
        assert sha(path)==expected,('production source changed',path)
    for path,expected in bundle.get('input_hashes',{}).items():
        assert sha(path)==expected,('training input changed',path)
    for split in ('development','confirmation'):
        for key,panel in bundle['prepared_panels'][split].items():
            assert sha(panel['path'])==panel['sha256'],('benchmark manifest changed',split,key)
            for row in json.loads(Path(panel['path']).read_text())['rows']:
                if row.get('prepared',False):assert sha(row['path'])==row['sha256'],'prepared state changed'
    return plan,manifest,release


def worker(run):
    import torch
    from production_train import train_paired,freeze_and_test
    from online_evaluation import evaluator_from_plan,prepare_reserved_panels
    run=Path(run);session=json.loads((run/'session.json').read_text())
    with (run/'worker.started.json').open('x') as f:json.dump(dict(pid=os.getpid()),f)
    plan,manifest,release=verify_ready(run/'plan.json',run/'release.json')
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    panels={}
    for split,mapping in plan['ready_bundle']['prepared_panels'].items():
        panels[split]={key:entry['path'] for key,entry in mapping.items()}
    regular=evaluator_from_plan(plan,panels,progress_root=run/'evaluation_progress')
    reserved_evaluator=None
    def evaluator(path,seed,update,split,deadline):
        nonlocal reserved_evaluator
        if split=='reserved_final':
            if reserved_evaluator is None:
                selection=run/'final_test/selection.json'
                # prepare_reserved_panels verifies all six model hashes itself.
                assert selection.exists(),'all selected models must be frozen first'
                prepared=prepare_reserved_panels(plan,run/'reserved_preparation',deadline,
                    selection,plan_sha256=sha(run/'plan.json'))
                if isinstance(prepared,dict) and 'reserved_final' in prepared:
                    panels['reserved_final']=prepared['reserved_final']
                else:
                    panels['reserved_final']=prepared
                reserved_evaluator=evaluator_from_plan(plan,panels,progress_root=run/'evaluation_progress')
            return reserved_evaluator(path,seed,update,split,deadline)
        return regular(path,seed,update,split,deadline)
    dump(run/'status.json',dict(state='TRAINING_AND_DEVELOPMENT',deadline=session['deadline']))
    result=train_paired(plan,manifest,run/'training',session['training_deadline'],evaluator,
                        release=release,device='cuda')
    dump(run/'training_result.json',result)
    dump(run/'status.json',dict(state='FREEZE_AND_FINAL_EVALUATION'))
    try:
        results=freeze_and_test(result,run/'final_test',evaluator,session['deadline']-120)
        state='COMPLETE' if result['state']=='COMPLETE' else 'COMPLETE_WITH_PARTIAL_TRAINING'
        dump(run/'status.json',dict(state=state,result_groups=len(results),finished_unix=time.time()))
    except TimeoutError:
        dump(run/'status.json',dict(state='PARTIAL_TIME_LIMIT',reason='final evaluation incomplete',finished_unix=time.time()))
    finally:write_report(run)


def supervise(plan_path,release_path,output):
    plan,_,_=verify_ready(plan_path,release_path)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    global_lock=HERE/'ACTIVE_RUN.json'
    with global_lock.open('x') as f:json.dump(dict(pid=os.getpid(),run=str(output.resolve())),f)
    process=None;info=dict(state='STARTING',pid=os.getpid())
    try:
        (output/'plan.json').write_bytes(Path(plan_path).read_bytes())
        (output/'release.json').write_bytes(Path(release_path).read_bytes())
        start=time.time();deadline=start+float(plan['budget']['proposed_max_wall_hours'])*3600
        session=dict(start=start,deadline=deadline,
                     training_deadline=deadline-plan['budget']['training_stop_hours_before_deadline']*3600,
                     supervisor_pid=os.getpid(),plan_sha256=sha(output/'plan.json'))
        dump(output/'session.json',session)
        with (output/'coordinator.lock').open('x') as f:json.dump(dict(pid=os.getpid()),f)
        if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        info.update(state='RUNNING',deadline=deadline)
        with (output/'worker.log').open('ab',buffering=0) as log:
            process=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--worker',str(output.resolve())],
                 stdout=log,stderr=log,stdin=subprocess.DEVNULL,
                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            info['worker_pid']=process.pid;dump(output/'supervisor_status.json',info)
            while process.poll() is None:
                if time.time()>=deadline or (output/'STOP').exists():
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                    else:process.terminate()
                    process.wait(timeout=20);info['state']='TIME_LIMIT_OR_STOP';break
                time.sleep(2)
            else:info['state']='COMPLETED' if process.returncode==0 else 'FAILED'
            info['returncode']=process.returncode
    except Exception:info.update(state='FAILED',error=traceback.format_exc())
    finally:
        try:
            if process is not None and process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                else:process.terminate()
                process.wait(timeout=20)
        finally:
            info['finished_unix']=time.time()
            info['wake_lock_released']=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)) if os.name=='nt' else True
            dump(output/'supervisor_status.json',info)
            if global_lock.exists():
                owner=json.loads(global_lock.read_text())
                if owner.get('pid')==os.getpid() and owner.get('run')==str(output.resolve()):global_lock.unlink()
            write_report(output)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--start',action='store_true')
    parser.add_argument('--worker',type=Path);parser.add_argument('--plan',type=Path)
    parser.add_argument('--release',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.worker:
        try:worker(args.worker)
        except Exception:
            dump(args.worker/'failure.json',dict(error=traceback.format_exc(),failed_unix=time.time()))
            write_report(args.worker)
            raise
    elif args.start:
        assert args.plan and args.release and args.output,'plan, explicit user release and new output folder required'
        supervise(args.plan,args.release,args.output)
    else:print(json.dumps(dict(mode='DRY_RUN',training_started=False,
            requires='--start --plan READY_PLAN --release USER_APPROVAL --output NEW_SESSION',
            user_approval_file_created=False)))


if __name__=='__main__':main()
