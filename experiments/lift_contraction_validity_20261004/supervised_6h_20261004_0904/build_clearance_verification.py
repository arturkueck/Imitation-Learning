import shutil
from pathlib import Path
S=Path(__file__).resolve().parent;D=S/'clearance_filter_001';O=D/'query_verification_001';O.mkdir()
shutil.copy2(D/'preflight_003/supervise.py',O/'supervise.py')
