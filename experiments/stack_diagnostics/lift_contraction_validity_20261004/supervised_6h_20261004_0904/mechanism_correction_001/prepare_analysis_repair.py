from pathlib import Path
p = Path(__file__).resolve().parent
old = p/'analysis_repair_001'
(old/'FAILED.txt').write_text('First independent audit rejected an assumed float32 policy action (max ratio discrepancy 1.65e-8). Stored full action values retain float64 precision. No simulation or training repeated; no derived result written. Original audit code preserved.\n', encoding='utf-8')
new = p/'analysis_repair_002'
new.mkdir()
text = (old/'analyze.py').read_text(encoding='utf-8')
text = text.replace("np.array(common['base_policy_action'], dtype=np.float32)", "np.array(common['base_policy_action'])")
text = text.replace("np.array(ref['action'], dtype=np.float32)", "np.array(ref['action'])")
(new/'analyze.py').write_text(text, encoding='utf-8')
