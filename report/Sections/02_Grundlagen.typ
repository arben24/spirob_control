= Grundlagen <sec:grundlagen>

== Aufbau und Antrieb des SpiRob

Der SpiRob ist eine serielle Kette aus 14 Segmenten, die über 13 Drehgelenke
verbunden sind. Alle Gelenkachsen zeigen in dieselbe Richtung, sodass sich der
Arm ausschließlich in einer Ebene biegt - im Folgenden die $x$-$z$-Ebene mit
$z$ nach oben und $x$ zur Seite. Die Segmente verjüngen sich entlang einer
logarithmischen Spirale; dadurch krümmt sich der Arm bei gleichmäßigem Zug
spiralförmig ein und kann Objekte sehr unterschiedlicher Größe umschließen
@wang_2025.

Angetrieben wird er von zwei Seilen, die außen an der Kette entlanglaufen und
von je einem Motor über eine Spule gezogen werden. Ein Seil allein biegt den
Arm zu seiner Seite, beide gemeinsam rollen ihn ein. Die Firmware auf dem
ESP32 regelt dabei nicht die Position der Spulen, sondern die *Zugkraft*: Der
Host gibt je Seil eine Sollkraft zwischen 0 und 150 N vor. In der Simulation
entspricht dem eine ziehende, also negative Stellgröße im Bereich
$-150 dots 0$ N.

Weil der Tentakel nicht dehnbar ist, füllen die erreichbaren Positionen der
Spitze keine Fläche, sondern liegen auf einer dünnen, bogenförmigen Schale.
Seitliches Biegen tauscht Auslenkung gegen Reichweite. Der Zusammenhang wurde
im Trainingsprojekt an eine quasistatische Messreihe angepasst und lautet

$ r(alpha) = r_0 - c alpha^2, quad r_0 = 0.33 "m", quad c = 0.045 "m/rad"^2 $ <eq:schale>

mit dem Winkel $alpha$ zur Senkrechten, begrenzt auf $plus.minus 1.7$ rad. Die
Zielpositionen im Training wurden aus einem Band von $plus.minus 0.08$ m um
diese Schale gezogen; @eq:schale beschreibt damit zugleich den Bereich, in dem
die gelernte Regelung verlässlich arbeitet.

== Regelung durch Reinforcement Learning

Die verwendeten Regelungen wurden mit Proximal Policy Optimization
@schulman_2017 in einer massiv parallelen Simulationsumgebung
@rudin_2022 trainiert. Die Aufgabe ("Reach") lautet: Halte die Spitze an einer
zufällig gezogenen Zielposition. Der Regeltakt beträgt 50 Hz, was bei einem
Simulationszeitschritt von 4 ms einer Dezimation von fünf entspricht.

Die Policy ist ein mehrschichtiges Perzeptron mit fünf verdeckten Schichten
(128-128-128-128-64) und ELU-Aktivierung. Sie bekommt einen Beobachtungsvektor
und liefert zwei Zahlen $a_0, a_1$, aus denen die Seilkräfte werden:

$ F_i = "clip"(75 - 75 a_i, 0, 150) "N" $ <eq:kraft>

Der Beobachtungsvektor besteht aus mehreren Termen, von denen jeder als
Historie über fünf Takte eingeht. Immer enthalten sind die Zielposition und die
zuletzt ausgegebene Aktion. Welche Sensordaten darüber hinaus sichtbar sind,
unterscheidet die vier trainierten Varianten - eine Ablation, die zeigen soll,
wie viel Sensorik die Aufgabe wirklich braucht (@tab:level).

#figure(
  table(
    columns: (auto, 1fr, auto),
    inset: 7pt,
    align: left,
    [*Sensor-Level*], [*Zusätzlich sichtbar*], [*Eingänge*],
    [`force`], [nichts], [25],
    [`tendon`], [Seillänge und -geschwindigkeit], [45],
    [`imu`], [zusätzlich die Neigung jedes Segments], [185],
    [`joints`], [13 Gelenkwinkel und ihre Geschwindigkeiten], [155],
  ),
  caption: [Die vier trainierten Sensor-Level. Alle sehen zusätzlich Ziel und letzte Aktion.],
) <tab:level>

Entscheidend für diese Arbeit ist, dass die Policy deterministisch ausgewertet
werden kann: Sie wurde ohne Beobachtungsnormalisierung und mit skalarer
Standardabweichung trainiert, sodass die auszuführende Aktion exakt die
Netzausgabe ist. Ein Vorwärtspass aus Matrixmultiplikationen und ELU genügt -
eine Eigenschaft, auf der die gesamte Umsetzung in @sec:umsetzung aufbaut.

== Werkzeuge

Für die Physik wird MuJoCo @todorov_2012 verwendet, dieselbe Engine wie im
Training, mit unverändert übernommenem Modell. Die Oberfläche nutzt Tkinter
@python_tkinter, das Teil der Python-Standardbibliothek ist und unter Windows
ohne Zusatzinstallation zur Verfügung steht. Die serielle Verbindung zum
Motorcontroller läuft über pySerial @pyserial.
