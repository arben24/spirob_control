= Umsetzung <sec:umsetzung>

== Der Regeltakt

Alle 20 ms ruft die Ereignisschleife der Oberfläche einen Regelschritt auf. Er
läuft immer in derselben Reihenfolge ab: Hardwaretelemetrie abholen, Sollkräfte
bestimmen, auf die Kraftgrenze begrenzen, die Simulation fünf Schritte à 4 ms
rechnen, die Kräfte an die Hardware schicken, Telemetrie einsammeln.

Die 50 Hz sind kein frei gewählter Wert, sondern der Takt, mit dem die Policies
trainiert wurden; sie rechnen zudem mit einer Historie über fünf Takte. Ein
anderer Takt würde ihnen eine andere Zeitachse vorsetzen. Der Zeitplan bleibt
deshalb auf seinem ursprünglichen Raster: Dauert ein Schritt zu lange, werden
verpasste Schlitze übersprungen, statt die Phase zu verschieben - ein
verpasster Regelschritt bleibt so ein verpasster Schritt und wird nicht
stillschweigend zu einem dauerhaft langsameren Regelkreis.

Die Anzeige wird bewusst seltener aufgefrischt als geregelt wird: das Bild
25-mal, die Zahlen 10-mal je Sekunde.

== Export und Nachbau der Policies

Das Exportwerkzeug lädt einen Trainings-Checkpoint, entnimmt die Gewichte der
linearen Schichten des Actors und schreibt sie zusammen mit einem Manifest in
eine komprimierte NumPy-Datei von rund 250 KiB. Das Manifest beschreibt die
Terme des Beobachtungsvektors mit Name und Dimension, die Historienlänge, die
Aktionsgrenze und die benötigten Sensorsignale.

Zwei Details sind dabei entscheidend und zugleich leicht zu übersehen. Erstens
die Reihenfolge: Die Schichten heißen im Checkpoint `mlp.0`, `mlp.2`, ... bis
`mlp.10`; wird lexikografisch sortiert, landet `mlp.10` vor `mlp.2` und das
Netz ist still vertauscht. Zweitens die Dimensionsprüfung: Das Layout wird nicht
aus dem Checkpoint gelesen - das würde eine vollständige Simulationsumgebung
erfordern -, sondern aus einer Tabelle rekonstruiert und gegen die
Eingangsdimension des Netzes geprüft. Passt beides nicht zusammen, bricht der
Export ab, statt später einen plausibel aussehenden, aber falschen Vektor zu
erzeugen.

Zur Laufzeit baut die Anwendung den Beobachtungsvektor neu auf: je Term die
vollständige Historie von alt nach neu, die Terme in Manifest-Reihenfolge. Beim
ersten Takt wird jeder Term über die ganze Historie kopiert statt mit Nullen
aufgefüllt, wie es der Ringpuffer der Trainingsumgebung ebenfalls tut. Als
`last_action` geht die auf $plus.minus 5$ begrenzte Netzausgabe ein, denn genau
dieser beschnittene Wert wurde im Training zurückgekoppelt. Der Vorwärtspass ist
dann eine Kette aus Matrixmultiplikation und ELU, die letzte Schicht ohne
Aktivierung; die Umrechnung in Kräfte folgt @eq:kraft.

== Simulation

Das Modell wurde unverändert aus dem Trainingsprojekt übernommen - jede
Änderung an Dämpfung, Reibung oder Seilparametern würde die Grundlage der
gelernten Regelung verschieben. Aus ihm liest die Anwendung alle Signale, die
irgendeine Policy braucht: Seillängen und -geschwindigkeiten, Gelenkwinkel und
-geschwindigkeiten sowie die Neigung jedes Segments. Die Reihenfolge folgt der
Modellreihenfolge, also von der Basis zur Spitze, weil die Trainingsumgebung
ihre Namensmuster genauso auflöst.

Die Vorzeichenkonvention ist an genau einer Stelle gekapselt: Nach außen sind
Seilkräfte Beträge in Newton, nur die Simulation rechnet mit ziehenden, also
negativen Stellgrößen.

== Serielle Anbindung

Die Verbindung zum Motorcontroller ist bewusst anspruchslos gehalten. Gesendet
werden ASCII-Zeilen (`start all`, `f <i> <newton>`, `stop`), empfangen werden
Binärpakete mit Zeitstempel, gemessener Kraft und Seillänge. Der Controller
sendet mit etwa 600 Hz, also zwölfmal schneller als geregelt wird; je Takt wird
deshalb der Empfangspuffer geleert und nur das jüngste Paket behalten. Das ist
zugleich die einfachste und die verzögerungsärmste Variante.

Gesendet wird höchstens 50-mal je Sekunde und nur bei einer Kraftänderung von
mehr als 0,05 N. Der Not-Aus umgeht beide Drosseln, weil er auch dann ankommen
muss, wenn er sich vom letzten Wert kaum unterscheidet. Kein Aufruf blockiert,
und keiner wirft: Ein abgezogenes Kabel beendet die Verbindung geordnet und
erscheint als Meldung in der Statuszeile, während die Simulation weiterläuft.

== Oberfläche

#figure(
  image("../Images/gui-policy.png", width: 100%),
  caption: [Die Oberfläche im Policy-Betrieb: links die Bedienelemente, rechts die 3D-Ansicht mit dem Ziel als Kugel, darunter die Telemetrie.],
) <fig:gui-policy>

@fig:gui-policy zeigt den Policy-Betrieb. Der Winkel-Regler bestimmt, wohin die
Spitze zeigen soll; der Abstand folgt in der Voreinstellung automatisch der
Schale aus @eq:schale, sodass das Ziel im trainierten Bereich bleibt. Wird er
von Hand verstellt und verlässt das Band, warnt die Oberfläche - verboten ist
es nicht, denn außerhalb zu extrapolieren ist ein legitimes Experiment.

Die Auswahl der Datenquelle für die Beobachtung ist der Punkt, an dem
Simulation und Hardware sichtbar auseinandertreten. Verlangt eine Policy
Signale, die der angeschlossene Controller nicht liefert, wird sie nicht
stillschweigend mit Ersatzwerten gefahren: Die Anwendung fällt in den
Handbetrieb zurück, setzt die Kräfte auf null und nennt den Grund.

#figure(
  image("../Images/gui-schema.png", width: 100%),
  caption: [Die Schema-Ansicht zeigt zusätzlich den trainierten Arbeitsraum als Band und erlaubt, das Ziel per Klick zu setzen. Sie kommt ohne Grafikbeschleunigung aus.],
) <fig:gui-schema>

== Windows-Tauglichkeit

Da die Anwendung ausdrücklich unter Windows laufen soll, wurden einige
Fallstricke von vornherein vermieden: keine fest verdrahteten POSIX-Pfade, kein
`select()` auf der Standardeingabe, Portauswahl über die Geräteliste von
pySerial statt über einen Gerätenamen, alle Pfade über `pathlib` und alle
Dateien mit ausdrücklicher UTF-8-Kodierung. Ein Startskript legt beim ersten
Aufruf die virtuelle Umgebung an, installiert die Abhängigkeiten und startet die
Oberfläche; danach genügt ein Doppelklick. Installiert werden nur MuJoCo, NumPy,
pySerial und Pillow - Tkinter gehört zur Standardinstallation von Python.

== Tests

Die Testsuite umfasst 36 Tests und läuft in wenigen Sekunden. Geprüft werden
das Layout jeder Policy gegen ihr Netz, die
Vollständigkeit der von der Simulation gelieferten Signale, das Auffüllen der
Historie beim ersten Takt, die Aktionsgrenze, die Kraftabbildung an ihren
Rändern, das Verhalten des Regelkreises (Kraftgrenze, Not-Aus, Rückfall bei
fehlender Sensorik) sowie die Geometrie des Arbeitsraums. Dazu kommt ein
Rauchtest, der die Oberfläche einmal vollständig durchklickt und dabei prüft,
dass ohne Verbindung nichts gesendet wird und eine Policy ohne Sensordaten in
den Handbetrieb zurückfällt; er wird übersprungen, wenn kein Fenstersystem
verfügbar ist. Der aussagekräftigste Test ist ein vollständiger Rollout bis ans
Ziel; er ist in @sec:messungen ausgewertet.
