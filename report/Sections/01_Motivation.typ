= Motivation <sec:motivation>

Weiche, seilzuggetriebene Greifer sind ein aktives Feld der Robotik, weil sie
Gegenstände sehr unterschiedlicher Form und Größe umschließen können, ohne für
jede davon eigens ausgelegt zu sein. Der SpiRob folgt dazu einem
bioinspirierten Entwurfsprinzip: Seine Segmente sind entlang einer
logarithmischen Spirale verjüngt, wodurch derselbe Greifer über mehrere
Größenordnungen hinweg funktioniert und mit nur zwei Seilen angetrieben werden
kann @wang_2025. Genau diese Sparsamkeit macht ihn interessant - und zugleich
schwer zu bedienen: Zwei Zahlen bestimmen die gesamte Form eines Arms mit
dreizehn Gelenken, und der Zusammenhang zwischen beiden ist weder linear noch
anschaulich.

Für den am Institut aufgebauten SpiRob lagen zu Beginn dieser Arbeit bereits
alle Einzelteile vor: ein in MuJoCo @todorov_2012 abgestimmtes
Simulationsmodell, eine Firmware, die auf einem ESP32 die Seilkräfte regelt,
und mehrere mit Reinforcement Learning trainierte Regelungen, die die Spitze an
eine vorgegebene Position bringen. Was fehlte, war der Zugang dazu. Bedient
wurde der Roboter entweder über die Schieberegler des MuJoCo-Viewers - einem
Entwicklerwerkzeug, das jede Aktuator-Stellgröße unkommentiert anbietet - oder
über Kommandozeilenwerkzeuge, die die vollständige Trainingsumgebung samt
PyTorch, mjlab und einer passenden CUDA-Installation voraussetzen. Für eine
Vorführung, eine Messreihe oder die Inbetriebnahme an einem anderen Rechner war
das umständlich und fehleranfällig.

Daraus ergibt sich die Zielstellung dieser Arbeit: eine eigenständige, bewusst
einfach gehaltene grafische Bedienoberfläche, die den SpiRob auf zwei Wegen
fahrbar macht - von Hand über zwei Schieberegler für die Seilkräfte und über
eine trainierte Policy, der nur noch das Ziel der Spitze vorgegeben wird. Sie
soll Simulation und Hardware in einem Programm zusammenführen, ohne
Trainingsbibliotheken auskommen und auf einem beliebigen Windows-Rechner nach
dem Klonen des Repositories startbar sein.

Der Aufbau der Arbeit folgt diesem Weg. @sec:grundlagen legt die Grundlagen zu
Aufbau, Antrieb und Arbeitsraum des SpiRob sowie zur Struktur der trainierten
Regelungen. @sec:stand-der-technik ordnet die bisherigen Bedienwege und
vergleichbare Werkzeuge ein. @sec:entwurf entwickelt daraus die Anforderungen
und die Architektur, @sec:umsetzung beschreibt die Umsetzung im Detail.
@sec:messungen weist nach, dass der Nachbau der Regelung dem Training
entspricht, und misst das Zeitverhalten; @sec:zusammenfassung fasst zusammen
und benennt die offenen Punkte.
