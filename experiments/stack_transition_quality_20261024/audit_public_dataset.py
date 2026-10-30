from pathlib import Path
import urllib.request,json
out=Path('experiments/stack_transition_quality_20261024/web_dataset_audit');out.mkdir(exist_ok=True)
url='https://huggingface.co/api/datasets/amandlek/mimicgen_datasets/tree/main/source?limit=100'
with urllib.request.urlopen(url,timeout=30) as response:data=json.load(response)
(out/'mimicgen_source_listing.json').write_text(json.dumps(data,indent=2))
print(json.dumps([r for r in data if 'stack' in r.get('path','')],indent=2))
