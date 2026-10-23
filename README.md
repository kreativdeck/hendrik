# Hendrik Lampe Website

Originalgetreue Migration der vorhandenen PHP-/Tailwind-Website nach Astro 7, Tailwind CSS 4 und TypeScript. Die Anwendung liegt in `frontend/` und baut statische Seiten. Der alte Projektordner wird zum Entwickeln und Bauen nicht benötigt.

## Lokal starten

Node.js 24 und npm verwenden. Nach einem frischen Checkout:

```sh
cd frontend
npm ci
npm run dev
```

Die lokale Adresse aus der Terminalausgabe öffnen. Für den produktionsgleichen lokalen Stand:

```sh
npm run check
npm run build
npm run test:parity
npm run preview
```

`dist/` enthält die erzeugte Website. `astro dev` und `astro preview` können in dieser Astro-Version als Hintergrundprozess starten; beenden mit `npm run dev -- stop` bzw. `npm run preview -- stop`.

## Inhalte und Komponenten

- `src/pages/`: öffentliche Seiten-URLs, einschließlich `404.astro`. Die Bereiche heißen `interior`, `formcultur`, `materials` und `landoak`; die Bildordner unter `public/assets/images/` behalten ihre ursprünglichen Namen.
- `src/components/`: Header, Footer, Logo, Hero, Bildausgabe, Bereichsübersichten, Galerien und Lightbox.
- `src/content/sections/*.json`: Texte, Farben, Titelbilder, Bildordner und originale Alt-Texte der Bereiche.
- `src/content/blog/*.json`: Blogbeiträge mit Titel, Datum, Beschreibung und HTML-Inhalt. Der Dateiname bestimmt die URL; neue Beiträge werden automatisch gebaut und in die Sitemap aufgenommen.
- `src/content/pages.json`: originale SEO-Daten für die individuellen Seiten. Bereichs- und Beitragsmetadaten erzeugt `src/lib/seo.ts` aus den Inhaltsdateien.
- `src/content/settings/`: ursprüngliche Website- und Organisationsdaten für JSON-LD.
- `src/styles/global.css`: originale Schriftdefinitionen, Farben, Abstände, Typografie und Tailwind-Varianten.
- `src/scripts/main.js`: adaptive Navigation, Tastatursteuerung, Scrollverhalten und Lightbox.
- `public/assets/`: unveränderte Originalbilder, lokale Schriften, SVGs und Icons.
- `integrations/image-pipeline.mjs`: Astro-Verarbeitung für Bildmetadaten und AVIF-/WebP-Varianten mit 150/960/1920 Pixeln, ohne Hochskalierung. Die bisherigen öffentlichen Bildpfade bleiben erhalten.

Alte Bereichs-URLs (`/holzobjekte/`, `/formkultur/`, `/materialen/` samt Unterseiten) leitet `public/.htaccess` per 301 auf `/interior/`, `/formcultur/` und `/materials/` weiter. Die Regeln stehen vor den Datei-/Verzeichnisprüfungen und benötigen Apache mit `mod_rewrite`. Hero-Bildbereiche zeigen keinen sichtbaren Text; die H1 bleibt als `sr-only` erhalten.

Sitemap und robots.txt entstehen als statische Astro-Endpunkte. CSS und JavaScript werden von Vite kompiliert und mit Inhalts-Hashes ausgegeben. PHP und `build.php` sind für den Website-Build nicht erforderlich.

Die originale SEO-Basis `https://www.deinedomain.de` bleibt Standard. Die Adresse lässt sich über `SITE_URL` setzen, lokal in einer `.env` (Beispiel: `frontend/.env.example`) oder als Umgebungsvariable beim Build; sie aktualisiert Sitemap, robots.txt und JSON-LD. Im GitHub-Workflow kommt sie aus der Repository-Variable `SITE_URL` (siehe [GitHub-Workflow](#github-workflow)).

## Prüfungen

`npm run test:parity` vergleicht den fertigen Build mit `tests/site-expectations.json`: alle 34 Seiten, Inhalte, Bilder/Alt-Texte, Navigation, SEO/JSON-LD, Galeriedaten, lokale Ziele und Sitemap. Die Erwartungen stammen aus dem PHP-Vergleich und wurden gezielt um die beauftragten Änderungen ergänzt. Die ursprüngliche Referenz bleibt unverändert in `tests/legacy-parity.json`. Das Skript benötigt Python 3.

`test:parity` liest `SITE_URL` genauso wie der Build (Umgebungsvariable vor `.env`, sonst die Original-Basis) und prüft damit die Origin im fertigen `dist/`. Die Fixture bleibt unverändert auf `https://www.deinedomain.de`; zur Laufzeit wird nur der Origin-Anfang von URL-Werten (JSON-LD) ausgetauscht, Texte und alle übrigen Erwartungen bleiben unberührt. Zusätzlich müssen alle Sitemap-URLs und die Sitemap-Zeile in `robots.txt` zur Origin passen. Bauen und prüfen muss daher mit derselben Adresse erfolgen:

```sh
# Original-Basis
npm run build && npm run test:parity

# Produktions-Origin
SITE_URL=https://hendrik.kreativdeck.dev npm run build
SITE_URL=https://hendrik.kreativdeck.dev npm run test:parity
```

Ein Build mit anderer Origin als beim Prüfen schlägt mit Abweichungen in `schema`, Sitemap und `robots.txt` fehl.

Für die Browserprüfungen zuerst `npm run preview -- --host 127.0.0.1 --port 4321` starten:

```sh
npm run test:browser
```

Die Prüfung verwendet installiertes Google Chrome unter macOS. Ein anderer Chromium-Pfad ist über `CHROME_PATH` möglich; die Website-Adresse über `SITE_TEST_URL`. Ergebnisse und Screenshots liegen ausschließlich in `.migration/qa/`, außerhalb der Veröffentlichung und von Git ausgeschlossen.

`npm run test:visual` prüft alle 34 Seiten bei 1440/768/390/320 Pixeln auf überlaufende Inhalte, defekte Bilder und JavaScript-Fehler. Screenshots der geänderten Seiten und die Ergebnisse liegen unter `.migration/qa/current/`. Ein pixelgleicher Vergleich mit der alten Website ist nach den beauftragten Gestaltungsänderungen nicht mehr das Abnahmekriterium. Die ursprünglichen Vergleichsergebnisse bleiben als Migrationsartefakte erhalten.

## Kontakt-API

Die bisherige `api/contact.php` ist bytegleich in `public/api/contact.php` erhalten. Die Quellwebsite enthält aktuell kein Kontaktformular; Kontakt erfolgt über Telefon- und E-Mail-Links. Nur die separat vorhandene API braucht beim späteren Hosting PHP mit Mailkonfiguration. Astro dev/preview führen diese Datei nicht aus. Sie darf nur auf einem Host mit PHP-Ausführung betrieben werden.

Die API-Prüfung benötigt einen lokal gestarteten PHP-Server für `frontend/dist` unter Port 4322 und läuft mit `npm run test:api`. `CONTACT_TEST_URL` kann die Adresse überschreiben. Geprüft werden ausschließlich Validierung und Honeypot, ohne Nachrichten zu versenden.

## GitHub-Workflow

`.github/workflows/ci.yml` läuft bei Pushes auf `main`, bei Pull Requests und manuell (`workflow_dispatch`) auf `ubuntu-latest` mit Node.js aus `.nvmrc` (24). Er führt im Ordner `frontend/` nacheinander `npm ci`, `npm run check`, `npm run build` und `npm run test:parity` aus. Erst nach erfolgreicher Prüfung wird `frontend/dist` samt `.htaccess` als Artifact `website-dist-<commit>` bereitgestellt (14 Tage Aufbewahrung); vorher prüft ein Schritt, dass `dist` keine `._*`-, `.DS_Store`- oder `.env`-Dateien enthält. Zusätzlich laufen die Tests des Deployment-Skripts (`python3 -m unittest discover -s deployment`). Der Workflow hat nur Leserechte (`contents: read`), die Actions sind auf geprüfte Commit-SHAs gepinnt (Versionen als Kommentar). Secrets verwendet ausschließlich der optionale Job `deploy` (siehe unten); der Build-Job benötigt keine.

`SITE_URL` stammt aus der Repository-Variable `SITE_URL` (GitHub: Settings → Secrets and variables → Actions → Variables). Ohne Variable gilt `https://hendrik.kreativdeck.dev`. Build und Parity-Prüfung verwenden denselben Wert. Die Browser-, Sichtprüfungs- und API-Skripte (`test:browser`, `test:visual`, `test:api`) setzen macOS-Chrome bzw. einen PHP-Server voraus und gehören nicht zur CI.

Beim Aktualisieren der Actions jeweils Release prüfen, den Commit-SHA des Tags über die GitHub-API ermitteln und SHA samt Versionskommentar gemeinsam ändern.

### Hosting und Deployment (FTPS, noch nicht aktiv)

Das Hosting ist der bestätigte FTPS-Server (Zielordner `/hendrik.kreativdeck.dev`, Adresse `https://hendrik.kreativdeck.dev`), nicht ALL-INKL und nicht das JMC-Ziel. Die Website braucht weiterhin Apache mit `mod_rewrite` für `.htaccess` und PHP für `api/contact.php`; GitHub Pages ist deshalb nicht vorgesehen.

Der Workflow enthält den Job `deploy` (Python-Standardbibliothek, keine Fremd-Deploy-Action). Er ist **inaktiv**, solange die Repository-Variable `DEPLOY_ENABLED` nicht exakt `true` ist, und läuft nie für Pull Requests, nur für `push`/`workflow_dispatch` auf `main` nach erfolgreichem Job `build`. Er lädt das geprüfte Artifact `website-dist-<commit>` desselben Laufs und überträgt es per FTPS. Dabei wird nichts auf dem Server gelöscht: Gleichnamige Builddateien werden ersetzt, zusätzliche Serverdateien bleiben unverändert. Vor dem ersten Dateiupdate bestätigt eine Zufallsprobe den Webroot. Details, Modi (`--offline`, Plan, `--deploy`), Konfiguration und Grenzen: [deployment/README.md](deployment/README.md).

Lokal ohne Server prüfen (keine Verbindung, keine Schreibvorgänge) und planen (nur lesend, benötigt Zugangsdaten als Umgebungsvariablen):

```sh
python3 deployment/ftps_deploy.py --offline --source frontend/dist
python3 deployment/ftps_deploy.py --source frontend/dist
```

Die lokale, von Git ignorierte `.env.ftp` enthält Zugangsdaten: nicht committen, nicht ausgeben und nicht per `source` in die Shell laden.

Einzurichten sind später auf GitHub die Secrets `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` sowie die Variablen `FTP_PORT`, `FTP_REMOTE_DIR`, `SITE_URL`. `DEPLOY_ENABLED` bleibt `false`, bis die Aktualisierung gleichnamiger Dateien auf dem Server bestätigt ist. Stand: Die CI lief lokal grün, der erste Lauf auf GitHub steht noch aus; bis zur Aktivierung bleibt der Upload von `dist` manuell.

Offene Quelllücken, bewusste Korrekturen und die abschließenden Prüfergebnisse stehen in [MIGRATION.md](MIGRATION.md). Es wurde nichts veröffentlicht.
