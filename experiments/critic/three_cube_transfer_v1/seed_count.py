"""B-3: Werkzeug für N4-2, Seedzahl des Hauptvergleichs (AGENTS.md §1, PROTOCOL.md §10).

Das Skript rechnet nur mit übergebenen Zahlen oder mit der Ausgabe von ``pilot_analysis.py``
(``pilot_analysis_v1``). Es startet keine Simulation, lädt keine Modelle, liest keine Rohdaten und
führt keine Optimizerupdates aus. Panels mit Testfamilien werden abgewiesen.

Planungsmodell (vor Sicht auf Pilotdaten festgelegt):

* Einheit ist der unabhängige Trainingsseed, also ein neuer BC-Parent mit seinen gepaarten Armen.
  Je Seed wird der primäre Kontrast d_i = Erfolgsquote(AC-IL) − Erfolgsquote(AC-neu) gebildet.
  Geplant wird für einen zweiseitigen gepaarten t-Test über die Seeds beziehungsweise für ein
  t-Intervall des mittleren Kontrasts. Szenen- und Seedunsicherheit stecken beide in der Streuung
  der d_i. Ein Familienbootstrap allein deckt die Seedstreuung nicht ab (AGENTS.md §3).
* Kleinster relevanter Effekt δ = 0,10 (10 Prozentpunkte, PROTOCOL.md §10), α = 0,05 zweiseitig,
  Teststärke 0,80. Abweichende Werte müssen in N4-2 begründet werden.
* Planungsstreuung σ_plan = max(σ_oben, σ_Szene).
  σ_oben ist die einseitige obere 80-%-Konfidenzgrenze der Pilot-Standardabweichung
  s · sqrt(df / χ²_{0,20; df}) mit df = Zahl der Pilotseeds − 1. Bei drei Pilotseeds (df = 2) ist s
  sehr unsicher, deshalb wird nicht mit dem Punktwert geplant. Der Punktwert wird mitberichtet.
  σ_Szene = sqrt(q / N) ist die Szenenstreuung eines gepaarten Quotenunterschieds auf N
  Auswertungsfamilien bei Diskordanzrate q (Anteil Familien, in denen genau ein Arm erfolgreich ist).
  Sie ist eine Untergrenze, damit ein zufällig kleines Pilot-s nicht zu wenige Seeds ergibt.
* Mindestzahl 4 (mehr als drei Seeds, AGENTS.md §1). Erforderlich ist
  n = max(4, n_Teststärke, n_Präzision). Reicht das Budget nicht, wird keine kleinere Zahl
  empfohlen. Das Werkzeug meldet dann Teststärke, Intervallbreite und den kleinsten nachweisbaren
  Effekt bei der bezahlbaren Seedzahl, und der Nutzer entscheidet.

Ohne scipy: t-, χ²- und Normalverteilung sowie die exakte Teststärke über die nichtzentrale
t-Verteilung (numerische Integration über die χ-Verteilung) sind hier implementiert und in
``test_seed_count.py`` gegen Tabellenwerte und Monte-Carlo geprüft.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

TOOL_VERSION = "seed_count_v1"
OUTPUT_SCHEMA = "three_cube_transfer_v1.seed_count.v1"
PILOT_ANALYSIS_VERSION = "pilot_analysis_v1"
PRIMARY_CONTRAST = ("AC-IL", "AC-neu", "validation_normal")

MIN_SEEDS = 4                 # AGENTS.md §1: mehr als drei
DEFAULT_DELTA = 0.10          # PROTOCOL.md §10
DEFAULT_ALPHA = 0.05          # zweiseitig
DEFAULT_POWER = 0.80
DEFAULT_SD_CONFIDENCE = 0.80  # einseitige obere Grenze der Pilot-SD
N_MAX = 10_000
GRID_POINTS = 20_000

EXAMPLE_SDS = (0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25)
EXAMPLE_LABEL = "Beispielwerte zur Planung, keine Pilotdaten"


class InputError(ValueError):
    """Ungültige oder unzulässige Eingabe."""


class TestFamilyError(InputError):
    """Eingabe bezieht sich auf Testfamilien."""


# --------------------------------------------------------------------------- Verteilungen

def norm_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _bisect(f, target, lo, hi, iters=200):
    """Monotone wachsende f: x mit f(x) = target in [lo, hi]."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def norm_ppf(p):
    _check_prob(p)
    return _bisect(norm_cdf, p, -40.0, 40.0)


def _betacf(a, b, x):
    """Kettenbruch der unvollständigen Betafunktion (modifizierter Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            return h
    raise ArithmeticError("Kettenbruch der Betafunktion konvergiert nicht")


def betainc(a, b, x):
    """Regularisierte unvollständige Betafunktion I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    _check_df(df)
    x = df / (df + t * t)
    tail = 0.5 * betainc(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def t_ppf(p, df):
    _check_prob(p)
    _check_df(df)
    return _bisect(lambda t: t_cdf(t, df), p, -1e7, 1e7, iters=300)


def gammainc_lower(a, x):
    """Regularisierte untere unvollständige Gammafunktion P(a, x)."""
    if x <= 0.0:
        return 0.0
    gln = math.lgamma(a)
    if x < a + 1.0:
        ap, total, term = a, 1.0 / a, 1.0 / a
        for _ in range(10_000):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-16:
                return total * math.exp(-x + a * math.log(x) - gln)
        raise ArithmeticError("Gammareihe konvergiert nicht")
    tiny = 1e-300
    b = x + 1.0 - a
    c, d = 1.0 / tiny, 1.0 / b
    h = d
    for i in range(1, 10_000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            return 1.0 - math.exp(-x + a * math.log(x) - gln) * h
    raise ArithmeticError("Gammakettenbruch konvergiert nicht")


def chi2_cdf(x, df):
    _check_df(df)
    return gammainc_lower(df / 2.0, x / 2.0)


def chi2_ppf(p, df):
    _check_prob(p)
    _check_df(df)
    hi = df + 100.0 * math.sqrt(2.0 * df) + 100.0
    return _bisect(lambda x: chi2_cdf(x, df), p, 0.0, hi, iters=300)


def _check_prob(p):
    if not (0.0 < p < 1.0):
        raise InputError(f"Wahrscheinlichkeit muss in (0, 1) liegen: {p}")


def _check_df(df):
    if not (df > 0 and math.isfinite(df)):
        raise InputError(f"Freiheitsgrade müssen positiv sein: {df}")


# --------------------------------------------------------------------------- Teststärke und Präzision

def paired_t_power(n, delta, sd, alpha=DEFAULT_ALPHA):
    """Exakte Teststärke des zweiseitigen gepaarten t-Tests mit n Seeds (nichtzentrales t).

    T = (Z + λ) / U mit λ = δ·sqrt(n)/σ, U = sqrt(V/ν), V ~ χ²_ν, ν = n − 1.
    Integriert wird über die Dichte von U auf einem Mittelpunktgitter.
    """
    _check_planning(delta, sd, alpha)
    if n < 2:
        raise InputError("Für einen gepaarten t-Test sind mindestens 2 Seeds nötig")
    nu = n - 1
    lam = delta * math.sqrt(n) / sd
    crit = t_ppf(1.0 - alpha / 2.0, nu)
    upper = 1.0 + 20.0 / math.sqrt(2.0 * nu) + 2.0
    h = upper / GRID_POINTS
    u = (np.arange(GRID_POINTS) + 0.5) * h
    v = nu * u * u
    half = nu / 2.0
    log_dens = (math.log(2.0 * nu) + np.log(u) + (half - 1.0) * np.log(v) - v / 2.0
                - half * math.log(2.0) - math.lgamma(half))
    w = np.exp(log_dens)
    w /= w.sum()
    z_hi = crit * u - lam
    z_lo = -crit * u - lam
    r2 = math.sqrt(2.0)
    p_hi = 0.5 * np.array([math.erfc(z / r2) for z in z_hi])      # P(Z > z_hi)
    p_lo = 0.5 * np.array([math.erfc(-z / r2) for z in z_lo])     # P(Z < z_lo)
    return float(np.dot(w, p_hi + p_lo))


def n_for_power(delta, sd, alpha=DEFAULT_ALPHA, power=DEFAULT_POWER, n_max=N_MAX):
    """Kleinste Seedzahl n ≥ 2 mit Teststärke ≥ power. None, wenn n_max nicht genügt."""
    _check_prob(power)
    if power <= alpha / 2.0:
        raise InputError("Ziel-Teststärke muss über α/2 liegen")
    # Normalapproximation als Startpunkt, danach exakt nach unten und oben prüfen.
    z = norm_ppf(1.0 - alpha / 2.0) + norm_ppf(power)
    n = max(2, int(math.floor((z * sd / delta) ** 2)) - 2)
    while n > 2 and paired_t_power(n - 1, delta, sd, alpha) >= power:
        n -= 1
    while n <= n_max:
        if paired_t_power(n, delta, sd, alpha) >= power:
            return n
        n += 1
    return None


def ci_halfwidth(n, sd, alpha=DEFAULT_ALPHA):
    """Halbe Breite des (1 − α)-t-Intervalls für den mittleren Kontrast bei Streuung sd."""
    if n < 2:
        raise InputError("Für ein t-Intervall sind mindestens 2 Seeds nötig")
    if not (sd > 0 and math.isfinite(sd)):
        raise InputError(f"Streuung muss positiv sein: {sd}")
    return t_ppf(1.0 - alpha / 2.0, n - 1) * sd / math.sqrt(n)


def n_for_precision(halfwidth, sd, alpha=DEFAULT_ALPHA, n_max=N_MAX):
    """Kleinste Seedzahl, deren erwartete Intervallhalbbreite ≤ halfwidth ist."""
    if not (halfwidth > 0 and math.isfinite(halfwidth)):
        raise InputError(f"Zielhalbbreite muss positiv sein: {halfwidth}")
    for n in range(2, n_max + 1):
        if ci_halfwidth(n, sd, alpha) <= halfwidth:
            return n
    return None


def min_detectable_effect(n, sd, alpha=DEFAULT_ALPHA, power=DEFAULT_POWER):
    """Kleinster Effekt, der mit n Seeds die Ziel-Teststärke erreicht."""
    if n < 2:
        raise InputError("Mindestens 2 Seeds nötig")
    return _bisect(lambda d: paired_t_power(n, d, sd, alpha), power, 1e-9, 50.0 * sd, iters=80)


def _check_planning(delta, sd, alpha):
    if not (delta > 0 and math.isfinite(delta)):
        raise InputError(f"Effekt δ muss positiv sein: {delta}")
    if not (sd > 0 and math.isfinite(sd)):
        raise InputError(f"Streuung σ muss positiv sein: {sd}")
    if not (0.0 < alpha < 1.0):
        raise InputError(f"α muss in (0, 1) liegen: {alpha}")


# --------------------------------------------------------------------------- Streuung

def pilot_sd(differences):
    """Stichproben-Standardabweichung (ddof = 1) der Pilotkontraste je Seed und Freiheitsgrade."""
    values = [float(d) for d in differences]
    if len(values) < 2:
        raise InputError("Mindestens zwei Pilotkontraste nötig")
    for d in values:
        if not math.isfinite(d) or abs(d) > 1.0:
            raise InputError(f"Pilotkontrast außerhalb [−1, 1] oder nicht endlich: {d}")
    s = float(np.std(values, ddof=1))
    if s < 1e-12:  # Gleitkommarest identischer Kontraste ist keine Streuung
        s = 0.0
    return s, len(values) - 1


def sd_upper_limit(s, df, confidence=DEFAULT_SD_CONFIDENCE):
    """Einseitige obere Konfidenzgrenze von σ: s · sqrt(df / χ²_{1−conf; df})."""
    if not (s >= 0 and math.isfinite(s)):
        raise InputError(f"Standardabweichung ungültig: {s}")
    _check_prob(confidence)
    return s * math.sqrt(df / chi2_ppf(1.0 - confidence, df))


def scene_sd_floor(n_families, discordance_rate):
    """Szenenstreuung eines gepaarten Quotenunterschieds: sqrt(q / N).

    Var(d̂ | Seed) = (q − Δ²) / N ≤ q / N. Die Untergrenze ist deshalb leicht konservativ.
    """
    if not (isinstance(n_families, int) and n_families > 0):
        raise InputError(f"Familienzahl muss eine positive ganze Zahl sein: {n_families}")
    if not (0.0 <= discordance_rate <= 1.0):
        raise InputError(f"Diskordanzrate muss in [0, 1] liegen: {discordance_rate}")
    return math.sqrt(discordance_rate / n_families)


# --------------------------------------------------------------------------- Budget

def cost_per_seed(components):
    """Summe der Kosten je Seed in Stunden. components: {Name: Stunden}."""
    if not components:
        raise InputError("Mindestens ein Kostenbestandteil je Seed nötig")
    total = 0.0
    for name, hours in components.items():
        if not (hours >= 0 and math.isfinite(hours)):
            raise InputError(f"Kosten für {name!r} ungültig: {hours}")
        total += hours
    if total <= 0:
        raise InputError("Kosten je Seed müssen positiv sein")
    return total


def affordable_seeds(budget_hours, per_seed_hours, fixed_hours=0.0):
    """Größte Seedzahl, deren Gesamtkosten fixed + n · per_seed ≤ budget sind."""
    for name, value in (("Budget", budget_hours), ("Fixkosten", fixed_hours)):
        if not (value >= 0 and math.isfinite(value)):
            raise InputError(f"{name} ungültig: {value}")
    if not (per_seed_hours > 0 and math.isfinite(per_seed_hours)):
        raise InputError(f"Kosten je Seed müssen positiv sein: {per_seed_hours}")
    remaining = budget_hours - fixed_hours
    if remaining < 0:
        return 0
    return int(math.floor(remaining / per_seed_hours + 1e-12))


# --------------------------------------------------------------------------- Pilotauswertung lesen

def read_pilot_analysis(result):
    """Primärkontraste je Parent und Diskordanzrate aus einer pilot_analysis_v1-Ausgabe."""
    if result.get("analysis_version") != PILOT_ANALYSIS_VERSION:
        raise InputError(f"Erwartet analysis_version {PILOT_ANALYSIS_VERSION}, "
                         f"gefunden {result.get('analysis_version')!r}")
    for key in result.get("panel_sizes", {}):
        if str(key).startswith("test"):
            raise TestFamilyError(f"Pilotauswertung enthält Testpanel {key!r}")
    arm_a, arm_b, panel = PRIMARY_CONTRAST
    for contrast in result.get("contrasts", []):
        if str(contrast.get("panel", "")).startswith("test"):
            raise TestFamilyError(f"Kontrast auf Testpanel {contrast.get('panel')!r}")
    matches = [c for c in result.get("contrasts", [])
               if c.get("arm_a") == arm_a and c.get("arm_b") == arm_b and c.get("panel") == panel]
    if len(matches) != 1:
        raise InputError("Primärkontrast AC-IL − AC-neu auf validation_normal nicht eindeutig gefunden")
    primary = matches[0]
    per_parent = primary["per_parent"]
    diffs, rates = [], []
    for row in per_parent:
        dis = row["discordant"]
        n = int(row["n"])
        if n <= 0 or dis["only_a"] + dis["only_b"] + dis["both"] + dis["neither"] != n:
            raise InputError(f"Diskordanztabelle von Parent {row.get('parent')} passt nicht zu n = {n}")
        diffs.append(float(row["difference"]))
        rates.append((dis["only_a"] + dis["only_b"]) / n)
    return {
        "differences": diffs,
        "parents": [row["parent"] for row in per_parent],
        "discordance_rate": float(np.mean(rates)),
        "discordance_rate_per_parent": rates,
        "n_families_pilot": int(per_parent[0]["n"]),
        "any_aborted": bool(primary.get("any_aborted", False)),
    }


# --------------------------------------------------------------------------- Plan

def plan(*, delta=DEFAULT_DELTA, alpha=DEFAULT_ALPHA, power=DEFAULT_POWER,
         pilot_differences=None, sd_assumed=None, sd_confidence=DEFAULT_SD_CONFIDENCE,
         eval_families=None, discordance_rate=None, target_halfwidth=None,
         cost_components=None, budget_hours=None, fixed_hours=0.0, source=None):
    """Seedzahl nach der Regel im Modulkopf. Gibt ein JSON-fähiges Ergebnis zurück."""
    _check_planning(delta, 1.0, alpha)
    _check_prob(power)
    if (pilot_differences is None) == (sd_assumed is None):
        raise InputError("Genau eine Streuungsquelle angeben: Pilotkontraste oder angenommene σ")

    spread = {"confidence_upper": sd_confidence}
    if pilot_differences is not None:
        s, df = pilot_sd(pilot_differences)
        upper = sd_upper_limit(s, df, sd_confidence)
        spread.update({"source": "Pilotkontraste je Seed", "pilot_differences": list(map(float, pilot_differences)),
                       "sd_point": s, "df": df, "sd_upper": upper})
        candidate = upper
    else:
        if not (sd_assumed > 0 and math.isfinite(sd_assumed)):
            raise InputError(f"Angenommene σ muss positiv sein: {sd_assumed}")
        spread.update({"source": "Annahme", "sd_point": float(sd_assumed), "df": None, "sd_upper": None})
        candidate = float(sd_assumed)

    if (eval_families is None) != (discordance_rate is None):
        raise InputError("Für die Szenenuntergrenze Familienzahl und Diskordanzrate gemeinsam angeben")
    floor = scene_sd_floor(eval_families, discordance_rate) if eval_families is not None else None
    sd_plan = max(candidate, floor) if floor is not None else candidate
    if not sd_plan > 0:
        raise InputError("Planungsstreuung ist 0. Szenenuntergrenze angeben (Familien und Diskordanzrate).")
    spread.update({"scene_floor": floor, "eval_families": eval_families, "discordance_rate": discordance_rate,
                   "sd_plan": sd_plan, "floor_binding": floor is not None and floor > candidate})

    n_power = n_for_power(delta, sd_plan, alpha, power)
    n_power_point = (n_for_power(delta, spread["sd_point"], alpha, power)
                     if spread["sd_point"] > 0 else None)
    n_precision = n_for_precision(target_halfwidth, sd_plan, alpha) if target_halfwidth is not None else None
    if n_power is None or (target_halfwidth is not None and n_precision is None):
        raise InputError(f"Mehr als {N_MAX} Seeds nötig, Planung nicht sinnvoll")
    n_required = max([MIN_SEEDS, n_power] + ([n_precision] if n_precision is not None else []))

    out = {
        "schema": OUTPUT_SCHEMA,
        "tool_version": TOOL_VERSION,
        "tool_sha256": _self_sha256(),
        "source": source,
        "unit": "unabhängiger Trainingsseed (neuer BC-Parent mit gepaarten Armen)",
        "contrast": "AC-IL − AC-neu je Seed (primär, PROTOCOL.md §10)",
        "test": "zweiseitiger gepaarter t-Test über Seeds, exakte Teststärke (nichtzentrales t)",
        "inputs": {"delta": delta, "alpha": alpha, "power": power, "target_halfwidth": target_halfwidth},
        "spread": spread,
        "n_min_rule": MIN_SEEDS,
        "n_power": n_power,
        "n_power_at_sd_point": n_power_point,
        "n_precision": n_precision,
        "n_required": n_required,
        "at_required": {"power": paired_t_power(n_required, delta, sd_plan, alpha),
                        "ci_halfwidth": ci_halfwidth(n_required, sd_plan, alpha)},
        "limits": [
            "Pilot-σ aus wenigen Seeds ist sehr unsicher, geplant wird mit der oberen Grenze.",
            "Die Pilotparents teilen Szenen. Ihre Kontraste sind keine unabhängigen Szenenstichproben.",
            "Planungsrechnung, kein Wirksamkeitsnachweis.",
        ],
    }

    if cost_components is not None or budget_hours is not None:
        if cost_components is None or budget_hours is None:
            raise InputError("Für die Budgetprüfung Kosten je Seed und Budget gemeinsam angeben")
        per_seed = cost_per_seed(cost_components)
        n_budget = affordable_seeds(budget_hours, per_seed, fixed_hours)
        budget = {"cost_components_hours": dict(cost_components), "cost_per_seed_hours": per_seed,
                  "fixed_hours": fixed_hours, "budget_hours": budget_hours, "n_affordable": n_budget,
                  "cost_at_required_hours": fixed_hours + n_required * per_seed}
        if n_budget >= n_required:
            out["decision"] = "machbar"
            out["n_recommended"] = n_required
        else:
            out["decision"] = "Budget reicht nicht"
            out["n_recommended"] = None
            out["user_decision_required"] = (
                "Budget erhöhen oder Effekt/Teststärke begründet ändern. Keine stille Reduktion der "
                "Seedzahl (AGENTS.md §1).")
            if n_budget >= 2:
                budget["at_affordable"] = {
                    "power": paired_t_power(n_budget, delta, sd_plan, alpha),
                    "ci_halfwidth": ci_halfwidth(n_budget, sd_plan, alpha),
                    "min_detectable_effect": min_detectable_effect(n_budget, sd_plan, alpha, power),
                    "below_min_rule": n_budget < MIN_SEEDS,
                }
        out["budget"] = budget
    else:
        out["decision"] = "ohne Budgetprüfung"
        out["n_recommended"] = n_required

    table_max = min(max(n_required, out.get("budget", {}).get("n_affordable", 0), 12), 40)
    out["power_table"] = [{"n": n, "power": paired_t_power(n, delta, sd_plan, alpha),
                           "ci_halfwidth": ci_halfwidth(n, sd_plan, alpha)}
                          for n in range(MIN_SEEDS, table_max + 1)]
    return out


def example_grid(delta=DEFAULT_DELTA, alpha=DEFAULT_ALPHA, power=DEFAULT_POWER, sds=EXAMPLE_SDS):
    """Planungstabelle über angenommene σ. Ausdrücklich Beispielwerte, keine Pilotdaten."""
    rows = []
    for sd in sds:
        n_power = n_for_power(delta, sd, alpha, power)
        n_req = max(MIN_SEEDS, n_power)
        rows.append({"sd": sd, "n_power": n_power, "n_required": n_req,
                     "power_at_required": paired_t_power(n_req, delta, sd, alpha),
                     "ci_halfwidth_at_required": ci_halfwidth(n_req, sd, alpha),
                     "pilot_sd_reaching_this_upper": sd / math.sqrt(2.0 / chi2_ppf(1.0 - DEFAULT_SD_CONFIDENCE, 2))})
    return {"schema": OUTPUT_SCHEMA, "tool_version": TOOL_VERSION, "tool_sha256": _self_sha256(),
            "label": EXAMPLE_LABEL, "delta": delta, "alpha": alpha, "power": power, "rows": rows}


def _self_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- Ausgabe

def _fmt(x, digits=3):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def render_plan(result):
    sp = result["spread"]
    lines = [f"# Seedzahl ({result['tool_version']})", "",
             f"Quelle: {result['source'] or sp['source']}",
             f"δ = {_fmt(result['inputs']['delta'], 2)}, α = {_fmt(result['inputs']['alpha'], 2)} zweiseitig, "
             f"Teststärke {_fmt(result['inputs']['power'], 2)}", "",
             f"σ Punkt {_fmt(sp['sd_point'])}, σ obere {int(sp['confidence_upper'] * 100)}-%-Grenze "
             f"{_fmt(sp['sd_upper'])}, Szenenuntergrenze {_fmt(sp['scene_floor'])}, Planung {_fmt(sp['sd_plan'])}",
             f"n Teststärke {result['n_power']} (bei σ Punkt {result['n_power_at_sd_point']}), "
             f"n Präzision {result['n_precision'] if result['n_precision'] is not None else '–'}, "
             f"Mindestregel {result['n_min_rule']} → erforderlich {result['n_required']}",
             f"Entscheidung: {result['decision']}, empfohlen {result['n_recommended'] or '–'}"]
    if "budget" in result:
        b = result["budget"]
        lines.append(f"Budget: {_fmt(b['cost_per_seed_hours'], 2)} h je Seed, Fixkosten {_fmt(b['fixed_hours'], 2)} h, "
                     f"Budget {_fmt(b['budget_hours'], 2)} h → bezahlbar {b['n_affordable']} Seeds")
        if "at_affordable" in b:
            a = b["at_affordable"]
            lines.append(f"Bei {b['n_affordable']} Seeds: Teststärke {_fmt(a['power'])}, Halbbreite "
                         f"{_fmt(a['ci_halfwidth'])}, kleinster nachweisbarer Effekt {_fmt(a['min_detectable_effect'])}")
        if result.get("user_decision_required"):
            lines.append(f"Nutzerentscheidung: {result['user_decision_required']}")
    lines += ["", "| n | Teststärke | 95-%-Halbbreite |", "|---:|---:|---:|"]
    lines += [f"| {r['n']} | {_fmt(r['power'])} | {_fmt(r['ci_halfwidth'])} |" for r in result["power_table"]]
    return "\n".join(lines)


def render_example(grid):
    lines = [f"# Planungstabelle ({grid['tool_version']}), {grid['label']}", "",
             f"δ = {_fmt(grid['delta'], 2)}, α = {_fmt(grid['alpha'], 2)} zweiseitig, Teststärke {_fmt(grid['power'], 2)}",
             "", "| σ_plan | n Teststärke | n erforderlich (≥ 4) | Teststärke dort | 95-%-Halbbreite dort | "
             "Pilot-s mit dieser oberen Grenze (3 Seeds) |", "|---:|---:|---:|---:|---:|---:|"]
    for r in grid["rows"]:
        lines.append(f"| {_fmt(r['sd'], 2)} | {r['n_power']} | {r['n_required']} | {_fmt(r['power_at_required'])} | "
                     f"{_fmt(r['ci_halfwidth_at_required'])} | {_fmt(r['pilot_sd_reaching_this_upper'])} |")
    return "\n".join(lines)


def _parse_components(items):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise InputError(f"Kostenbestandteil als name=stunden angeben: {item!r}")
        name, value = item.split("=", 1)
        if name in out:
            raise InputError(f"Kostenbestandteil doppelt: {name!r}")
        out[name] = float(value)
    return out or None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("example", help="Planungstabelle über angenommene σ (Beispielwerte)")
    ex.add_argument("--json", action="store_true")

    pl = sub.add_parser("plan", help="Seedzahl aus Effekt, Streuung und Budget")
    src = pl.add_mutually_exclusive_group(required=True)
    src.add_argument("--pilot-analysis", type=Path, help="Ausgabe von pilot_analysis.py (pilot_analysis_v1)")
    src.add_argument("--pilot-differences", type=float, nargs="+", help="Primärkontraste je Pilotseed")
    src.add_argument("--sd", type=float, help="angenommene Streuung der Kontraste je Seed")
    pl.add_argument("--delta", type=float, default=DEFAULT_DELTA)
    pl.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    pl.add_argument("--power", type=float, default=DEFAULT_POWER)
    pl.add_argument("--sd-confidence", type=float, default=DEFAULT_SD_CONFIDENCE)
    pl.add_argument("--eval-families", type=int, help="Familien je Seed im Hauptvergleichspanel")
    pl.add_argument("--discordance-rate", type=float, help="Anteil diskordanter Familien (überschreibt Pilotwert)")
    pl.add_argument("--target-halfwidth", type=float)
    pl.add_argument("--cost", action="append", metavar="NAME=STUNDEN", help="Kostenbestandteil je Seed")
    pl.add_argument("--budget-hours", type=float)
    pl.add_argument("--fixed-hours", type=float, default=0.0)
    pl.add_argument("--out", type=Path, help="JSON-Ausgabe")
    pl.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        if args.cmd == "example":
            grid = example_grid()
            print(json.dumps(grid, ensure_ascii=False, indent=1) if args.json else render_example(grid))
            return 0
        diffs, dis, source = args.pilot_differences, args.discordance_rate, None
        if args.pilot_analysis is not None:
            raw = args.pilot_analysis.read_bytes()
            pilot = read_pilot_analysis(json.loads(raw))
            diffs = pilot["differences"]
            dis = pilot["discordance_rate"] if dis is None else dis
            source = {"pilot_analysis": str(args.pilot_analysis), "sha256": hashlib.sha256(raw).hexdigest(),
                      "parents": pilot["parents"], "discordance_rate_pilot": pilot["discordance_rate"],
                      "n_families_pilot": pilot["n_families_pilot"], "any_aborted": pilot["any_aborted"]}
        result = plan(delta=args.delta, alpha=args.alpha, power=args.power, pilot_differences=diffs,
                      sd_assumed=args.sd, sd_confidence=args.sd_confidence, eval_families=args.eval_families,
                      discordance_rate=dis, target_halfwidth=args.target_halfwidth,
                      cost_components=_parse_components(args.cost), budget_hours=args.budget_hours,
                      fixed_hours=args.fixed_hours, source=source)
    except InputError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else render_plan(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
