import importlib.util
from pathlib import Path
import unittest
import copy
import subprocess
import sys

spec=importlib.util.spec_from_file_location('grasp_ablation_test_subject',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


class AblationTests(unittest.TestCase):
    def test_watchdog_stops_owned_child_tree(self):
        import psutil
        child_script='import time; time.sleep(30)'
        parent_script='import subprocess,sys,time; c=subprocess.Popen([sys.executable,"-c",'+repr(child_script)+']); print(c.pid,flush=True); time.sleep(30)'
        proc=subprocess.Popen([sys.executable,'-u','-c',parent_script],stdout=subprocess.PIPE,text=True)
        descendant=None
        try:
            descendant=psutil.Process(int(proc.stdout.readline().strip()))
            p.stop_worker(proc)
            self.assertIsNotNone(proc.poll())
            try:descendant.wait(timeout=3)
            except psutil.NoSuchProcess:pass
            self.assertFalse(descendant.is_running())
        finally:
            if proc.poll() is None:p.stop_worker(proc)
            if descendant is not None:
                try:descendant.kill()
                except psutil.NoSuchProcess:pass
            proc.stdout.close()

    def test_phase_scope(self):
        arms={'control':[],'close':[2],'full_grasp':[0,1,2]}
        self.assertTrue(p.selected('close',2,2,False,arms))
        for stage,phase,retreat in [(1,2,False),(2,1,False),(2,2,True),(2,3,False)]:
            self.assertFalse(p.selected('close',stage,phase,retreat,arms))
        self.assertFalse(p.selected('control',2,2,False,arms))

    def test_unreached_stays_in_total(self):
        row=dict(success=False,expert_frames=0,second_lift=None)
        group={'arms':{'control':row,'close':dict(row,success=True,expert_frames=20,second_lift={'held':True})}}
        result=p.summary([group],['control','close'])
        self.assertEqual(result['control']['n'],1)
        self.assertEqual(result['control']['reached_lift'],0)
        self.assertEqual(result['close']['gains'],1)

    def test_bad_phase_prefix_rejected(self):
        row=dict(initial_sha256='same',entries={'0':{'frame':3}},frames=10,success=False,
                 final_stage=2,final_phase=6,retreat_timeout=False,expert_frames=0,second_lift=None)
        group={'arms':{'control':copy.deepcopy(row),'full_grasp':copy.deepcopy(row)}}
        group['arms']['full_grasp']['entries']['0']['frame']=4
        with self.assertRaisesRegex(ValueError,'history mismatch'):
            p.check_group(group,{'arms':{'control':[],'full_grasp':[0,1,2]}},
                          {'control':row,'expert_grasp':row})


if __name__=='__main__':unittest.main()
