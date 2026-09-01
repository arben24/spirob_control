# Git & SSH: Committen und Pushen einrichten

Um Änderungen zu GitLab hochzuladen (**pushen**), brauchst du einen sicheren
Weg, dich gegenüber GitLab auszuweisen. Am komfortabelsten geht das mit
**SSH-Schlüsseln**: Einmal einrichten, danach nie wieder Passwort eingeben.

Diese Anleitung ist bewusst sehr kleinschrittig gehalten – auch wenn du
vorher noch nie mit der Kommandozeile/Terminal gearbeitet hast, solltest du
hier durchkommen.

!!! note "Was ist SSH überhaupt?"
    SSH ist ein Verfahren, um dich sicher gegenüber einem Server (hier:
    GitLab) auszuweisen – ohne jedes Mal ein Passwort einzutippen. Dazu
    erzeugst du ein **Schlüsselpaar**: einen **privaten Schlüssel** (bleibt
    geheim auf deinem Rechner) und einen **öffentlichen Schlüssel** (den
    hinterlegst du bei GitLab). Nur wer den passenden privaten Schlüssel hat,
    kann sich damit anmelden.

## Schritt 1: Terminal öffnen

=== "Windows"
    1. **Git für Windows installieren**, falls noch nicht vorhanden:
       [git-scm.com/download/win](https://git-scm.com/download/win)
       herunterladen und mit den Standardeinstellungen installieren.
    2. Startmenü öffnen, **„Git Bash"** eingeben und starten.
    3. Es öffnet sich ein schwarzes Fenster (Terminal) – hier tippst du alle
       folgenden Befehle ein.

=== "Linux"
    1. Terminal öffnen (z. B. über das Anwendungsmenü nach „Terminal"
       suchen, oder Tastenkürzel `Strg + Alt + T`).
    2. Prüfen, ob Git installiert ist:
       ```bash
       git --version
       ```
       Falls nicht installiert (Fehlermeldung), z. B. unter Ubuntu/Debian:
       ```bash
       sudo apt update && sudo apt install git
       ```

## Schritt 2: SSH-Schlüsselpaar erzeugen

=== "Windows"
    In der Git Bash eingeben (E-Mail durch deine eigene ersetzen):
    ```bash
    ssh-keygen -t ed25519 -C "vorname.nachname@stud.htwk-leipzig.de"
    ```
    Jetzt kommen drei Nachfragen – einfach dreimal **Enter** drücken (Standard
    übernehmen, keine Passphrase setzen):
    ```text
    Enter file in which to save the key (...): [Enter]
    Enter passphrase (empty for no passphrase): [Enter]
    Enter same passphrase again: [Enter]
    ```

=== "Linux"
    Im Terminal eingeben (E-Mail durch deine eigene ersetzen):
    ```bash
    ssh-keygen -t ed25519 -C "vorname.nachname@stud.htwk-leipzig.de"
    ```
    Jetzt kommen drei Nachfragen – einfach dreimal **Enter** drücken (Standard
    übernehmen, keine Passphrase setzen):
    ```text
    Enter file in which to save the key (...): [Enter]
    Enter passphrase (empty for no passphrase): [Enter]
    Enter same passphrase again: [Enter]
    ```

!!! note "Passphrase leer lassen?"
    Der Einfachheit halber wird hier keine Passphrase gesetzt. Das ist für
    einen Übungs-/Projekt-Rechner in Ordnung. Auf einem gemeinsam genutzten
    Rechner solltest du stattdessen eine Passphrase vergeben.

## Schritt 3: Öffentlichen Schlüssel kopieren

=== "Windows"
    In der Git Bash:
    ```bash
    clip < ~/.ssh/id_ed25519.pub
    ```
    Der öffentliche Schlüssel ist jetzt in der Zwischenablage (wie nach
    einem `Strg + C`).

=== "Linux"
    Im Terminal:
    ```bash
    cat ~/.ssh/id_ed25519.pub
    ```
    Den ausgegebenen Text komplett markieren (von `ssh-ed25519` bis zur
    E-Mail-Adresse am Ende) und mit `Strg + Umschalt + C` kopieren (im
    Terminal ist das normale `Strg + C` oft anders belegt).

## Schritt 4: Schlüssel bei GitLab hinterlegen

Ab hier ist es für Windows und Linux identisch – im Browser:

1. Bei GitLab anmelden.
2. Oben rechts auf deinen **Avatar** klicken → **Edit profile**.
3. Links im Menü **SSH Keys** auswählen.
4. In das Feld „Key" den kopierten Text einfügen (`Strg + V`).
5. Optional einen Titel vergeben (z. B. „Mein Laptop") und ein
   Ablaufdatum setzen.
6. Auf **„Add key"** klicken.

## Schritt 5: Verbindung testen

=== "Windows"
    In der Git Bash:
    ```bash
    ssh -T git@gitlab.dit.htwk-leipzig.de
    ```

=== "Linux"
    Im Terminal:
    ```bash
    ssh -T git@gitlab.dit.htwk-leipzig.de
    ```

Beim allerersten Verbindungsversuch kommt eine Sicherheitsabfrage:
```text
The authenticity of host 'gitlab.dit.htwk-leipzig.de' can't be established.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```
Hier `yes` eingeben und mit Enter bestätigen. Bei Erfolg erscheint:
```text
Welcome to GitLab, @dein-username!
```

!!! warning "Stattdessen kommt „Permission denied (publickey)"?"
    Siehe Abschnitt [Problembehandlung](#problembehandlung) weiter unten.

## Schritt 6: Projekt klonen (herunterladen)

Falls du das Projekt noch nicht lokal hast:

1. Auf der GitLab-Projektseite den blauen **„Code"**-Button anklicken.
2. Unter „Clone with SSH" die Adresse kopieren (beginnt mit `git@gitlab...`).
3. Im Terminal/Git Bash:
   ```bash
   git clone git@gitlab.dit.htwk-leipzig.de:<gruppe>/<projekt>.git
   cd <projekt>
   ```

## Schritt 7: Name und E-Mail für Commits hinterlegen

Einmalig (gilt danach für alle Projekte auf diesem Rechner):

```bash
git config --global user.name "Vorname Nachname"
git config --global user.email "vorname.nachname@stud.htwk-leipzig.de"
```

## Schritt 8: Ändern, committen, pushen

Der eigentliche Arbeitsablauf, den du ab jetzt immer wieder nutzt:

```bash
# 1. Datei(en) im Projektordner ändern (z.B. README.md)

# 2. Änderungen zum Commit vormerken
git add .

# 3. Commit mit kurzer Beschreibung erstellen
git commit -m "Kurze Beschreibung, was sich geändert hat"

# 4. Commit zu GitLab hochladen
git push
```

Danach kannst du auf der GitLab-Projektseite (Tab „Repository" bzw. direkt
auf der Startseite) sehen, dass deine Änderung angekommen ist.

## Problembehandlung

**„Permission denied (publickey)"**
: Der öffentliche Schlüssel wurde nicht (korrekt) bei GitLab hinterlegt.
  Schritt 3 und 4 wiederholen – dabei genau prüfen, dass der komplette Text
  (inkl. `ssh-ed25519` am Anfang) kopiert wurde, ohne Zeilenumbruch
  dazwischen.

**„Host key verification failed"**
: Bei der allerersten Verbindung muss die Sicherheitsabfrage mit `yes`
  bestätigt werden (siehe Schritt 5). Falls das schon passiert ist und der
  Fehler trotzdem kommt, kurz melden – dann schauen wir gemeinsam drauf.

**Nach jedem Befehl wird erneut nach der Passphrase gefragt**
: Nur relevant, falls beim Erzeugen des Schlüssels (Schritt 2) doch eine
  Passphrase gesetzt wurde. Mit folgendem Befehl merkt sich das System die
  Passphrase für die aktuelle Terminal-Sitzung:
  ```bash
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/id_ed25519
  ```

**`git push` sagt „rejected" oder „non-fast-forward"**
: Jemand anderes (oder du selbst an anderer Stelle) hat zwischenzeitlich
  bereits etwas gepusht. Erst die Änderungen holen, dann erneut pushen:
  ```bash
  git pull
  git push
  ```
