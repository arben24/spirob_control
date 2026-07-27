#import "../template.typ": hinweis

= Messungen, Evaluation und Diskussion <sec:messungen>

#hinweis[
  Beschreibung des Versuchsaufbaus bzw. der Messmethodik, Darstellung der
  Ergebnisse (Diagramme/Tabellen), Diskussion und Einordnung der Ergebnisse
  sowie eine kritische Betrachtung der Grenzen der eigenen Arbeit.
]

== Verwendung von Bildern und Grafiken

Die nachfolgende Abbildung @fig:zylinder zeigt ein Beispielbild, welches als
Veranschaulichung in wissenschaftlichen Arbeiten dienen kann.

#figure(
  // Platzhalter für ein Bild. Ersetzen Sie die URL oder den Pfad.
  // image("../Images/CylinderImage.jpg", width: 60%),
  rect(width: 80%, height: 7cm, fill: rgb("eef")),
  caption: [Dieses Rechteck steht stellvertretend für ein eingefügtes Bild (z.B. ein Strömungsprofil um einen Zylinder).],
) <fig:zylinder>

Wie in @fig:zylinder zu sehen ist, können Bilder einfach zentriert
eingebunden und mit einer Unterschrift (Caption) versehen werden. Im
Abbildungsverzeichnis am Anfang des Dokuments wird diese Grafik automatisch
registriert.

Hier ein Beispiel:

#figure(
  image("../Images/CylinderImage.jpg", width: 60%),
  caption: "Das ist ein Testbild. (Quelle: Eigenes Bild)"
)

== Tabellen

Auch Tabellen sind für die wissenschaftliche Praxis unerlässlich, um Daten
strukturiert darzustellen. Ein Beispiel ist in @tab:beispiel zu sehen.

#figure(
  table(
    columns: (auto, auto, auto),
    inset: 10pt,
    align: horizon,
    [*Parameter*], [*Wert*], [*Einheit*],
    [Geschwindigkeit $v$], [10.5], [m/s],
    [Dichte $rho$], [1.225], [$"kg" / m^3$],
    [Druck $P$], [101325], [Pa]
  ),
  caption: [Übersicht der verwendeten Simulationsparameter.]
) <tab:beispiel>

== Diskussion

Die hier dargestellten Ergebnisse sollten abschließend eingeordnet und
kritisch diskutiert werden: Was funktioniert gut, wo liegen Grenzen, welche
Annahmen wurden getroffen?
