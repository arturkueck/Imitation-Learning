import time,json,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
deadline=json.loads((OUT/'session.json').read_text())['deadline']-240
while time.time()<deadline:
    state=json.loads((OUT/'final_test/status.json').read_text())['state']
    if state in ['COMPLETE','TIME_LIMIT_PARTIAL']:
        subprocess.run([sys.executable,str(OUT/'retreat_ablation.py')],check=True)
        break
    time.sleep(2)
