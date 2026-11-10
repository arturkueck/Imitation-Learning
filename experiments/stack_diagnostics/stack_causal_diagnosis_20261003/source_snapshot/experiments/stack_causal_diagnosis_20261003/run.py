"""Detached bounded evaluation worker: Exp0 -> Exp1, then exit. No training."""
import ctypes, hashlib, json, os, subprocess, sys, time, traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]

def write(name,obj):
    p=OUT/name;tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');tmp.replace(p)

def main():
    assert not (OUT/'worker_started.json').exists(),'Refusing duplicate'
    assert json.loads((OUT/'preflight_v3/complete.json').read_text())['completed']
    assert json.loads((OUT/'anchor_preflight_v3/complete.json').read_text())['episodes']==30
    assert json.loads((OUT/'unet_config_fix_verified.json').read_text())['passed']
    for name,h in json.loads((OUT/'source_hashes.json').read_text()).items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,('Source/config changed',name)
    write('worker_started.json',dict(pid=os.getpid(),started_unix=time.time(),training=False))
    log=(OUT/'run.log').open('a',encoding='utf-8',buffering=1);sys.stdout=log;sys.stderr=log
    keep_awake=ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        for stage in ('baseline','phases'):
            write('status.json',dict(state='RUNNING',stage=stage,pid=os.getpid(),training=False))
            print('STAGE',stage,flush=True)
            child=subprocess.Popen([sys.executable,'-u',str(OUT/'evaluate.py'),stage],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            write('status.json',dict(state='RUNNING',stage=stage,pid=os.getpid(),child_pid=child.pid,training=False))
            # Waiting occurs only inside this detached worker; the assistant does not monitor it.
            code=child.wait()
            if code:raise RuntimeError(f'{stage} exited with {code}; inspect run.log and {stage}_failed.json')
        baseline=json.loads((OUT/'experiment_0_baseline/results.json').read_text())
        phases=json.loads((OUT/'experiment_1_phases/results.json').read_text())
        table=[]
        for phase in json.loads((OUT/'protocol.json').read_text())['phase_anchors'][0]['anchors']:
            for model in ('expert','direct','diffusion'):
                rows=[r for r in phases if r['phase']==phase and r['model']==model]
                table.append(dict(phase=phase,model=model,n=len(rows),stable_stacks=sum(r['sustained_success'] for r in rows),position_held=sum(r['position_held'] for r in rows),lower_held=sum(r['lower_held'] for r in rows),release=sum(r['phase_conditioned_stages']['release'] for r in rows)))
        write('results.json',dict(baseline_n=len(baseline),baseline_stable_stacks=sum(r['sustained_success'] for r in baseline),phase_summary=table,training=False))
        report=['# Exp0 und Exp1: gemessene Ergebnisse','',f"Unveränderte C-Diffusion-Baseline: {sum(r['sustained_success'] for r in baseline)}/{len(baseline)} stabile Stacks.",'','| Phase | Modell | n | Stabile Stacks | Position gehalten | Absenken gehalten | Release |','|---|---|---:|---:|---:|---:|---:|']
        report.extend(f"| {r['phase']} | {r['model']} | {r['n']} | {r['stable_stacks']} | {r['position_held']} | {r['lower_held']} | {r['release']} |" for r in table)
        report.extend(['','Bereits initial erfüllte Position-/Absenkgeometrie wird in den Einzelwerten ausgewiesen. Teilindikatoren können bereits am Start erfüllt sein; nur vollständiger stabiler Stack zählt als primärer Erfolg. Ein Seed, fünf Demos je Phase; keine robuste Methodenaussage.','Expert-Prefix-Replay erhält die Controller-/Gripper-Erinnerung. Alle Paare werden auf identische replayte Startzustände geprüft.','Es wurden keine weiteren Experimente oder Trainings automatisch gestartet. Interpretation der Failure Points erfolgt erst anhand dieser Ergebnisse.'])
        (OUT/'RESULTS.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        hashes={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.suffix not in ('.pyc','.tmp') and p.name not in ('run.log','status.json','output_hashes.json')}
        write('output_hashes.json',hashes)
        write('complete.json',dict(state='COMPLETED',pid=os.getpid(),training=False,finished_unix=time.time(),automatic_followup=False))
        write('status.json',dict(state='COMPLETED',pid=os.getpid(),training=False))
        print('COMPLETED',flush=True)
    except Exception:
        write('failed.json',dict(state='FAILED',cause=traceback.format_exc(),finished_unix=time.time()));write('status.json',dict(state='FAILED',pid=os.getpid()));traceback.print_exc();raise
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);log.flush()

if __name__=='__main__':
    if '--worker' in sys.argv:main()
    else:
        assert not (OUT/'launch.json').exists() and not (OUT/'worker_started.json').exists(),'Refusing duplicate launch'
        log=(OUT/'startup.log').open('ab',buffering=0)
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
        proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--worker'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=flags,startupinfo=startup,close_fds=True)
        write('launch.json',dict(worker_pid=proc.pid,executable=sys.executable,arguments=[str(Path(__file__).resolve()),'--worker'],creationflags=flags,started_unix=time.time(),log=str(OUT/'run.log'),training=False))
        print(json.dumps(dict(started_pid=proc.pid,experiment=str(OUT),log=str(OUT/'run.log'),training=False)))
