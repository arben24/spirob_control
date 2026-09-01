# Policies

## Woher sie kommen

Die Netze stammen aus dem Trainingsprojekt (`RL_explor`, mjlab + rsl_rl +
PyTorch). Trainiert wurde der Reach-Task: *„halte die Spitze an einem zufällig
gezogenen Ziel“*. Der Roboter bekommt dafür 50-mal je Sekunde einen
Beobachtungsvektor und gibt zwei Zahlen zurück, aus denen die Seilkräfte
werden.

Die vier mitgelieferten Policies unterscheiden sich **nur** darin, welche
Sensordaten der Actor sehen darf – eine Ablation, die zeigt, wie viel Sensorik
die Aufgabe wirklich braucht:

| Datei               | Sensor-Level | Der Actor sieht …                                               | Eingänge | Mittlerer Zielabstand am Trainingsende |
| ------------------- | ------------ | --------------------------------------------------------------- | -------- | -------------------------------------- |
| `reach_force.npz`   | `force`      | nur Ziel und letzte Aktion                                       | 25       | 344 mm – erreicht das Ziel **nicht**    |
| `reach_tendon.npz`  | `tendon`     | zusätzlich Seillänge und -geschwindigkeit                        | 45       | 68 mm                                   |
| `reach_imu.npz`     | `imu`        | zusätzlich die Neigung jedes Segments                            | 185      | 44 mm                                   |
| `reach_joints.npz`  | `joints`     | die 13 Gelenkwinkel und ihre Geschwindigkeiten                   | 155      | 42 mm                                   |

`force` ist bewusst mit dabei: es ist die Referenz der Ablation und zeigt, dass
ohne jede Rückmeldung nichts geht. Wer den Roboter arbeiten sehen will, nimmt
`joints` (Simulation) oder `tendon` (Hardware).

Alle vier sind Actor-Netze mit fünf verdeckten Schichten
(128-128-128-128-64) und ELU-Aktivierung, rund 78 000 Parameter.

## Der Beobachtungsvektor

Hier liegt der eigentliche Aufwand. Das Netz bekommt je Term die vollständige
Historie über fünf Takte, alt nach neu, und die Terme in genau der Reihenfolge,
in der die Trainingsumgebung sie zusammensetzt. Beispiel `tendon`, 45 Werte:

```text
[ target(t-4) … target(t) ]        3 Werte je Takt  (Ziel x, y=0, z)
[ last_action(t-4) … (t) ]         2                (rohe Aktion des Vortakts)
[ tendon_len(t-4) … (t) ]          2                (Seillänge minus Ruhelänge)
[ tendon_vel(t-4) … (t) ]          2                (Seilgeschwindigkeit)
```

Stimmt hier die Reihenfolge nicht, rechnet das Netz trotzdem weiter – der Arm
bewegt sich dann einfach falsch, ohne dass irgendetwas einen Fehler meldet.
Deshalb steht das Layout im Manifest jeder `.npz`-Datei, wird beim Export gegen
die Eingangsdimension des Netzes geprüft und zur Laufzeit noch einmal gegen die
tatsächlich gelieferte Signallänge.

Zwei weitere Feinheiten, die aus dem Training übernommen werden mussten:

* **Beim ersten Takt** wird jeder Term über die ganze Historie kopiert, statt
  mit Nullen aufzufüllen – so hält es der Ringpuffer der Trainingsumgebung
  auch.
* **`last_action`** ist die auf ±5 begrenzte rohe Netzausgabe, nicht die
  unbegrenzte: im Training beschnitt der Wrapper die Aktion, bevor die
  Umgebung sie sah, und genau dieser Wert wurde zurückgekoppelt.

Aus der Aktion werden die Seilkräfte so:

```text
F_i = clip(75 - 75 * a_i, 0, 150)   [N]
```

## Vom Checkpoint zum NumPy-Paket

Damit die GUI ohne PyTorch auskommt, werden die Gewichte einmalig exportiert.
Das Werkzeug dafür liegt in `src/tools/export_policy.py` und wird **im
Trainings-Repo** ausgeführt:

```bash
cd ~/RL_explor
.venv/bin/python /pfad/zu/spirob_control/src/tools/export_policy.py \
    --checkpoint logs/rsl_rl/rl_explor_spirob_tcp_tendon/<run>/model_499.pt \
    --sensor-level tendon \
    --out /pfad/zu/spirob_control/src/spirob_control/assets/policies/reach_tendon.npz \
    --name "Reach – tendon" \
    --description "Kurzbeschreibung, die die GUI anzeigt"
```

Herauskommt eine `.npz` mit den Gewichten je Schicht und einem JSON-Manifest
(Layout, Historienlänge, Aktionsgrenze, benötigte Signale, Herkunft des
Checkpoints). Die Datei ist rund 250 KiB groß und wird eingecheckt. Neue
Dateien in `assets/policies/` findet die Oberfläche beim nächsten Start von
selbst.

Der Vorwärtspass in `policy.py` ist dann nur noch eine Kette aus
Matrixmultiplikation und ELU – ohne Normalisierung, ohne Sampling: die
deterministische Aktion **ist** die Netzausgabe.

## Woher wir wissen, dass der Nachbau stimmt

Ein falsch zusammengesetzter Beobachtungsvektor fällt nicht auf, solange man
nur die Dimensionen prüft. Der überzeugende Test ist deshalb der Rollout: in
der Simulation wird eine Policy 15 Sekunden lang auf ein Ziel angesetzt und der
verbleibende Abstand gemessen.

Genau das tut `tests/test_policy.py`. Das Ergebnis über den Arbeitsraum stimmt
mit den Werten überein, die am Ende des Trainings protokolliert wurden – für
alle vier Sensor-Level, einschließlich des erwarteten Scheiterns von `force`.
Wären Termreihenfolge, Historienrichtung oder Kraftabbildung vertauscht, wäre
davon nichts zu sehen.

## Grenzen

* Die Policies sind auf den **Reach-Task** trainiert. Andere Aufgaben aus dem
  Trainingsprojekt (Form vorgeben, Trajektorie folgen, ein Objekt umgreifen)
  haben andere Zielvorgaben und bräuchten in der GUI zusätzliche Regler.
* Sie kennen nur den **trainierten Arbeitsraum**. Außerhalb extrapolieren sie;
  die Oberfläche warnt in dem Fall.
* Zwischen Simulation und Hardware bleibt ein Sim-to-Real-Abstand. Die
  angegebenen Millimeterwerte stammen aus der Simulation, nicht vom realen
  Aufbau.
