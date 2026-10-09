"""Derive rollout-only worker from frozen verified action7 code, before new answers."""
from pathlib import Path
import hashlib,json,py_compile
S=Path(__file__).resolve().parent;O=S/'mechanism_domain_001'
source=(S/'mechanism_action7_001/run.py').read_text(encoding='utf-8')
prefix=source[:source.index("        if not all(r['gates']['passed'] for r in result['rows']):")]
suffix=source[source.index('    except BaseException as exc:'):]
prefix=prefix.replace('Predeclared seven-component response diagnosis; frozen policy, no training.',
                      'Predeclared held-only phase/domain rollout; frozen calibration and policy, no training.')
prefix=prefix.replace("selection = h.read(OUT / 'selection.json')", "selection = h.read(OUT / 'selection.json')\n    calibration = h.read(OUT / 'calibration.json')")
prefix=prefix.replace("rows=[], counts=h.COUNTS)","rows=[], counts=h.COUNTS, fit_updates=0, planned_branches=336)")
prefix=prefix.replace("assert h.sha(data) == selection['dataset_sha256']", "assert h.sha(data) == selection['dataset_sha256']\n        for path, digest in calibration['calibration_sources'].items():\n            assert h.sha(Path(path)) == digest")
prefix=prefix.replace('for t in times:', 'for fraction, t in zip(selection["anchor_fractions"], times):')
prefix=prefix.replace("split='identification' if demo in selection['identification_demos'] else 'heldout', branches={}",
                      "split='heldout', fraction=fraction, stratum=str(fraction), branches={}")
prefix=prefix.replace("['B', 'A', 'Pxyz', 'Pfull']", "['B', 'A', 'Pfull']")
prefix=prefix.replace("for kind in ['Pxyz', 'Pfull']]", "for kind in ['Pfull']]")
# Existing helper/source stays frozen. Add the stricter predeclared 1-um condition.
prefix=prefix.replace("interventions_passed=all(v['intervention']['passed'] for v in b.values() if v['intervention']),",
                      "interventions_passed=all(v['intervention']['passed'] and v['intervention']['position_error_m'] <= selection['position_tolerance_m'] for v in b.values() if v['intervention']),")
prefix=prefix.replace("g['passed'] = bool(anchor_error", "g['technical_passed'] = bool(anchor_error")
prefix=prefix.replace("and g['auxiliary_fields_passed'] and g['interventions_passed'] and g['contact_free'])",
                      "and g['auxiliary_fields_passed'] and g['interventions_passed'])\n                    g['passed'] = bool(g['technical_passed'] and g['contact_free'])\n                    g['failure_reasons'] = ([\"physical_or_pairing_gate\"] if not g['technical_passed'] else []) + ([\"robot_contact\"] if not g['contact_free'] else [])")
tail="""        assert len(result['rows']) == 12 and sum(len(r['branches']) for r in result['rows']) == 336
        result.update(state='COMPLETE_DATA' if all(r['gates']['passed'] for r in result['rows']) else 'DOMAIN_GATE_FAILED',
                      decision='Complete fixed rollout inventory. Failed domain anchors preserved; no refit or training. Conditional analysis separately.')
        return 0
"""
target=O/'run.py'
with target.open('x',encoding='utf-8') as f:f.write(prefix+tail+suffix)
assert "selection['identification_demos']" not in target.read_text()
assert "np.linalg.lstsq(x, y" not in target.read_text()
assert "for kind in ['Pfull']]" in target.read_text()
py_compile.compile(str(target),doraise=True)
names=['run.py','helpers.py','supervise.py','PROTOCOL.md','selection.json','calibration.json']
manifest={name:hashlib.sha256((O/name).read_bytes()).hexdigest() for name in names}
manifest['worker_builder_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
with (O/'source_hashes.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
print('Frozen domain worker: 12 held-only anchors x 28 branches, no calibration fit or policy updates.')
