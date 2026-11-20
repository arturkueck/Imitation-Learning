"""N2-3: Nur lesende Berichtsausgabe des abgeschlossenen Actor-Critic-Smokes.

Liest summary.json, Stufenbewertungen, Baselines und Laufergebnisse aus
praxis/results/critic/three_cube_transfer_v1/ac_smoke_n2_3/ und gibt eine kompakte
Verlaufstabelle aus (Standard) oder alles als JSON (--full).
Schreibt nichts und startet keine Rollouts oder Updates.

    & praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/ac_smoke_report.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "praxis" / "results" / "critic" / "three_cube_transfer_v1" / "ac_smoke_n2_3"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def full():
    summary = read(OUT / "summary.json")
    report = dict(summary=summary, supervisor=read(OUT / "supervisor_status.json"), worker=read(OUT / "status.json"),
                  baselines={p.parent.name: read(p) for p in sorted((OUT / "baseline").glob("*/result.json"))},
                  runs={p.parent.name: read(p) for p in sorted((OUT / "runs").glob("*/result.json"))})
    json.dump(report, sys.stdout, indent=1, ensure_ascii=True, default=str)


def table():
    summary = read(OUT / "summary.json")
    f = lambda v: f"{v:+.3f}" if isinstance(v, (int, float)) else str(v)
    print("Baseline Parent (Entwicklung, k/20):", summary["parent_development_successes"])
    for stage in summary["stages"]:
        print(f"\nStufe δ_max={stage['delta_max']}: bestanden={stage['passed']} technisch={stage['technical_pass']} "
              f"verloren je Parent (B)={stage['lost_per_parent_both_variants']} gesamt={stage['lost_total']} "
              f"Lesart B={stage['retention_reading_b']} Lesart A={stage['retention_reading_a']}")
        for name, e in stage["runs"].items():
            print(f"  {name}: checks={e['checks']} Q nach Runden={[f(v) for v in e['q_after_rounds']]} "
                  f"Q in Updates inkl. Init={[f(v) for v in e['q_during_updates_incl_init']]} ESS={e['ess_mean']:.1f} "
                  f"Entw. {e['development_successes']}/20 (Parent {e['parent_development_successes']}) "
                  f"verloren={e['lost_parent_successes']} neu={e['new_successes']}")
    print("\nVerlauf je Lauf und Runde:")
    print("lauf | runde | onl.erf | critic_loss | q_upd[min,max] | replay_q[min,max] | probe_parent[min,max] | "
          "probe_actor[min,max] | drift_mean/max | roh_mean/max | w_max | ess")
    for path in sorted((OUT / "runs").glob("*/result.json")):
        r = read(path)
        for h in r["history"]:
            u, d, q = h.get("updates", {}), h["drift"], h.get("replay_q", {})
            print(f"{path.parent.name} | {h['round']} | {h.get('online_successes', '-')} | "
                  f"{u.get('critic_loss_mean', float('nan')):.5f} | [{f(u.get('q_min'))}, {f(u.get('q_max'))}] | "
                  f"[{f(q.get('min'))}, {f(q.get('max'))}] | [{f(d['q_parent_min'])}, {f(d['q_parent_max'])}] | "
                  f"[{f(d['q_actor_min'])}, {f(d['q_actor_max'])}] | {d['mean_xyz']:.4f}/{d['max_xyz']:.4f} | "
                  f"{d['raw_mean_xyz']:.4f}/{d['raw_max_xyz']:.4f} | {f(u.get('weight_max'))} | {f(u.get('ess_mean'))}")
        print(f"{path.parent.name} | Summe | online {r['online_successes']}/{len(r['online'])}, "
              f"{r['online_frames']} Frames | Entw. {r['development_successes']}/{len(r['development'])} | "
              f"Verletzungen {r['bound_violations']} | Updates {r['critic_updates']}/{r['actor_updates']} | "
              f"Rollout {r['rollout_seconds']:.0f} s, Updates {r['update_seconds']:.1f} s")
    print("\nSumme:", {k: summary[k] for k in ("runs", "critic_updates_total", "actor_updates_total", "online_episodes",
                                               "development_episodes", "baseline_episodes", "discarded_partials",
                                               "worker_wall_seconds", "config_sha256")})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    full() if "--full" in sys.argv else table()
