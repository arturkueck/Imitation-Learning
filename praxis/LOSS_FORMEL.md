# Die Self-Imitation-Formel im Code

Die Formel aus dem Projektvorschlag ist ein geplantes Lernverfahren. Vorhanden
sind ein gewichteter BC-Pilot und eine separate Critic-Machbarkeitspruefung.
Diese Bausteine bilden noch keine durchgaengige Critic-gewichtete Lernschleife.
Die folgenden Verweise beziehen sich auf den aktuellen Arbeitscode, nicht auf
eingefrorene Quellen historischer Laeufe.

## Symbole und Daten

| Formel | Aktueller Code | Bedeutung |
|---|---|---|
| pi_theta(x_t) | `pred` aus `PhaseNet.forward(x, phase)` | Vorhergesagte Aktion der trainierten Policy |
| a_t | `a` im Trainingsbatch | Gespeicherte Zielaktion; bei Originaldaten Demoaktion, bei eigenen Daten ausgefuehrte Aktion |
| x_t | `x` | Zehn Zustandsmerkmale; die Phase wird zusaetzlich uebergeben |
| tau | Abschnitt mit `source`, `start`, `end` | Zusammenhaengender Teil einer gespeicherten Trajektorie |
| S_phi(tau) | `q_delta` und `delta` in `paired_sim.py` | Geschaetzter Vorteil aufgezeichneter Aktionen gegenueber der Referenz |
| w_tau | `weight` im Abschnitt bzw. `w` im Batch | Im bisherigen BC-Pilot geometrisch bestimmt, noch nicht aus S_phi gelernt/abgeleitet |

Modell: [method.py](../experiments/self_imitation/stack_phased_8h_20261023/method.py),
Klasse `PhaseNet`. Sie liefert vier Aktionskomponenten und separat einen Logit
fuer den Abschluss einer Bewegungsphase. Nur die vier Aktionen gehoeren in den
quadratischen Nachahmungsfehler. Vorhersage und Ziel sind nicht zu vertauschen:
`pred` ist die neue Vorhersage, `a` ist das gespeicherte Label.

## 1. Nachahmungsfehler L_BC

In [pilot.py](../experiments/self_imitation/partial_self_imitation_20261104/pilot.py),
Funktion `train`:

```python
pred, z = model(x, p)
errors = (pred - a).square().mean(-1)
```

Das ist eine vereinfachte Darstellung der vorhandenen Tensor-Aufrufe.
Fuer jeden Frame entsteht ein Fehler `errors[i]`. `mean(-1)` mittelt ueber die
vier Aktionskomponenten. Der Code berechnet also

\[
e_i = \frac{1}{m}\sum_{j=1}^{m}
       (\pi_\theta(x_i)_j-a_{i,j})^2,\qquad m=4.
\]

Ein anschliessendes `errors.mean()` entspricht dem Mittel ueber den Batch.
Gegenueber der abgebildeten Formel mit einer Summe ueber Komponenten enthaelt
der Code einen zusaetzlichen Faktor 1/m. Beide Aktionsterme verwenden dieselbe
Skalierung; gegenueber weiteren Losstermen ist dieser Faktor jedoch relevant.

## 2. Gewichteter Self-Loss

[transition_pilot.py](../experiments/self_imitation/stack_transition_quality_20261024/transition_pilot.py),
Funktion `weighted_loss`:

```python
return (per_frame * weights).sum() / weights.sum()
```

Mit rohen positiven Gewichten u ergibt das

\[
\widehat L_{\rm self}
=\frac{\sum_i u_i e_i}{\sum_i u_i}
=\frac{1}{B}\sum_i\frac{u_i}{\overline u_{\rm batch}}e_i.
\]

Hier wird die Normalisierung im jeweiligen Batch vorgenommen. Das entspricht
nicht exakt einem vorab festen Erwartungswert ueber den gesamten D_self aus
der Abbildung. Eine gemeinsame Skalierung aller Batchgewichte kuerzt sich weg.

`Pool.sample` waehlt Phase, Episode, Abschnitt und Frame hierarchisch aus.
Das gespeicherte Abschnittsgewicht wird an den gezogenen Frame weitergegeben.
Es wird nicht zuerst explizit der Fehler aller H Frames eines Abschnitts
gemittelt und danach uniform ueber Abschnitte gemittelt. Samplingverteilung
und Abschnittslaengen sind deshalb bei einem exakten Formelvergleich relevant.

## 3. Mischung mit Originaldemonstrationen

Der gewertete Arm D in `partial_self_imitation/pilot.py` berechnet:

```python
actor = .75 * errors[:48].mean() + .25 * weighted_loss(errors[48:], w[48:])
```

Dies ist die naechste vorhandene Entsprechung zu

\[
L_{\rm actor}=(1-\lambda)L_{\rm BC}+\lambda L_{\rm self},
\qquad\lambda=0.25.
\]

Die ersten 48 Beispiele kommen aus den Originaldemos, die letzten 16 aus dem
Pool eigener erfolgreicher Episoden und bestaetigter Abschnitte. Der tatsaechlich
optimierte Gesamt-Loss fuegt `0.1 * bce` fuer den Phasenabschluss hinzu.
Dieser Zusatz steht nicht in der abgebildeten Aktions-Loss-Formel.

Die Produktionsvarianten
[production_train.py](../experiments/self_imitation/stack_transition_quality_20261024/production_train.py)
und [production_train_resume.py](../experiments/self_imitation/stack_transition_quality_20261024/production_train_resume.py)
verwenden einen anderen, dreiteiligen Mix: 0.5 Originaldemos, 0.25 erfolgreiches
Replay und 0.25 gewichtete neue Abschnittsframes.

## 4. Wo der Critic ins Spiel kommt

In [paired_sim.py](../experiments/critic/il_action_feasibility_20261107/paired_sim.py)
wird im besuchten Zustand zuerst die Referenzaktion und dann die tatsaechlich
ausgefuehrte Sammleraktion bewertet:

```python
q_delta = q_src - q_ref
delta = sum(gamma**i * step["q_delta"] for i, step in enumerate(window))
```

Das entspricht dem Score-Baustein Q_phi(s_t,a_t)-Q_phi(s_t,pi_0(x_t)).
Der Machbarkeitstest verwendet laut seinem `protocol.json` gamma=0.995,
waehrend der Vorschlag gamma=1 und eine ungewichtete Abschnittssumme vorsieht.
Diese Datei misst den Score und vergleicht ihn mit gepaarten Outcomes; sie
trainiert damit noch keine neue Policy.

Im BC-Pilot stammen die Gewichte dagegen aus `quality()`: Bewegung und
Ausrichtung der Wuerfel ergeben feste Werte zwischen 0.5 und 1.0. Das ist eine
geometrische Outcome-Heuristik, kein gelernter Critic.

**Die noch fehlende Verbindung ist:** Score S_phi berechnen, daraus nach einer
festgelegten Regel f positive Abschnittsgewichte ableiten und diese ueber die
vorgesehene D_self-Normalisierung in den Actor-Loss einspeisen. Die Gewichte
sollen beim Actortraining fest bleiben. Eine solche Regel wird durch die
Normalisierungsformel allein noch nicht definiert.

## 5. Abgrenzung zum historischen Actor-Critic-Loss

[core.py](../experiments/critic/critic_warmstart_20261104/core.py),
`Learner.update`, optimiert stattdessen

\[
-\operatorname{mean}Q_\phi(s,\pi_\theta(x))+cL_{\rm BC}.
\]

Hier laeuft der Aktionsgradient durch den Critic. Das ist ein anderes Verfahren
als die geplante Gewichtung gespeicherter eigener Aktionen durch feste Scores.
Der enthaltene Expert-BC-Term allein macht diesen Actor-Critic-Schritt noch
nicht zu dem Self-Imitation-Loss aus der Abbildung.

Die Kommentare erlaeutern den bestehenden Code. Modell, Loss-Rechnung,
Sampling, Seeds und Hyperparameter werden dadurch nicht veraendert.
