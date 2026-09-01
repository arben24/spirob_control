= Stand der Technik <sec:stand-der-technik>

== Bisherige Bedienwege des SpiRob

Vor dieser Arbeit gab es drei Wege, den Roboter zu bewegen; alle drei sind
Entwicklerwerkzeuge und für den täglichen Betrieb nur bedingt geeignet.

*MuJoCo-Viewer mit Serienbrücke.* Ein Skript öffnete das Simulationsmodell im
MuJoCo-Viewer und leitete die dort verstellten Aktuator-Stellgrößen als
Kraftkommandos an den ESP32 weiter. Der Viewer zeigt allerdings alle
Stellgrößen des Modells in Simulationskonvention, also negative Kräfte ohne
Einheit und ohne Bezug zur Hardware; Sicherheitsgrenzen, Not-Aus oder eine
Anzeige der zurückgemeldeten Kräfte gibt es nicht. Der Port war fest im
Quelltext hinterlegt.

*Kommandozeilen-Brücke für Policies.* Ein zweites Werkzeug lädt eine trainierte
Policy, baut den Beobachtungsvektor aus der Hardwaretelemetrie zusammen und
regelt mit 50 Hz. Es ist funktional das Vorbild dieser Arbeit, setzt aber die
komplette Trainingsumgebung voraus: PyTorch, mjlab und die Task-Registrierung,
weil das Beobachtungslayout zur Laufzeit aus einer aufgebauten
Simulationsumgebung ausgelesen wird. Auf einem Rechner ohne GPU und ohne diese
Umgebung ist es nicht startbar. Ziele werden als Text auf der Standardeingabe
oder über ein separates kleines Fenster per UDP gesetzt.

*Policy auf dem Mikrocontroller.* Für den Betrieb ohne PC wurden Netze als
C-Header exportiert und auf dem ESP32 ausgeführt. Das löst die
Abhängigkeitsfrage radikal, ist aber an einen Flash-Vorgang gebunden: Eine
andere Policy bedeutet ein neues Firmware-Image, und es gibt keine Ansicht des
Roboterzustands.

Der gemeinsame Nenner ist, dass jedes dieser Werkzeuge genau eine Aufgabe
erfüllt und dabei Wissen voraussetzt, das nicht in der Bedienung sichtbar ist -
etwa das Vorzeichen der Kraft, die Bedeutung der Seilnummern oder die Frage,
welche Policy mit welcher Sensorik überhaupt lauffähig ist.

== Vergleichbare Ansätze

Bedienoberflächen für Forschungsroboter folgen üblicherweise einem von zwei
Mustern. Der erste Weg ist ein web- oder middlewarebasiertes Bedienpult, wie es
etwa Werkzeuge im ROS-Umfeld anbieten: sehr flexibel, aber mit einer
Infrastruktur verbunden, die für einen Roboter mit zwei Stellgrößen deutlich
überdimensioniert wäre und die Installation auf einem fremden Rechner erschwert.
Der zweite Weg sind Simulator-eigene Betrachter wie der MuJoCo-Viewer selbst;
sie sind sofort verfügbar, zeigen aber die Modellsicht statt der Maschinensicht
und lassen sich nicht um Hardwarezustand, Sicherheitsgrenzen oder eine
Zielvorgabe ergänzen.

Für den Transport gelernter Regelungen aus der Trainingsumgebung in eine
schlanke Laufzeit ist der übliche Weg ein Austauschformat wie ONNX oder ein
TorchScript-Modul. Beides funktioniert, zieht aber wieder eine
Laufzeitbibliothek nach sich. Da die hier verwendeten Actor-Netze ausschließlich
aus linearen Schichten mit ELU bestehen und deterministisch ausgewertet werden,
ist ein Export der reinen Gewichte samt Beschreibung des Beobachtungslayouts der
sparsamste Weg - der Vorwärtspass sind dann wenige Zeilen NumPy.

== Abgrenzung

Diese Arbeit schließt die Lücke zwischen den genannten Werkzeugen: eine
Oberfläche, die beide Betriebsarten in derselben Ansicht anbietet, die
Simulation immer mitlaufen lässt, die Hardware bewusst zuschaltbar macht und
dabei ohne Trainingsbibliotheken auskommt. Sie ersetzt weder das Training noch
die Firmware, sondern macht deren Ergebnisse bedienbar.
