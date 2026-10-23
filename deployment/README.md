# FTPS-Deployment

Veröffentlicht den geprüften Build (`frontend/dist`) per FTPS nach `https://hendrik.kreativdeck.dev`. Alles liegt in `ftps_deploy.py` (nur Python-Standardbibliothek, keine Fremd-Action) und im Job `deploy` von `.github/workflows/ci.yml`.

**Status: implementiert, aber nicht aktiv.** Der Job `deploy` wird übersprungen, solange die Repository-Variable `DEPLOY_ENABLED` nicht exakt `true` ist. Sie bleibt `false` bzw. ungesetzt, bis die Aktualisierung gleichnamiger Dateien (siehe unten) ausdrücklich bestätigt ist.

## Ziel

- Hosting ist der bestätigte FTPS-Server (explizites TLS, Port 21, PROT P, passiv; Zertifikat gültig für `server.kumarmedia.de`). Es ist **nicht** ALL-INKL und **nicht** das JMC-Ziel; für JMC gibt es hier keine Konfiguration.
- Zulässig ist ausschließlich der Serverordner `/hendrik.kreativdeck.dev` und die Adresse `https://hendrik.kreativdeck.dev`. Das ist im Skript fest hinterlegt: `FTP_REMOTE_DIR=/` oder ein anderer Ordner/Unterordner sowie jede andere `SITE_URL` werden vor dem Verbindungsaufbau abgelehnt.
- `FTP_HOST` muss dem Zertifikatsnamen entsprechen (`server.kumarmedia.de`); das Zertifikat wird mit `ssl.create_default_context()` geprüft, mindestens TLS 1.2.

## Was passiert mit Serverdateien

| Fall | Verhalten |
| --- | --- |
| Datei im Build, auf dem Server nicht vorhanden | wird neu angelegt |
| **Gleichnamige** Datei im Build und auf dem Server (z. B. `index.html`, `.htaccess`, `_astro/…`) | wird **ersetzt** (aktualisiert), erst nach vollständigem Temp-Upload per Umbenennen |
| Datei/Ordner nur auf dem Server (zusätzliche Dateien, Uploads, Fremdinhalte) | **bleibt unverändert**; wird nie gelöscht, verschoben oder überschrieben |

Es gibt keinen Spiegelmodus und keine Löschfunktion. Das Skript löscht ausschließlich eigene Namen: die Zufallsprobe dieses Laufs (`kd-deploy-probe-<zufall>.txt`) und eigene temporäre Dateien (`.kd-tmp-<lauf>-<nr>`). Ältere Reste solcher Namen aus abgebrochenen Läufen werden nicht angefasst. Der Deployer erzeugt keinen Zustand im Webroot. Der Zielordner selbst wird nie angelegt; fehlende Unterordner des Builds werden mit `MKD` ergänzt.

## Modi

Im Repository-Wurzelordner (Python 3, Standardbibliothek):

```sh
# 1. Rein lokal: Build und Konfigurationsformat prüfen, keine Verbindung
python3 deployment/ftps_deploy.py --offline --source frontend/dist

# 2. Plan (Standard): lesende FTPS-Verbindung, Vergleich Build ↔ Server, keine Schreibvorgänge
python3 deployment/ftps_deploy.py --source frontend/dist

# 3. Schreibmodus – nur nach ausdrücklicher Freigabe
DEPLOY_ENABLED=true python3 deployment/ftps_deploy.py --source frontend/dist --deploy
```

Der Plan meldet: neue Dateien, gleichnamige Dateien (die ein Deploy ersetzen würde; getrennt nach gleicher/abweichender Größe), neue Ordner, zusätzliche Serverinhalte (bleiben) und Typkonflikte (Datei vs. Ordner; sie brechen ab). Technisch ist der Plan lesend abgesichert: Er arbeitet mit einem Wrapper ohne Schreibmethoden, und der FTP-Client erlaubt Schreiben ohnehin nur im Zielordner und nur auf eigene Namen.

Exitcodes: `0` ok, `1` Fehler/Abbruch, `2` Konfiguration fehlt oder ist unzulässig.

### Konfiguration (Umgebungsvariablen)

| Variable | Art | Hinweis |
| --- | --- | --- |
| `FTP_HOST` | Secret | Hostname, passend zum Zertifikat |
| `FTP_USER`, `FTP_PASSWORD` | Secret | werden nie ausgegeben |
| `FTP_PORT` | Variable | Standard 21 |
| `FTP_REMOTE_DIR` | Variable | exakt `/hendrik.kreativdeck.dev` |
| `SITE_URL` | Variable | exakt `https://hendrik.kreativdeck.dev`; muss zum Build passen (Abgleich mit `robots.txt`) |
| `DEPLOY_ENABLED` | Variable | nur `true` erlaubt `--deploy` |

Lokal können die Werte in der ignorierten `.env.ftp` liegen. **Diese Datei nie per `source` in die Shell laden, nie committen und nie ausgeben**; Werte stattdessen gezielt als Umgebungsvariablen an den Befehl übergeben (z. B. mit einem Werkzeug, das die Datei ohne Shell-Auswertung liest). Fehlende Zugangsdaten stoppen den Lauf mit Exitcode 2, bevor eine Verbindung entsteht.

## Ablauf im Schreibmodus

1. `DEPLOY_ENABLED` exakt `true`, Konfiguration und Ziel prüfen (sonst Abbruch ohne Verbindung).
2. Build prüfen: nur reguläre Dateien und Ordner (keine Symlinks), `.htaccess` und `index.html` vorhanden, keine `.env*`, `.git*` (außer `.gitkeep`), `.DS_Store`, `._*`, `node_modules`, keine Steuerzeichen/Backslashes in Namen, keine reservierten Namen des Deployers.
3. FTPS verbinden (`AUTH TLS`, Login, `PROT P`, passiv), Zielordner und gemeldetes Arbeitsverzeichnis exakt prüfen, Plan lesend erstellen. Konflikte brechen ab.
4. **Webroot-Bestätigung:** Zufallsprobe im Zielordner anlegen, per HTTPS unter `SITE_URL` abrufen und den Zufallswert vergleichen, dann mit einer zweiten Probe das Ersetzen per Umbenennen testen und die Probe löschen. Liefert `SITE_URL` die Probe nicht aus (falsches Ziel/Webroot), bricht der Lauf ab, bevor irgendeine Websitedatei verändert wurde. Es werden keine bestehenden Dateien dafür verwendet.
5. Fehlende Ordner anlegen, dann Dateien übertragen: Assets zuerst, dann HTML (Startseite zuletzt), `.htaccess` ganz zuletzt. Jede Datei wird zuerst als temporäre Datei im selben Ordner hochgeladen, per `SIZE` geprüft und dann umbenannt. Bei Fehlern wird nur die eigene Temp-Datei entfernt.
6. HTTPS-Nachprüfung ohne feste Inhalte: Startseite liefert HTML, `robots.txt`, `sitemap.xml` und je ein CSS/JS aus `_astro/` stimmen byteweise mit dem Build überein, `/.htaccess` ist nicht öffentlich (403/404), eine unbekannte Adresse liefert 404. Schlägt sie fehl, endet der Lauf mit Exitcode 1; es gibt **keinen automatischen Rollback**.

Läufe sind wiederholbar (idempotent). Nach einem Abbruch einfach erneut starten; angefangene Dateien sind nie halb ersetzt, weil erst nach vollständigem Upload umbenannt wird. Ältere Läufe erneut auszuführen (Re-run) deployt deren Stand und kann einen neueren überschreiben.

## GitHub-Einrichtung (später durch den Hauptagenten)

- Secrets: `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD`. Variablen: `FTP_PORT`, `FTP_REMOTE_DIR`, `SITE_URL`.
- `DEPLOY_ENABLED` erst auf `true` setzen, nachdem bestätigt ist, dass gleichnamige Dateien auf dem Server aktualisiert werden dürfen.
- Der Job hängt von `build` ab (Check, Build, Parity, Artifact), läuft nur bei `push` auf `main` oder `workflow_dispatch` auf `main` (nie bei Pull Requests) und lädt exakt das Artifact `website-dist-<commit>` desselben Laufs (`actions/download-artifact` v8.0.2, auf Commit-SHA gepinnt; `action.yml` am SHA geprüft). Das Skript stammt aus dem Checkout desselben Commits.
- Rechte: `contents: read`. Secrets liegen nur als Umgebungsvariablen im Deploy-Schritt, nie in der Shell-Interpolation. Der Workflow-Concurrency-Abbruch gilt nur für Pull Requests; der Deploy-Job nutzt eine eigene Gruppe mit `cancel-in-progress: false`, laufende Deploys werden also nie abgebrochen.
- Stand: Die bestehende CI (Check, Build, Parity) lief lokal grün, der erste GitHub-Lauf steht noch aus.

## Tests

```sh
python3 -m unittest discover -s deployment -p 'test_*.py'
```

Die Tests laufen ohne Netzwerk und ohne echte Zugangsdaten (Fake-FTP und Fake-HTTP). Sie decken ab: Konfiguration und Zielgrenzen, Build-Validierung (Symlinks, Metadaten, fehlende `.htaccess`/`index.html`), Plan ohne Schreibvorgänge, Probe vor allen Uploads und deren Bereinigung, falsches HTTP-Ziel, Upload-Reihenfolge, Temp-Upload mit Umbenennen, keine Löschung fremder Dateien, Abbruchbereinigung, fehlgeschlagene Nachprüfung, keine Zugangsdaten in der Ausgabe sowie TLS-/Passiv-Ablauf und Pfadgrenzen des FTP-Clients. Die Tests laufen auch im CI-Job `build`.

## Grenzen

- Server ohne `MLSD` werden über `NLST` gelesen (langsamer, versteckte Dateien können im Plan fehlen).
- Unterstützt der Server `RNTO` auf vorhandene Dateien nicht, bricht der Lauf bereits bei der Webroot-Bestätigung ab, bevor Websitedateien verändert werden. Es gibt dafür bewusst keinen Lösch-Fallback.
- Alle Dateien werden bei jedem Deploy übertragen (ca. 850 Dateien, rund 20 MB); es gibt keinen Inhaltsvergleich mit dem Server.
