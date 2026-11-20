"""Kompakter Lesebericht zu N2-2b (nur Lesen, keine Rechnung, keine Optimizerupdates).

Gibt aus summary.json die Panelkennzahlen je Parent ohne Punktlisten und ECE-Bins aus, dazu die
Vortrainingsmetadaten ohne vollständigen Lossverlauf und die SHA-256 der Abschlussdateien.
Die fachliche Neuberechnung übernimmt `critic_validation_v2.py monitor`.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "praxis/results/critic/three_cube_transfer_v1/critic_validation_n2_2b"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    """Ruft die eingefrorene Abschlussprüfung `verify()` des Laufcodes auf (nur Vorwärtsdurchläufe)."""
    import importlib.util
    import sys
    path = Path(__file__).resolve().with_name("critic_validation_v2.py")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("critic_validation_v2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify()
    print("VERIFY OK | Eingaben, Quellen, Gewichte und Neuberechnung beider Panels stimmen mit summary.json überein")


def main():
    import sys
    if "--verify" in sys.argv[1:]:
        verify()
        return
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    report = dict(decision=summary["decision"], critic_updates_total=summary["critic_updates_total"],
                  new_rollouts=summary["new_rollouts"], rollout_optimizer_updates=summary["rollout_optimizer_updates"],
                  saved_validation_episodes=summary["saved_validation_episodes"],
                  config_sha256=summary["config_sha256"], input_dataset_sha256=summary["input_dataset_sha256"],
                  files_sha256={name: digest(OUT / name) for name in ("summary.json", "config.json")},
                  parents={})
    for parent, entry in summary["assessment"].items():
        meta = summary["pretraining"][parent]
        history = meta["loss_history"]
        panels = {}
        for panel, metrics in entry.items():
            if isinstance(metrics, dict) and "passed" in metrics:
                panels[panel] = {k: v for k, v in metrics.items() if k not in ("points", "records", "ece_bins")}
        report["parents"][parent] = dict(
            passed=entry["passed"], baseline_overall_success_rate=entry["baseline_overall_success_rate"],
            baseline_points=len(entry["baseline_points"]), panels=panels,
            pretraining=dict(updates=meta["updates"], train_episodes=meta["train_episodes"],
                             train_frames=meta["train_frames"], weights_sha256=meta["weights_sha256"],
                             loss_first=history[0] if history else None, loss_last=history[-1] if history else None,
                             loss_windows=len(history), finishing_segment_seconds=meta["finishing_segment_seconds"]))
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
