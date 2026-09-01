= Entwurf / Design <sec:entwurf>

== Anforderungen

Aus der Analyse in @sec:stand-der-technik ergeben sich die folgenden
Anforderungen. Sie sind nach ihrer Bedeutung für den praktischen Betrieb
geordnet.

#figure(
  table(
    columns: (auto, 1fr),
    inset: 7pt,
    align: left,
    [*Nr.*], [*Anforderung*],
    [A1], [Der Roboter ist von Hand über zwei Schieberegler fahrbar - eine Kraft je Seil, in Newton und als Betrag.],
    [A2], [Eine trainierte Policy ist nutzbar; vorgegeben wird nur die Zielposition der Spitze.],
    [A3], [Die Anwendung läuft ohne PyTorch, ohne die Trainingsbibliotheken und ohne GPU.],
    [A4], [Simulation und Hardware laufen in einem Programm; es ist jederzeit sichtbar, ob die Hardware Kräfte bekommt.],
    [A5], [Not-Aus und eine Kraftobergrenze sind immer erreichbar.],
    [A6], [Fehler im Betrieb (Kabel gezogen, kein Treiber, keine Grafikbeschleunigung) führen zu einer Meldung, nicht zum Absturz.],
    [A7], [Nach `git clone` ist die Anwendung unter Windows in wenigen Minuten startbar.],
    [A8], [Die vorhandene Sensorik ist über einen zweiten USB-Port einbindbar; die Anzeige zeigt dann den gemessenen Arm, und jede Policy kann auf gemessenen Daten laufen.],
  ),
  caption: [Anforderungen an die Bedienoberfläche.],
) <tab:anforderungen>

== Grundsatzentscheidungen

*Ein Thread statt eines Regelungs-Threads.* Der naheliegende Entwurf trennt
Regelung und Anzeige in zwei Threads. Eine Abschätzung zeigt jedoch, dass das
nicht nötig ist: Ein Regelschritt kostet etwa 0,1 ms und eine Bildausgabe rund
6 bis 8 ms, zusammen also weniger als die Hälfte des 20-ms-Budgets. Der
Regelkreis hängt deshalb an der Ereignisschleife der Oberfläche. Das erspart
Sperren, Warteschlangen und jede Form von Wettlauf zwischen Anzeige und
Regelung - für die geforderte Robustheit (A6) der wirksamste Hebel. Damit die
Rechnung auch auf einem sehr großen Bildschirm aufgeht, richtet sich die
Bildrate nach der gemessenen Zeichendauer: Wird das Zeichnen teuer, wird
seltener gezeichnet, der Regeltakt bleibt.

*Gewichte statt Laufzeitbibliothek.* Um A3 zu erfüllen, werden die Policies
einmalig aus dem Trainingsprojekt exportiert: die Gewichte als NumPy-Arrays,
das Beobachtungslayout als JSON-Manifest daneben. Der Vorwärtspass wird
nachgebaut. Der Preis dafür ist, dass das Layout nun an zwei Stellen existiert
und auseinanderlaufen kann; dagegen hilft nur, es beim Export gegen die
Netzdimension und zur Laufzeit gegen die gelieferten Signale zu prüfen - und
das Ganze in einem Rollout zu testen (@sec:messungen).

*Geräte als austauschbare Quellen.* Eine Policy verlangt Signale, keine Geräte.
Deshalb meldet jede Hardwarequelle, welche Signale sie liefert, und der
Regelkreis führt darüber Buch; ob eine Policy fahrbar ist, entscheidet allein
der Abgleich beider Listen (A8). Das kostet ein paar Zeilen mehr als eine
direkte Abfrage, hat aber zwei Folgen, die den Aufwand tragen: Eine dritte
Quelle bedeutet keine Änderung an der Prüfung, und eine Policy mit fehlenden
Signalen wird nie mit Ersatzwerten gefahren - sie fällt in den Handbetrieb
zurück, mit einer Meldung, welches Signal fehlt und welches Gerät es liefern
würde.

*Die Simulation läuft immer.* Sie ist Anzeige und Vergleichsmaßstab zugleich.
Damit erfüllt A4 sich fast von selbst: Es gibt immer etwas zu sehen, auch ohne
Hardware, und im Hardwarebetrieb steht neben dem realen Zustand das erwartete
Verhalten. Die Hardware ist eine Zugabe, die bewusst zugeschaltet wird - erst
verbinden, dann freigeben.

*Zwei Regler in beiden Betriebsarten.* Der Roboter hat zwei Stellgrößen, und
sein erreichbarer Arbeitsraum ist eine Kurve, keine Fläche (@eq:schale). Beides
lässt sich mit je zwei Reglern vollständig abdecken: im Handbetrieb zwei
Kräfte, im Policy-Betrieb Winkel und Abstand. Rastet der Abstand auf die
Schale ein - die Voreinstellung -, genügt sogar ein einziger Regler.

== Aufbau der Oberfläche

Das Fenster ist dreigeteilt: links die Bedienelemente, rechts die Ansicht des
Roboters mit der Telemetrie darunter, unten eine Statuszeile für Meldungen. Die
beiden Betriebsarten liegen als Register übereinander, sodass immer nur die
gerade gültigen Regler sichtbar sind und ein Wechsel eindeutig ist. Not-Aus und
Verbindungszustand sitzen in der Kopfzeile, außerhalb des scrollbaren Bereichs -
sie müssen unabhängig von Fenstergröße und Scrollposition erreichbar bleiben (A5).

Die Ansicht ist umschaltbar: ein gerendertes Bild des MuJoCo-Modells oder ein
flaches Schema, das zusätzlich den trainierten Arbeitsraum zeigt. Das Schema
kommt ohne Grafikbeschleunigung aus und ist damit zugleich die Rückfallebene,
wenn das Rendern auf einem Rechner nicht startet (A6).

== Softwarearchitektur

Die Zerlegung folgt der Frage, was ohne Fenster testbar sein muss.

#figure(
  table(
    columns: (auto, 1fr),
    inset: 7pt,
    align: left,
    [*Modul*], [*Verantwortung*],
    [`app`], [Fenster, Bedienelemente, Takt - keine Fachlogik],
    [`controller`], [ein Regelschritt: Modus, Kräfte, Sicherheitsgrenze, Telemetrie],
    [`simulation`], [MuJoCo-Modell, Regelschritt, Sensorsignale],
    [`policy`], [Beobachtungsvektor, Vorwärtspass, Aktionsgrenze],
    [`hardware`], [Motor-Controller: Kraftkommandos und Telemetrie, nicht blockierend],
    [`sensors`], [Sensorplatine: Frames, Gelenkwinkel, Segmentneigungen],
    [`kinematics`], [Armform und Spitze aus den Gelenkwinkeln],
    [`view`], [3D-Bild und Schema],
    [`workspace`], [Geometrie des Arbeitsraums, nur Standardbibliothek],
  ),
  caption: [Module und ihre Verantwortung.],
) <tab:module>

`controller` kennt keine Widgets und `app` keine Physik. Dadurch lässt sich der
vollständige Regelkreis in den Tests durchfahren, einschließlich Moduswechsel,
Kraftgrenze und Not-Aus.
