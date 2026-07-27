#import "../template.typ": hinweis

= Grundlagen <sec:grundlagen>

#hinweis[
  Theoretische und technische Grundlagen, die zum Verständnis der Arbeit
  nötig sind: Begriffsdefinitionen, mathematische/physikalische Basis,
  verwendete Methoden oder Technologien auf Konzeptebene.
]

Um das Thema tiefgreifend analysieren zu können, ist es notwendig, die
mathematischen und physikalischen Prinzipien zu verstehen.

== Mathematische Formeln

Die Navier-Stokes-Gleichungen sind ein fundamentales Konzept der
Strömungsmechanik. @eq:navier_stokes zeigt die inkompressiblen
Navier-Stokes-Gleichungen in Tensornotation.

$ partial u_i / partial t + u_j partial u_i / partial x_j = - 1/rho partial P / partial x_i + nu (partial^2 u_i) / (partial x_j^2) $ <eq:navier_stokes>

Solche komplexen Formeln lassen sich leicht in Typst darstellen und
referenzieren. Hierbei wird ein Ansatz verwendet, der sehr stark an die
Schreibweise auf dem Papier erinnert, aber intern wie ein modernes
Programmierframework funktioniert.

Quellen lassen sich mit der Syntax `@key` (z.B. `@ghia_1982`) referenzieren, wobei der Schlüssel
in `references.bib` hinterlegt sein muss - wie z. B. hier gezeigt @ghia_1982.
