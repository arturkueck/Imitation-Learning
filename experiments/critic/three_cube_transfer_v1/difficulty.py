"""Geometriemerkmale für StackThree vor der ersten Aktion (difficulty_v1).

Nach reset() und sim.forward() die Weltpositionen der Würfelmittelpunkte aus
env.sim.data.body_xpos[env.cube_ids] in Reihenfolge A, B, C und env.table_offset
übergeben. Alle Längen sind Meter. Die Merkmale beschreiben die XY-Projektion
der Startszene. A bleibt die geplante Turmbasis für beide Transporte. Die
Transportstrecke ist die Summe der direkten horizontalen Verschiebungen,
ohne Greiferanflug, Hubhöhe oder Umwege. Der Abstand C–A beschreibt den Weg
zum geplanten Turm, auch wenn die Policy die zweite Platzierung nie erreicht.

Der Freiraum ist der kleinste euklidische Abstand zwischen den Grundflächen
zweier Würfel (null bei Kontakt oder Überlappung). StackThree initialisiert
achsenparallele Würfel mit 0,04 m Kantenlänge. Die Arbeitsraumlage umfasst
die gerichtete Basisposition relativ zur Tischmitte und den größten radialen
Abstand eines Würfelmittelpunkts von dieser Mitte. Grenzen für die
Schwierigkeitsklassen werden in N1-5 aus der Kalibrierung bestimmt.
"""

import math


VERSION = "difficulty_v1"
CUBE_SIDE_M = 0.04


def _xyz(position):
    x, y, z = position
    if not all(math.isfinite(value) for value in (x, y, z)):
        raise ValueError("Jede XYZ-Position muss endlich sein.")
    return float(x), float(y), float(z)


def _footprint_gap(first, second):
    dx = max(0.0, abs(first[0] - second[0]) - CUBE_SIDE_M)
    dy = max(0.0, abs(first[1] - second[1]) - CUBE_SIDE_M)
    return math.hypot(dx, dy)


def initial_features(cube_positions, table_offset):
    """Liefert ein JSON-fähiges Merkmalsprotokoll für genau einen Dreierstart."""
    a, b, c = (_xyz(position)[:2] for position in cube_positions)
    center = _xyz(table_offset)[:2]
    first_leg = math.dist(b, a)
    tower_distance = math.dist(c, a)
    return {
        "version": VERSION,
        "b_to_base_xy_m": first_leg,
        "c_to_tower_xy_m": tower_distance,
        "transport_total_xy_m": first_leg + tower_distance,
        "min_pair_gap_xy_m": min(
            _footprint_gap(a, b), _footprint_gap(a, c), _footprint_gap(b, c)
        ),
        "base_x_from_table_center_m": a[0] - center[0],
        "base_y_from_table_center_m": a[1] - center[1],
        "max_radius_from_table_center_m": max(math.dist(p, center) for p in (a, b, c)),
    }
