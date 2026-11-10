from pathlib import Path
p=Path('experiments/self_imitation/stack_transition_quality_20261024/run_training.py');s=p.read_text(encoding='utf-8')
start=s.index('def supervise(');end=s.index('\n\ndef main():',start)
new='''def supervise(plan_path,release_path,output):
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
'''
s=s[:start]+new+s[end:];s=s.replace("regular=evaluator_from_plan(plan,panels)","regular=evaluator_from_plan(plan,panels,progress_root=run/'evaluation_progress')").replace("reserved_evaluator=evaluator_from_plan(plan,panels)","reserved_evaluator=evaluator_from_plan(plan,panels,progress_root=run/'evaluation_progress')");p.write_text(s,encoding='utf-8')
