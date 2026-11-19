#!/usr/bin/env python3
"""Regenerate data/site-data.js for the static project site.

Reads only versioned project sources (no checkpoints, no raw arrays):
  experiments/HYPOTHESENJOURNAL.md
  sites/research-atlas-source/public/curriculum-evidence/conclusion.json
  sites/research-atlas-source/public/curriculum-evidence/results.json

Usage (from anywhere):
  python sites/atlas-pages/tools/build_data.py [--repo-url https://github.com/<user>/<repo>]

--repo-url turns journal evidence paths into links to the repository on GitHub.
Without it, evidence is shown as plain paths (safe when the repo stays private).
"""
import argparse, json, re, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent.parent  # repository root

JOURNAL = ROOT / "experiments" / "HYPOTHESENJOURNAL.md"
EVIDENCE = ROOT / "sites" / "research-atlas-source" / "public" / "curriculum-evidence"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE = re.compile(r"`([^`]+)`")

STATUS_MAP = {  # German journal status -> (key, English label)
    "gestützt": ("supported", "Supported"),
    "gestützt im entwicklungspanel": ("supported", "Supported (dev panel)"),
    "teilweise gestützt": ("partial", "Partly supported"),
    "nicht gestützt": ("refuted", "Not supported"),
    "uneindeutig": ("unclear", "Inconclusive"),
    "diagnose": ("diagnosis", "Diagnosis"),
    "technisch bestanden": ("passed", "Technical gate passed"),
    "technisch gestoppt": ("stopped", "Technical stop"),
    "am gate gestoppt": ("stopped", "Stopped at gate"),
    "geplant": ("planned", "Planned"),
    "gestartet": ("running", "Started"),
    "pausiert": ("paused", "Paused"),
    "dokumentiert": ("documented", "Documented"),
}
FAMILY = {"BASE": "Baselines", "DIAG": "Diagnosis", "BC": "Behavior Cloning",
          "SI": "Self-imitation", "VIS": "Vision", "AC": "Actor–Critic"}


def parse_journal(repo_url):
    rows = []
    for line in JOURNAL.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| 2026"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 9:
            continue
        when, hid, topic, question, test, result, status, decision, evidence = cells
        links = []
        for text, href in LINK.findall(evidence):
            path = "experiments/" + href if not href.startswith(("http", "../")) else href.replace("../", "")
            links.append({"label": text, "path": path,
                          "url": f"{repo_url}/blob/main/{path}" if repo_url and not href.startswith("http") else (href if href.startswith("http") else None)})
        for ref in CODE.findall(evidence):
            if ":" in ref:
                commit, path = ref.split(":", 1)
                links.append({"label": path.split("/")[-1], "path": ref,
                              "url": f"{repo_url}/blob/{commit}/{path}" if repo_url else None})
            elif not any(ref in l["path"] for l in links):
                links.append({"label": "commit " + ref, "path": ref,
                              "url": f"{repo_url}/commit/{ref}" if repo_url else None})
        skey, slabel = STATUS_MAP.get(status.lower(), ("other", status))
        prefix = hid.split("-")[0] if hid != "—" else ""
        rows.append({"when": when, "date": when[:10], "id": hid, "family": FAMILY.get(prefix, "Project"),
                     "topic": topic, "question": question, "test": test, "result": result,
                     "status": skey, "statusLabel": slabel, "statusRaw": status,
                     "decision": decision, "evidence": links})
    return rows


def frac(d):
    return [d["successes"], d["n"]]


def results():
    c = json.loads((EVIDENCE / "conclusion.json").read_text(encoding="utf-8"))
    r = json.loads((EVIDENCE / "results.json").read_text(encoding="utf-8"))
    abc = {}
    for key, v in c["abc"]["models"].items():
        arm, seed = key.split("_")
        abc.setdefault(arm, {})[seed] = {"three": frac(v["3"]), "two": frac(v["2"])}
    conf = c["training"]["summary"]["confirmation"]
    arms = ["baseline", "replay", "action", "completion", "combined"]
    correction = {a: {"total": [sum(m[a]["successes"] for m in conf.values()), sum(m[a]["n"] for m in conf.values())],
                      "perSeed": [frac(conf[k][a]) for k in sorted(conf)]} for a in arms}
    dev = c["training"]["summary"]["development"]
    correction_dev = {a: [sum(m[a]["successes"] for m in dev.values()), sum(m[a]["n"] for m in dev.values())] for a in arms}
    ablation = {k: {"success": [v["successes"], v["n"]], "gains": v["gains"], "losses": v["losses"]}
                for k, v in c["ablation"].items()}
    clock = [{"model": k, "before": v["3"]["original_successes"], "after": v["3"]["bounded_successes"],
              "n": v["3"]["n"], "gains": v["3"]["gains"], "losses": v["3"]["losses"]}
             for k, v in r["clockConfirmation"]["models"].items()]
    return {"abc": abc, "correction": correction, "correctionDev": correction_dev,
            "grasp": c["grasp"], "ablation": ablation, "dataset": c["dataset"],
            "clock": clock, "clockHeadline": r["clockHeadline"], "limits": c["limits"],
            "updated": c["updated"],
            "provenance": {k: v["sha256"][:12] for k, v in c["provenance"].items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-url", default="")
    a = ap.parse_args()
    data = {"generated": datetime.date.today().isoformat(),
            "journal": parse_journal(a.repo_url.rstrip("/")),
            "results": results()}
    out = SITE / "data" / "site-data.js"
    out.write_text("// Generated by tools/build_data.py - do not edit by hand.\nwindow.SITE_DATA = "
                   + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"wrote {out} · {len(data['journal'])} journal entries")


if __name__ == "__main__":
    main()
