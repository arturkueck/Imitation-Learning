"""No training: verify Windows service-launched process independence."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import independence,save
save(HERE/'independent_probe_result.json',independence())
