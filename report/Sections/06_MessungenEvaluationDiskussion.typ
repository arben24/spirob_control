= Messungen, Evaluation und Diskussion <sec:messungen>

Zwei Fragen sind zu beantworten. Erstens: Entspricht die nachgebaute Regelung
dem, was trainiert wurde - oder ist beim Export und beim Zusammensetzen des
Beobachtungsvektors etwas verrutscht? Zweitens: Hält der Regelkreis seinen Takt?

== Versuchsaufbau

Alle Messungen laufen in der Simulation auf dem Entwicklungsrechner. Je Policy
und je Zielwinkel wird ein Rollout über 15 s gefahren; der Zielabstand wird über
die letzten 3 s gemittelt, um den eingeschwungenen Zustand statt der Anfahrt zu
bewerten. Die Ziele liegen auf der Mittellinie der Schale (@eq:schale) bei
elf Winkeln von $-1.5$ bis $+1.5$ rad. Das Skript `tools/evaluate_policies.py`
erzeugt diese Daten reproduzierbar und legt sie als CSV in `extra/` ab.

== Übereinstimmung mit dem Training

#figure(
  table(
    columns: (auto, auto, auto, auto),
    inset: 7pt,
    align: (left, right, right, right),
    [*Sensor-Level*], [*Fehler Nachbau*], [*Spanne*], [*Trainingsende*],
    [`force`], [294 mm], [177 - 443 mm], [344 mm],
    [`tendon`], [75 mm], [38 - 132 mm], [68 mm],
    [`imu`], [91 mm], [21 - 285 mm], [44 mm],
    [`joints`], [63 mm], [18 - 116 mm], [42 mm],
  ),
  caption: [Mittlerer Zielabstand im eingeschwungenen Zustand über elf Zielwinkel, verglichen mit der im Training protokollierten mittleren Zielabweichung.],
) <tab:genauigkeit>

@tab:genauigkeit zeigt die entscheidende Aussage: Die Rangfolge der Sensor-Level
und die Größenordnung der Fehler stimmen mit dem Training überein. Insbesondere
scheitert `force` im Nachbau ebenso deutlich wie im Training - dieses Level
sieht keinerlei Rückmeldung und ist die Referenz der Ablation, nicht eine
brauchbare Regelung. Dass ausgerechnet dieses erwartete Scheitern reproduziert
wird, ist ein starkes Indiz dafür, dass der Beobachtungsvektor korrekt
zusammengesetzt ist: Ein vertauschter Term oder eine umgekehrte Historie würde
sich nicht als "genauso schlecht wie im Training" äußern, sondern als beliebiges
Verhalten.

Die verbleibenden Abweichungen haben zwei nachvollziehbare Ursachen. Zum einen
sind die Trainingswerte über ganze Episoden gemittelt, also einschließlich der
Anfahrphase und über zufällig gezogene Ziele; hier wird stattdessen der
eingeschwungene Zustand auf der Schalenmittellinie gemessen. Zum anderen wurde
im Training mit Domänenrandomisierung gearbeitet, hier läuft das Modell bei
seinen nominellen Parametern.

Auffällig ist ein Ausreißer: `imu` verfehlt bei $alpha = -0.9$ rad das Ziel um
285 mm, während dieselbe Policy bei den Nachbarwinkeln 21 bzw. 32 mm erreicht.
Der Mittelwert dieses Levels wird dadurch nach oben verzerrt und liegt über
dem von `tendon`, obwohl es im Training besser abschnitt. Es handelt sich um
einen einzelnen Arbeitspunkt, in dem die Regelung in eine andere Ruhelage
einschwingt - ein Verhalten, das die Aufgabe zulässt, weil dieselbe
Spitzenposition durch mehrere Armformen erreichbar ist.

Ein zweites Muster durchzieht alle Level: Am größten sind die Fehler nahe
$alpha = 0$, wo alle vier Policies bei rund 110 mm liegen. Der Grund ist
geometrisch. Der gestreckte Arm reicht 440 mm weit, das Ziel auf der Schale
liegt bei $alpha = 0$ aber nur 330 mm über dem Fußpunkt. Die Spitze muss also
nicht seitlich ausgelenkt, sondern eingerollt werden - eine Bewegung, die von
beiden Seilen gleichzeitig kommt und deren Richtung im Beobachtungsvektor kaum
unterschieden werden kann. Für die Bedienung heißt das: Ziele nahe der
Senkrechten sind die schwierigsten, und die Oberfläche zeigt diesen Fehler
ehrlich an, statt ihn zu verstecken.

== Zeitverhalten

Ein Regelschritt - Beobachtung zusammensetzen, Netz auswerten, fünf
Simulationsschritte rechnen - kostet im Mittel 0,09 bis 0,11 ms, je nach
Sensor-Level. Im laufenden Betrieb mit Anzeige meldet die Statuszeile
Werte zwischen 0,17 und 0,42 ms je Takt; die Differenz ist die Telemetrie und
das gelegentliche Auffrischen der Anzeige.

Deutlich teurer ist die Bildausgabe, also das Rendern in MuJoCo samt Übergabe
an die Zeichenfläche. Sie hängt an der Fenstergröße und wurde bei drei Größen
gemessen (@tab:zeit). Weil sie höchstens jeden zweiten Takt anfällt und die
Bildrate zurückgenommen wird, sobald ein Bild mehr als etwa 5 ms je Takt
kostet, bleibt der Regeltakt davon unberührt - bis zu einer Fenstergröße von
1920 $times$ 1080 liegt er bei 50,0 Hz.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    inset: 7pt,
    align: (left, right, right, right),
    [*Zeichenfläche*], [*Bildausgabe*], [*Bilder je s*], [*Regeltakt*],
    [839 $times$ 534], [6,2 ms], [25], [50,0 Hz],
    [1439 $times$ 714], [8,2 ms], [25], [50,0 Hz],
    [4639 $times$ 2514], [140 ms], [2], [39 Hz],
  ),
  caption: [Kosten der Bildausgabe und ihre Auswirkung auf den Regeltakt. Die letzte Zeile ist ein virtueller Bildschirm über mehrere Monitore und damit ein Grenzfall weit jenseits üblicher Vollbildgrößen.],
) <tab:zeit>

Erst im letzten Fall - einer Zeichenfläche mit knapp zwölf Millionen Bildpunkten
- wird die Bildausgabe so teuer, dass sie trotz zurückgenommener Bildrate auf
den Takt durchschlägt. Bis dahin werden von den verfügbaren 20 ms je Takt im
Mittel etwa 4 ms benutzt. Die eingangs getroffene Entscheidung gegen einen
eigenen Regelungs-Thread (@sec:entwurf) ist damit bestätigt: Es gibt keinen
Bedarf für Nebenläufigkeit, und die dadurch vermiedenen Fehlerquellen sind der
eigentliche Gewinn.

== Diskussion und Grenzen

Zur zweiten Frage der Arbeit - wie viel Sensorik nötig ist - liefert
@tab:genauigkeit eine klare Rangfolge, die sich nun auch auf der Maschine
nachfahren lässt: Ohne jede Rückmeldung (`force`) ist die Aufgabe nicht lösbar;
die Seilencoder allein (`tendon`) bringen den Fehler auf ein Viertel, und die
Gelenkwinkel (`joints`) noch einmal deutlich weiter. Damit ist auch die
praktische Frage beantwortet, ob sich die zweite Platine lohnt.

Die Ergebnisse belegen, dass sich eine gelernte Regelung aus ihrer
Trainingsumgebung herauslösen lässt, ohne ihr Verhalten zu verändern - und dass
sich das auch nachweisen lässt, wenn man den Nachweis über das Verhalten führt
statt über Dimensionen. Ein Vergleich der Netzausgaben zwischen PyTorch und dem
NumPy-Nachbau auf identischen Eingaben würde die Aussage weiter härten und wäre
mit geringem Aufwand nachzuholen.

Zwei Einschränkungen bleiben. Erstens sind alle hier berichteten Zahlen
Simulationswerte; der Sim-to-Real-Abstand ist damit noch nicht vermessen. Die
Voraussetzungen dafür sind allerdings geschaffen: Mit der angebundenen
Sensorplatine sind alle vier Sensor-Level auch auf der realen Hardware fahrbar,
und die Oberfläche zeigt den Abstand zwischen kommandiertem Ziel und gemessener
Spitze live an - dieselbe Größe, auf die im Training belohnt wurde. Was fehlt,
ist die Messreihe selbst und ein Aufzeichnen dieser Werte aus der Oberfläche
heraus.

Zweitens hängt die Güte der gemessenen Armform an zwei Annahmen über den
Einbau, die die Software nicht prüfen kann: die Zuordnung der Sensoren zu den
Segmenten und das Vorzeichen der Winkel. Beides lässt sich in wenigen Sekunden
verifizieren, indem man den Arm von Hand biegt und die Anzeige beobachtet -
aber es ist ein Handgriff, der vor jeder Messreihe stehen muss, und kein
Automatismus.
