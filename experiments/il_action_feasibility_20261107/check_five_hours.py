"""Read the hour-five decision and independently confirm the first deep worker."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import time

HERE = Path(__file__).resolve().parent


def read(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def inspect(out, config):
    status = read(out / "status.json")
    selection = read(out / "selection.json")
    summary = read(out / "breadth/summary.json")
    names = selection["selected"]
    groups = [config["directions"][name]["group"] for name in names]
    with sqlite3.connect((out / "pairs.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        counts = dict(db.execute("SELECT direction,count(*) FROM pairs WHERE phase='breadth' GROUP BY direction"))
        deep = db.execute("SELECT count(*) FROM pairs WHERE phase='deep1' AND direction=?", (names[0],)).fetchone()[0]
    issues = []
    if set(counts) != set(config["directions"]) or any(counts[n] != summary[n]["families"] for n in counts):
        issues.append("Breitenbericht und gespeicherte Familienzahlen weichen voneinander ab")
    if min(counts.values(), default=0) < config["pilot_families"]:
        issues.append("Mindestens eine Richtung hat weniger als 60 vollständige Familien")
    if groups != ["Einzelaktion", "Bewegungsabschnitt"]:
        issues.append("Die gewählten Kandidaten decken die zwei vorgesehenen Gruppen nicht ab")
    if deep == 0 or status["state"] in {"ERROR", "STOPPED"}:
        issues.append("Erste Vertiefung ohne bestätigten Fortschritt oder Lauf beendet")
    return dict(status="WARNING" if issues else "OK", counts=counts, candidates=names,
                success_changes={n: summary[n]["flips"] for n in counts},
                deep1_completed=deep, issues=issues)


def main(out):
    config = read(HERE / "protocol.json")
    due = read(out / "launch.json")["time"] + 3600 * config["phase_hours"][0]
    while (remaining := due-time.time()) > 0:
        time.sleep(min(60, remaining))
    while True:
        try:
            result = inspect(out, config)
            if result["deep1_completed"]:
                break
        except (OSError, sqlite3.Error, KeyError, ValueError, IndexError) as exc:
            result = dict(status="WARNING", issues=[str(exc)])
        if read(out / "status.json")["state"] in {"ERROR", "STOPPED"} or time.time() >= due+300:
            break
        time.sleep(5)
    result["checked"] = datetime.now().astimezone().isoformat(timespec="seconds")
    temp = out / "kontrolle_5h.tmp"
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(out / "kontrolle_5h.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "night_001")
    main(parser.parse_args().out.resolve())
