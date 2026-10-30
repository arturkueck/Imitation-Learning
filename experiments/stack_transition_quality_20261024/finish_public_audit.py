from pathlib import Path
import json,h5py,xml.etree.ElementTree as ET
out=Path('experiments/stack_transition_quality_20261024/web_dataset_audit');report=json.loads((out/'mimicgen_inspection.json').read_text())
with h5py.File(out/'mimicgen_stack_three_source.hdf5','r') as f:
 demo=f['data'][list(f['data'])[0]];xml=demo.attrs['model_file'];xml=xml.decode() if isinstance(xml,bytes) else xml;r=ET.fromstring(xml)
 cubes={}
 for name in ['cubeA','cubeB','cubeC']:
  cubes[name]=[dict(name=g.attrib.get('name'),size=g.attrib.get('size'),type=g.attrib.get('type')) for g in r.iter('geom') if g.attrib.get('name','').startswith(name) and g.attrib.get('type')=='box']
 report['cube_geom_sizes']=cubes
 report['phase_annotations_present']=bool('datagen_info' in demo)
 report['decision']='QUARANTINED_COMPATIBILITY_AUDIT_ONLY; do not mix into B0/B. Different base geometry, rotation action requirements, absent seven-phase labels and different simulator version. A separate retargeting/architecture arm would be required.'
 report['license']='CC-BY-4.0 per official dataset card';report['attribution']='Mandlekar et al., MimicGen, CoRL2023; official amandlek/mimicgen_datasets repository'
 (out/'mimicgen_inspection.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(dict(cube_geometry=cubes,phase_annotations_present=report['phase_annotations_present'])))
