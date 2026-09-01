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

== Die Sensorplatine

Die zweite Quelle hängt an einem eigenen USB-Port und sendet mit 1 MBaud einen
Binärstrom aus Frames: pro Frame ein Kopf und danach je Sensor eine Kennung und
drei Fließkommazahlen. Der Parser sucht den Kopf, prüft Modus und Sensoranzahl
auf Plausibilität und verlangt, dass unmittelbar hinter einem Frame der nächste
Kopf steht - ohne diese letzte Prüfung wäre jede Bytefolge, die zufällig wie ein
Kopf aussieht, ein Frame, und nach einem verlorenen Byte liefe der Parser
dauerhaft falsch.

Aus dem jüngsten vollständigen Frame werden die Beschleunigungen sensorweise
geglättet, in die physische Reihenfolge gebracht, auf Länge eins normiert und
über @eq:winkel in Gelenkwinkel umgerechnet. Solange nicht jeder der 14 Sensoren
mindestens einmal gesehen wurde, gibt es gar keine Winkel: Ein Vektor mit einem
Loch darin wäre schlimmer als keiner. Die Geschwindigkeiten entstehen aus einer
gefilterten Differenzierung, wie beim Motorcontroller auch.

Zwei Dinge kann die Software nicht selbst wissen, weil sie vom Einbau abhängen:
die Zuordnung der Sensorkennungen zu den Segmenten und das Vorzeichen der
Winkel. Für das Vorzeichen gibt es einen Schalter in der Oberfläche, der sofort
wirkt - biegt sich der Arm in der Anzeige zur falschen Seite, ist er gemeint.
Die Zuordnung steht als Konstante im Quelltext.

Ein dritter Punkt betrifft die Sicherheit der Anzeige: Sensordaten gelten nur
als Messung, solange frische Frames ankommen. Bleibt der Strom stehen, fällt die
Anzeige nach einer Sekunde auf die Simulation zurück und eine Policy, die diese
Signale braucht, geht in den Handbetrieb. Eine eingefrorene Armform, die als
aktueller Zustand ausgegeben wird, wäre die gefährlichere Antwort.

== Von den Winkeln zur Armform

Der SpiRob kann seine eigene Spitze nicht messen. Die Gelenkwinkel und die
Gliedlängen genügen aber: Die Neigung eines Segments ist die Summe aller
Gelenkwinkel davor, und die Kette der gedrehten Gliedvektoren ergibt jeden
Stützpunkt bis hin zur Spitze. Die Gliedlängen werden dabei nicht als Konstante
gepflegt, sondern beim Start aus demselben MJCF gelesen, auf dem die Policies
trainiert wurden - eine kopierte Zahl wäre eine Zahl, die still veraltet.

Der Nachweis, dass diese Rechnung stimmt, ist billig zu haben: Füttert man sie
mit den Gelenkwinkeln der Simulation, muss sie deren Spitzenposition treffen.
Gemessen stimmen beide auf $10^(-16)$ m überein.

Damit bekommt die Oberfläche eine Größe, die es vorher nicht gab: den Abstand
zwischen kommandiertem Ziel und *gemessener* Spitze. Genau darauf ist im
Training belohnt worden, und genau das konnte die Maschine bisher nicht sagen.

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
Signale, die kein angeschlossenes Gerät liefert, wird sie nicht stillschweigend
mit Ersatzwerten gefahren: Die Anwendung fällt in den Handbetrieb zurück, setzt
die Kräfte auf null und nennt sowohl das fehlende Signal als auch das Gerät, das
es liefern würde.

Hängt die Sensorplatine, wechselt die Anzeige ihre Aussage (@fig:gui-sensoren).
Im Schema wird die gemessene Armform zur Hauptlinie und die Simulation nur noch
zur blassen gestrichelten Kurve dahinter; der Abstand zwischen beiden ist der
Sim-to-Real-Unterschied, und er soll sichtbar sein. In der 3D-Ansicht wird die
Messung als Strang über das Modell gelegt. Die Telemetrie bekommt zwei Felder
dazu, "Spitze gemessen" und "Abstand gemessen" - ohne Platine bleiben sie leer,
statt die Simulation als Messung auszugeben.

#figure(
  image("../Images/gui-sensoren.png", width: 100%),
  caption: [Mit angeschlossener Sensorplatine zeigt das Schema den gemessenen Arm (grün) und die Simulation als blasse gestrichelte Linie. Die Telemetrie nennt beide Zielabstände getrennt.],
) <fig:gui-sensoren>

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

Die Testsuite umfasst 51 Tests und läuft in wenigen Sekunden. Geprüft werden
das Layout jeder Policy gegen ihr Netz, die
Vollständigkeit der von der Simulation gelieferten Signale, das Auffüllen der
Historie beim ersten Takt, die Aktionsgrenze, die Kraftabbildung an ihren
Rändern, das Verhalten des Regelkreises (Kraftgrenze, Not-Aus, Rückfall bei
fehlender Sensorik) sowie die Geometrie des Arbeitsraums. Die Anbindung der
Sensorplatine wird über ein virtuelles Terminalpaar geprüft: Der Test schreibt
synthetische Frames auf eine echte serielle Leitung und erwartet am anderen Ende
genau die Winkel, aus denen er sie erzeugt hat - damit läuft der vollständige
Weg vom Byte bis zum Gelenkwinkel im Test, ohne dass Hardware angeschlossen sein
muss. Dazu kommt ein
Rauchtest, der die Oberfläche einmal vollständig durchklickt und dabei prüft,
dass ohne Verbindung nichts gesendet wird und eine Policy ohne Sensordaten in
den Handbetrieb zurückfällt; er wird übersprungen, wenn kein Fenstersystem
verfügbar ist. Der aussagekräftigste Test ist ein vollständiger Rollout bis ans
Ziel; er ist in @sec:messungen ausgewertet.
