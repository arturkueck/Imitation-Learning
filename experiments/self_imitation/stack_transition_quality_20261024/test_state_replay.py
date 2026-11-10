import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import state_replay as state

class SnapshotInvariants(unittest.TestCase):
    def test_runtime_objects_restore_in_place(self):
        original=NS(goal=np.array([1.,2.,3.]),interpolator=NS(step=3),previous=None)
        node=state.encode(original);original.goal[:]=99;original.interpolator.step=70
        self.assertIs(state.decode(node,original),original)
        np.testing.assert_array_equal(original.goal,[1.,2.,3.]);self.assertEqual(original.interpolator.step,3)
    def test_hash_rejects_corruption(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path=Path(folder)/'snapshot.pkl';snapshot=dict(schema='test',arr=np.arange(4))
            digest=state.save(path,snapshot);np.testing.assert_array_equal(state.load(path,digest)['arr'],np.arange(4))
            path.write_bytes(path.read_bytes()+b'corrupt')
            with self.assertRaisesRegex(AssertionError,'hash'):state.load(path,digest)
    def test_immutable_snapshot(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path=Path(folder)/'snapshot.pkl';state.save(path,{})
            with self.assertRaisesRegex(AssertionError,'immutable'):state.save(path,{})
    def test_unknown_native_type_fails_closed(self):
        with self.assertRaises(TypeError):state.encode({1,2})

if __name__=='__main__':unittest.main()
