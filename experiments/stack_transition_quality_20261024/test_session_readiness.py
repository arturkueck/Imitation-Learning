"""Release, provenance and failure-cleanup checks without production training."""
from pathlib import Path
import json
import tempfile
import time
import unittest
from unittest.mock import patch
import production_readiness as ready
import run_training as session
from transition_pilot import dump,sha
from production_train import release_check

HERE=Path(__file__).resolve().parent
TMP=HERE/'test_tmp';TMP.mkdir(exist_ok=True)


class SessionChecks(unittest.TestCase):
    def test_missing_release_never_creates_session(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);plan=root/'plan.json';dump(plan,dict(production_enabled=True))
            target=root/'run'
            with self.assertRaises(FileNotFoundError):session.supervise(plan,root/'absent.json',target)
            self.assertFalse(target.exists())

    def test_wrong_or_expired_release(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);plan=root/'plan.json';release=root/'release.json';dump(plan,{})
            dump(release,dict(user_approved=False,plan_sha256=sha(plan),expires_unix=time.time()+100))
            with self.assertRaisesRegex(AssertionError,'Go'):release_check(plan,release)
            dump(release,dict(user_approved=True,plan_sha256=sha(plan),expires_unix=time.time()-1))
            with self.assertRaisesRegex(AssertionError,'expired'):release_check(plan,release)

    def test_start_copy_failure_releases_global_lock(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);plan=root/'plan.json';dump(plan,dict(budget={}))
            with patch.object(session,'HERE',root),patch.object(session,'verify_ready',return_value=({}, {}, {})),\
                 patch.object(session.ctypes.windll.kernel32,'SetThreadExecutionState',return_value=1):
                # Deliberately missing approval file causes failure after lock acquisition.
                session.supervise(plan,root/'missing_release.json',root/'run')
            self.assertFalse((root/'ACTIVE_RUN.json').exists())
            self.assertEqual(json.loads((root/'run/supervisor_status.json').read_text())['state'],'FAILED')

    def test_global_lock_prevents_second_worker(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);(root/'ACTIVE_RUN.json').write_text('{}')
            with patch.object(session,'HERE',root),patch.object(session,'verify_ready',return_value=({}, {}, {})),\
                 patch.object(session.subprocess,'Popen') as popen:
                with self.assertRaises(FileExistsError):session.supervise(root/'p',root/'r',root/'run')
                popen.assert_not_called()

    def test_readiness_report_cannot_freeze_mutated_dataset(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);data=root/'data.json';dump(data,dict(rows=[],sections=[]))
            report=dict(data_ready=True,dataset_path=str(data),dataset_sha256=sha(data))
            data.write_text('{}')
            with self.assertRaisesRegex(ValueError,'stale'):ready.freeze_manifest({},data,root/'frozen.json',report)
            self.assertFalse((root/'frozen.json').exists())

    def fixture(self,root):
        n3=root/'n3';n3.mkdir();source=n3/'1.npz';source.write_bytes(b'native')
        teacher=root/'teacher.pth';teacher.write_bytes(b'parent')
        row=dict(path=str(source),sha256=sha(source),teacher=str(teacher),teacher_sha256=sha(teacher),
                 count=3,seed=1,frames=100,split='train',initial_sha256='initial',initial_family_id='family')
        section=dict(source=str(source),source_sha256=row['sha256'],teacher=str(teacher),teacher_sha256=row['teacher_sha256'],
                     count=3,seed=1,start=10,end=30,prefix=2,split='train',initial_family_id='family')
        return row,section,dict(parents=[dict(sha256=sha(teacher))],gates={})

    def test_section_outside_hashed_rows_rejected(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);row,s,plan=self.fixture(root);s['source']=str(root/'test_episode.npz')
            data=root/'manifest.json';dump(data,dict(rows=[row],sections=[s]))
            with self.assertRaisesRegex(ValueError,'absent'):ready.inspect(plan,data,measure_signal=False)

    def test_section_split_and_family_mismatch_rejected(self):
        for key,value in [('split','valid'),('initial_family_id','other'),('source_sha256','other')]:
            with tempfile.TemporaryDirectory(dir=TMP) as folder:
                root=Path(folder);row,s,plan=self.fixture(root);s[key]=value
                data=root/'manifest.json';dump(data,dict(rows=[row],sections=[s]))
                with self.assertRaisesRegex(ValueError,'provenance'):ready.inspect(plan,data,measure_signal=False)

    def test_section_out_of_frame_bounds_rejected(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            root=Path(folder);row,s,plan=self.fixture(root);s['end']=101
            data=root/'manifest.json';dump(data,dict(rows=[row],sections=[s]))
            with self.assertRaisesRegex(ValueError,'bounds'):ready.inspect(plan,data,measure_signal=False)


if __name__=='__main__':unittest.main()
