"""Reproduce the explicitly exploratory threshold analysis without simulation."""
import hashlib
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
raw = OUT / 'result.json'
result = json.loads(raw.read_text(encoding='utf-8'))
audit = json.loads((OUT / 'verification.json').read_text(encoding='utf-8'))
digest = hashlib.sha256(raw.read_bytes()).hexdigest()
assert result['state'] == 'COMPLETE' and audit['state'] == 'VERIFIED' and audit['result_sha256'] == digest
records = [v for row in result['rows'] for v in row.get('heldout_policy_probes', [])]
groups = {}
for kind in ['Pxyz', 'Pfull']:
    selected = [x for x in records if x['kind'] == kind]
    actual = np.array([x['observed_one_step_ratio'] for x in selected])
    models = {}
    for name in ['I_OLS', 'I_previous_partial', 'new_AB']:
        pred = np.array([x['scores'][name]['predicted_one_step_ratio'] for x in selected])
        observed_pass, predicted_pass = actual < .99, pred < .99
        models[name] = {'observed_below_0_99': int(observed_pass.sum()),
                        'predicted_below_0_99': int(predicted_pass.sum()),
                        'false_pass': int((predicted_pass & ~observed_pass).sum()),
                        'false_penalty': int((~predicted_pass & observed_pass).sum()),
                        'median_absolute_ratio_error': float(np.median(abs(actual - pred))),
                        'median_actual_hinge': float(np.median(np.maximum(0, actual**2 - .99**2))),
                        'median_predicted_hinge': float(np.median(np.maximum(0, pred**2 - .99**2)))}
    groups[kind] = {'n': len(selected), 'observed_ratio_median': float(np.median(actual)),
                    'observed_ratio_min': float(actual.min()), 'observed_ratio_max': float(actual.max()),
                    'models': models}
existing = json.loads((OUT / 'loss_mechanism.json').read_text(encoding='utf-8'))
assert existing['source_result_sha256'] == digest and existing['exploratory_posthoc_threshold_analysis']
assert existing['groups'] == groups
verification = {'state': 'VERIFIED_DERIVATION', 'exploratory_posthoc_analysis': True,
                 'source_result_sha256': digest,
                 'analysis_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 'training_updates': 0, 'groups': groups}
with (OUT / 'loss_derivation_verification.json').open('x', encoding='utf-8') as f:
    json.dump(verification, f, indent=2)
print('Exploratory threshold analysis reproduced exactly; zero simulation or training updates')
