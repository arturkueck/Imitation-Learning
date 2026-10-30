"""Bounded two-block session; block2 requires an actual agent-written analysis."""
from pathlib import Path
import subprocess,sys,json,time,os,ctypes,traceback,datetime
OUT=Path(__file__).resolve().parent
def write(p,d):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2));tmp.replace(p)
def kill_tree(process):
    # Only the exact child launched by this coordinator, including its venv child.
    if process.poll() is None:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
def run_block(plan,global_deadline):
    path=OUT/(plan['name']+'_plan.json');write(path,plan)
    with (OUT/(plan['name']+'.log')).open('ab',buffering=0) as log:
        child=subprocess.Popen([sys.executable,'-u',str(OUT/'train_block.py'),'--plan',str(path)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        write(OUT/'active_child.json',dict(pid=child.pid,block=plan['name']))
        while child.poll() is None:
            if time.time()>=min(global_deadline,plan['train_deadline']+30) or (OUT/'STOP').exists():kill_tree(child);break
            time.sleep(2)
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:kill_tree(child)
        return child.returncode
def main():
    session=json.loads((OUT/'session.json').read_text());end=session['deadline'];first=session['block1_deadline'];state=dict(state='BLOCK1_RUNNING',pid=os.getpid(),deadline=end)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        write(OUT/'status.json',state)
        plan=json.loads((OUT/'block1_plan.json').read_text());code=run_block(plan,end)
        state.update(state='AWAITING_AGENT_ANALYSIS' if code==0 else 'BLOCK1_FAILED',block1_returncode=code);write(OUT/'status.json',state)
        # No fallback invents an agent analysis or launches an unchanged second run.
        while time.time()<end and not (OUT/'STOP').exists():
            decision=OUT/'block2_decision.json'
            if decision.exists():
                d=json.loads(decision.read_text());assert d['agent_analysis_complete'] and (OUT/'REPORT_1.md').exists()
                plan=d['plan'];assert plan['name']=='block2' and plan['train_deadline']<=end
                assert all(str(Path(v).resolve()).startswith(str(OUT.resolve())) for v in plan.get('parents',{}).values())
                state['state']='BLOCK2_RUNNING';write(OUT/'status.json',state);code=run_block(plan,end)
                state.update(state='AWAITING_FINAL_ANALYSIS',block2_returncode=code);write(OUT/'status.json',state)
                while time.time()<end and not (OUT/'STOP').exists() and not (OUT/'REPORT_2.md').exists():time.sleep(3)
                if (OUT/'REPORT_2.md').exists():state['state']='COMPLETED'
                break
            time.sleep(3)
        if state['state'] not in ['AWAITING_FINAL_ANALYSIS','COMPLETED']:
            state['state']='STOPPED' if (OUT/'STOP').exists() else 'DEADLINE_WITHOUT_SECOND_BLOCK'
    except Exception:state.update(state='FAILED',error=traceback.format_exc())
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);state['coordinator_finished']=True;write(OUT/'status.json',state)
if __name__=='__main__':main()
