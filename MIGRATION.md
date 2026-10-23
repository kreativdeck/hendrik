# Migration der Hendrik-Website

Die Website wurde im bereits eingerichteten Projekt `frontend/` mit Astro 7.4.1, Tailwind CSS 4.3.3 und TypeScript umgesetzt. Es wurde nichts veröffentlicht.

Die folgenden Migrationsabschnitte dokumentieren die Abnahme vom 21. Oktober 2026. Die anschließend beauftragten Änderungen stehen am Ende dieses Berichts.

## Übertragener Umfang

- Alle 28 ursprünglichen PHP-Seiten einschließlich 404 sowie beide Blogbeiträge: insgesamt 30 HTML-Seiten mit den bisherigen Verzeichnis-URLs.
- Vollständige Seiteninhalte einschließlich Impressum und Datenschutz, Referenzliste und vorhandener Platzhalter.
- 211 Bilddateien, alle 8 lokalen Schriftdateien, SVG-Icons, Logo, Farben, Typografie, Abstände und responsive Raster. Die zusätzlichen `.DS_Store`-Dateien der Quelle sind keine Bildinhalte und werden nicht veröffentlicht.
- Header und Footer, aktive Navigationslinks, adaptive Mobilnavigation, Dropdowns, Fokussteuerung, Scrollverhalten und Jahreszahl.
- Alle 16 Galerien mit identischer Bildreihenfolge und identischen Alt-Texten, Lightbox, Pfeiltasten, Umlaufnavigation, Bildfehleranzeige und Hash-Direktlinks.
- Originale Seitentitel, Meta-Beschreibungen, noindex-Angaben und JSON-LD einschließlich Organisations-, Website-, Seiten-, Blog- und Breadcrumb-Daten.
- 27 indexierbare Sitemap-URLs und die bisherigen robots.txt-Regeln. Impressum, Datenschutz und 404 bleiben ausgeschlossen.
- Alle 229 ursprünglichen öffentlichen Dateien einschließlich `.htaccess` bytegleich; die Kontakt-API ist zusätzlich bytegleich erhalten.

## Ersatz für PHP und build.php

Die PHP-Seiten und -Templates wurden durch native Astro-Seiten und gemeinsame Komponenten ersetzt. Bereichsdaten, Bildbeschreibungen und Beiträge liegen in JSON-Inhaltsdateien. Blogrouten und Sitemap entstehen automatisch aus den Beitragsdateien; Titel und JSON-LD der Bereiche und Beiträge werden aus den jeweiligen Inhalten erzeugt.

Vite kompiliert Tailwind und JavaScript und versieht die Ausgaben mit Inhalts-Hashes. Eine Astro-Integration liest die Bildmetadaten und erzeugt beim Build 484 WebP-/AVIF-Varianten mit den ursprünglichen Breiten 150, 960 und 1920 Pixeln und Qualitätswerten 82/55. Kleinere Bilder werden nicht hochskaliert. Originale und Varianten behalten die bisherigen öffentlichen Bildpfade. In der Entwicklung werden Varianten bei Bedarf lokal erzeugt.

robots.txt und sitemap.xml sind statische Astro-Endpunkte. Der Website-Build benötigt weder PHP noch den alten Projektordner. Die separat erhaltene Kontakt-API braucht bei einer späteren Nutzung weiterhin PHP und einen eingerichteten Mailversand.

## Bewusste Korrekturen

1. Das originale Mobilmenü konnte beim direkten Wechsel zwischen zwei geöffneten Dropdowns den zweiten Klick verlieren: Der vorherige Bereich klappte schon beim Fokussieren ein und verschob das angeklickte Ziel. Die neue Fassung hält die Zeilen bis zur Klickverarbeitung stabil. Tastaturbedienung und Fokusrückgabe bleiben erhalten.
2. Leerzeichen und Umlaute in responsiven Bild-URLs werden im `srcset` korrekt URL-kodiert. So funktionieren auch Bilder in Ordnern wie `Two Stripes Oak` zuverlässig.
3. Sehr lange Wörter und URLs in Impressum und Datenschutz dürfen auf schmalen Displays umbrechen, statt über den Seitenrand hinauszulaufen. Texte, Farben und Schriftgrößen bleiben unverändert.
4. Der technische Paketname wurde von `hnedrik-website` zu `hendrik-website` berichtigt.

## Bereits in der Quelle offene Inhalte

- In der Quelle waren `/formkultur/`, `/formkultur/lovseth/` und `/formkultur/solveig/` verlinkt, ohne Seiten oder Inhalte. Am 23. Oktober 2026 wurden Formkultur-Übersicht und Løvseth-Galerie mit den neu bereitgestellten Bildern ergänzt. Alle elf Motive gehören laut Nutzer zu Løvseth. Der bislang ins Leere führende Solveig-Menüpunkt wurde entfernt; dafür wurden keine Inhalte erfunden.
- Die SEO-Basis ist weiterhin `https://www.deinedomain.de`. Die echte Domain ist in der Quelle nicht festgelegt. Eine spätere Festlegung über `SITE_URL` aktualisiert Sitemap, robots.txt und JSON-LD.
- Im ursprünglichen Datenschutz fehlte der Name und die Anschrift des Hosters. Dieser Punkt wurde am 22. Oktober 2026 mit der beauftragten ALL-INKL.COM-Angabe behoben.
- Leistungen und Blog enthalten Beispielinhalte; mehrere Titel verwenden noch „Meine Website“. Das Webmanifest verwendet „MyWebSite“/„MySite“. Diese Angaben wurden originalgetreu erhalten.
- Die Quellwebsite enthält auf der Kontaktseite Telefon- und E-Mail-Links, aber kein Kontaktformular. Die daneben vorhandene PHP-API enthält noch allgemeine Empfänger-/Absenderadressen und Autoresponder-Texte. Der reale Mailversand wurde nicht ausgelöst und ist vor einer späteren produktiven Nutzung separat zu konfigurieren und zu prüfen.

Diese Punkte sind Ausgangslücken der gelieferten Website und keine ausgelassenen Seiten der Migration. Sie benötigen erst bei einer späteren inhaltlichen Ergänzung oder Veröffentlichung Entscheidungen.

## Prüfung und Grenzen

`tests/legacy-parity.json` enthält unabhängig aus der ausgeführten PHP-Referenz gewonnene Erwartungen. `npm run test:parity` prüft den fertigen Astro-Build dagegen: Seitentexte, Bildquellen, Alt-Texte, Bildabmessungen/-klassen, Galeriedaten, Links, Metadaten, JSON-LD, Sitemap, Originaldateien und API-Prüfsumme. Es gibt 1.461 lokale Seiten-/Asset-Referenzen; nur die drei oben genannten Quelllücken werden als bekannt behandelt.

Die Browserprüfungen verwenden Google Chrome/Chromium unter macOS. Alle 30 Seiten werden mit 1440, 768, 390 und 320 Pixeln verglichen. Gemessen werden Positionen/Größen, überlaufende Inhalte und geladene Bilder; zusätzlich entstehen Screenshots. Sehr lange Seiten werden in Abschnitten aufgenommen. Navigation und alle 16 Galerien werden zusätzlich interaktiv bei 1920 und 390 Pixeln geprüft.

Die visuelle Referenz wurde ausschließlich aus einer Kopie der PHP-Templates innerhalb des neuen Projekts erzeugt, zusammen mit dem originalen Tailwind-CSS. Für den Bildvergleich nutzen beide Fassungen dieselben erzeugten Bildvarianten: Das lokale PHP-GD unterstützt kein AVIF, weshalb der alte Komplettbuild hier nicht unverändert ausführbar ist. Unterschiede zwischen Sharp und einem früheren Produktions-Bildencoder sind daher nicht quantitativ bewertet. Es wurden keine physischen Mobilgeräte oder Safari/Firefox getestet.

Prüfartefakte und die lokale Referenz liegen unter `.migration/`, sind von Git ausgeschlossen und werden nicht mit der Website veröffentlicht. Der alte Projektordner wurde ausschließlich gelesen; seine 310 erfassten Dateien sind per SHA-256 kontrolliert.

## Ergebnisse der ursprünglichen Migration

Stand: 21. Oktober 2026.

- `npm run check`: erfolgreich, 0 Fehler, 0 Warnungen, 0 Hinweise.
- `npm run build`: erfolgreich, 30 HTML-Seiten und 484 responsive Bildvarianten.
- `npm run test:parity`: erfolgreich für alle 30 Seiten, 27 Sitemap-URLs, 1.461 lokale Referenzen, 229 Originaldateien und die API-Prüfsumme.
- `npm run test:visual`: 120 erfolgreiche Vergleiche. In 117 Ansichten keine gemessenen Layout- oder Screenshot-Pixelabweichungen zur PHP-Referenz. Die 3 übrigen Ansichten betreffen ausschließlich den beabsichtigten Umbruch langer Rechtstext-Wörter (Impressum 390/320 Pixel, Datenschutz 320 Pixel). Keine überlaufenden Seiten und keine defekten Bilder.
- Interaktive Browserprüfungen: alle 5 Dropdown-Menüs, Mobilnavigation, aktive URL, Fokusführung, Escape, Header beim Scrollen, Wechsel zwischen Mobil- und Desktopansicht, alle 16 Galerien bei 1920 und 390 Pixeln, Hash-Direktlinks, Fehleranzeige und 404 erfolgreich. Zusätzlich alle Mobil-Dropdowns und die Lightbox durch Tippen in Touch-Emulation geprüft.
- Entwicklungsserver zusätzlich geprüft: Mobilnavigation und bedarfsgerecht erzeugte AVIF-Bilder funktionieren auch außerhalb des Produktionsbuilds.
- Alle 484 erzeugten Bildvarianten wurden zusätzlich decodiert und auf ihre erwartete Breite geprüft.
- 8 API-Prüfungen erfolgreich: Methodenprüfung, Pflichtfelder, Honeypot, zu langer Name, ungültige E-Mail, Header-Zeilenumbrüche, zu lange Nachricht und zu große Anfrage. Keine E-Mail versendet.
- Zusätzlicher temporärer Blogbeitrag erfolgreich automatisch gebaut und in der Sitemap erfasst. URL aus Dateiname und Domainwechsel über `SITE_URL` für JSON-LD/Sitemap/robots.txt geprüft. Der Prüfbeitrag wurde anschließend wieder entfernt.
- Prüfsummenprüfung: alle 310 erfassten Dateien im alten Projekt unverändert.

Es sind keine ungeklärten technischen Migrationsfehler bekannt. Die oben genannten inhaltlichen Quelllücken und die Grenzen der lokalen Prüfung bleiben ausdrücklich dokumentiert.

## Beauftragte Änderungen vom 22. Oktober 2026

- Navigation „Holzobjekte“ in „Möbel“ geändert; die bestehende Übersicht bleibt unter `/holzobjekte/` erreichbar und heißt nun ebenfalls „Möbel“.
- Die beiden kleinen Navigationssymbole verwenden `filter: grayscale(1)`. Aktive Seiten und ihre übergeordneten Menüs werden in Löwenkopf-Rot `#d2343a` angezeigt. Der Kontaktbutton ist weiß mit einer Umrandung in der Textfarbe des Bodys.
- Die Startseitenkachel heißt „Möbel-Holzobjekte“, verlinkt auf die Möbel-Übersicht und verwendet wieder das ursprüngliche Motiv mit Tisch und Bücherregalen (`holzmoebel-wohnzimmer-tisch-sitzbank-hendrik-lampe.jpg`). Das Startseiten-Hero verwendet auf korrigierten Wunsch `holzmoebel-wohnaccessoires-baenke-hendrik-lampe.jpg`. Die Two-Stripes-Oak-Kachel verwendet das beauftragte Sitzbankmotiv.
- Als letzter Menüpunkt unter „Möbel“ wurde „Holzobjekte“ ergänzt: `/holzobjekte/holzobjekte/`. Die Seite nutzt dieselben Hero-, Galerie- und Lightbox-Komponenten wie die übrigen Unterseiten. Alle 16 Bilder aus `02_Assets` wurden in das Website-Projekt kopiert und mit Bildbeschreibungen ergänzt; die Übersicht enthält eine entsprechende Kachel.
- Die Telefonnummer wurde auf Kontakt-, Impressums- und Datenschutzseite sowie in sämtlichen strukturierten Daten durch `+49 177 277814` ersetzt. Die Telefonlinks verwenden `tel:+49177277814`.
- Der Hoster-Platzhalter wurde durch die vorgegebene ALL-INKL.COM-Anbieterangabe ersetzt.
- `landoak-loobook-impressionen-1.jpg` ist aus der Landoak-Lookbook-Galerie ausgeschlossen. Die Originaldatei bleibt für die weiterhin vorhandene Verwendung auf der Materialen-Seite erhalten; das Lookbook enthält jetzt 29 Bilder.

Die aktuellen Erwartungen stehen in `tests/site-expectations.json`; die ursprüngliche PHP-Referenz in `tests/legacy-parity.json` bleibt unverändert. `test:visual` prüft nun die aktuelle Gestaltung auf Darstellungsfehler und erzeugt Screenshots, statt die beauftragten Abweichungen zur alten Website als Fehler zu behandeln.

Prüfung des Folgestands: `check` ohne Fehler, Warnungen oder Hinweise; Build mit 31 Seiten und 516 Bildvarianten; Inhaltsvergleich für 31 Seiten, 28 Sitemap-URLs, 1.545 lokale Referenzen, 245 unveränderte Originaldateien und die Kontakt-API erfolgreich. Alle 17 Galerien bei Desktop- und Mobilbreite, Touch-Bedienung, Navigation, Graustufen, Aktivfarben und Kontaktbutton erfolgreich geprüft. Es wurde nichts veröffentlicht.

Die abschließende responsive Prüfung umfasst 124 Ansichten (31 Seiten bei 1440, 768, 390 und 320 Pixeln): keine überlaufenden Inhalte, defekten Bilder oder JavaScript-Fehler. Aktuelle Screenshots und Ergebnisse stehen in `.migration/qa/current/`. Die Browserprüfungen erfolgten mit lokalem Chrome einschließlich Touch-Emulation; keine Prüfung auf physischen Mobilgeräten. Die kollaborative T3-Vorschau lieferte wiederholt Automation-Zeitüberschreitungen; die Abnahme erfolgte deshalb mit dem vorhandenen lokalen Playwright-Verfahren.

## Two-Stripes-Oak-Ergänzungen vom 23. Oktober 2026

- Das neue Logo aus `01_Work/neu_img` steht vor „Two Stripes Oak“ in der Desktop- und Mobilnavigation. Symbolgröße und Abstand entsprechen den vorhandenen Navigationssymbolen; das Logo verwendet `filter: grayscale(1)`. Wie die anderen Navigationslogos wird es über einen Raw-SVG-Import direkt in das HTML eingebunden. Aktuell wird die vom Nutzer um 08:30 Uhr ersetzte schwarze SVG-Datei bytegleich übernommen. Größe, Graustufen und der weiße Hintergrund hinter der ausgesparten Kreuzungsfläche werden über ein dekoratives umschließendes Element gesetzt; die SVG-Datei selbst wird nicht angepasst.
- Die beiden neuen Fotos wurden unverändert in den Website-Bildordner kopiert. Der doppelte Punkt im Dateinamen des Sitzgruppenfotos wurde nur in der Zielkopie bereinigt. Die Quelldateien bleiben unverändert. Die Galerie enthält nun neun Bilder einschließlich deutscher Alt-Texte, responsiver Varianten und Lightbox.
- Die aktuellen Prüferwartungen enthalten gezielt die beiden zusätzlichen Galeriebilder, die beiden neuen Originalfotos, die neue schwarze Original-SVG-Datei sowie die zuvor vom Nutzer ersetzten fünf Favicon-Dateien. Die historische PHP-Referenz bleibt unverändert.
- `check`: keine Fehler, Warnungen oder Hinweise. Build für `https://hendrik.kreativdeck.dev`: 31 Seiten, 229 Bildquellen, 524 AVIF-/WebP-Varianten. Inhaltsvergleich nach der Inline-SVG-Korrektur mit normalisierter Build-Domain: 31 Seiten, 28 Sitemap-URLs, 1.555 lokale Referenzen und 248 erwartete Original-/Asset-Dateien erfolgreich.
- Bestehende Browserprüfung für Navigation, alle 17 Galerien auf Desktop/Mobil und Touch-Emulation erfolgreich. Zusätzlich Logo, aktive Farbe, beide neuen Bilder und Lightbox bei 1920/1440/768/390/320 Pixeln geprüft: keine horizontalen Überläufe, defekten Bilder oder JavaScript-Fehler. Screenshots und Ergebnisse: `.migration/qa/two-stripes-update/`. T3-Snapshots liefen erneut zweimal in einen Timeout; die Prüfung erfolgte über den dokumentierten Chrome-/Playwright-Weg.

Nach der Inline-SVG-Korrektur wurden alle 31 erzeugten HTML-Seiten auf die direkte SVG-Einbindung geprüft. Zusätzliche Browserprüfung bei 1920/1440/390/320 Pixeln: Inline-SVG, weiße Kreuzungsfläche, Graustufen, aktive Farbe und Layout erfolgreich. Eine Pixelprüfung des gerenderten SVG bestätigt die Kreuzungsfläche als deckendes Weiß (RGBA 255/255/255/255). Prüfartefakte: `.migration/qa/two-stripes-inline-correction/`. Der dafür gestartete Prüfserver wurde beendet.

Die weitere Farbkorrektur setzt ausschließlich das Two-Stripes-Oak-Navigationssymbol auf reines Schwarz (`#000`), unabhängig von der Textfarbe des Links. Die Kreuzungsfläche bleibt weiß und der Graustufenfilter erhalten. Im neu gebauten Stand auf Startseite und aktiver Two-Stripes-Oak-Seite bei 1920/390 Pixeln geprüft: Füllung/Kontur RGB 0/0/0, Kreuzungsfläche RGB 255/255/255, kein horizontaler Überlauf. `check` und Build erfolgreich; Screenshots unter `.migration/qa/two-stripes-black/`. Die vom Nutzer gewünschte lokale Vorschau bleibt unter Port 4323 aktiv.

Der neue Build liegt unter `frontend/dist`. Es wurde nichts hochgeladen; der FTP-Upload erfolgt durch den Nutzer.

Aktueller Abschlussstand nach Austausch durch die schwarze Nutzer-SVG: Quelle, `public` und `dist` sind bytegleich (SHA-256 `699d2bffef06745dcb2df04442d50c9ff38d0e399ed625bf3e665fb33039f3fb`). Die zuvor erzeugte eigene SVG-Fassung wurde ersetzt. `check`, Build und Inhaltsvergleich aller 31 Seiten erfolgreich; Originalpfade, Originalfarben, Inline-Einbindung, Maße und weißer Hintergrund zusätzlich bei 1920/390 Pixeln geprüft. Screenshots: `.migration/qa/two-stripes-user-svg/`. Die lokale Vorschau bleibt aktiv.

## Formkultur vom 23. Oktober 2026

- Neue Übersicht `/formkultur/` und Unterseite `/formkultur/lovseth/` mit denselben Komponenten wie Möbel und Landoak. Alle elf Fotos aus `01_Work/neu_img/Formkultur` gehören laut abschließender Nutzerzuordnung zu Løvseth, einschließlich der gelben Liege. Der bisher ins Leere führende Solveig-Menüpunkt wurde entfernt; es wurden keine Solveig-Inhalte erfunden.
- Die Navigation enthält Übersicht und Løvseth, kennzeichnet die aktive Formkultur-Seite und funktioniert auf Desktop und Mobilgeräten. Die Galerie verwendet die vorhandene Lightbox einschließlich Beschriftung, Tastaturbedienung und Direktlinks.
- Die elf JPEG-Kopien unter `public/assets/images/Formkultur/Lovseth` haben beschreibende Dateinamen und deutsche Alt-Texte. Komprimierung bei unveränderter Auflösung von 1280 × 960 Pixeln: zusammen 1.290.695 statt 3.981.522 Bytes, rund 68 % kleiner. Die bestehende Bildverarbeitung erzeugt zusätzlich 44 responsive AVIF-/WebP-Varianten. Alle elf Quelldateien wurden anhand ihrer SHA-256-Prüfsummen als unverändert bestätigt.
- `npm run check`: keine Fehler, Warnungen oder Hinweise. Produktionsbuild mit `SITE_URL=https://hendrik.kreativdeck.dev`: 33 HTML-Seiten, 240 Bildquellen und 568 responsive Bildvarianten. Inhaltsprüfung mit normalisierter Build-Domain erfolgreich für 33 Seiten, 30 Sitemap-URLs, 1.693 lokale Referenzen, 259 erwartete Asset-Dateien und die Kontakt-API; keine bekannten fehlenden internen Seiten mehr.
- Responsive Prüfung aller 33 Seiten bei 1440, 768, 390 und 320 Pixeln: 132 Ansichten ohne defekte Bilder, horizontalen Überlauf oder JavaScript-Fehler. Navigation, alle 18 Galerien und Touch-Bedienung erfolgreich geprüft. Zusätzliche Formkultur-Prüfung bei 1920 und 390 Pixeln: aktive Navigation, Übersichtskachel, alle elf Bilder samt Beschriftung und Lightbox. Desktop- und Mobil-Screenshots zusätzlich gesichtet. Prüfartefakte unter `.migration/qa/current` und `.migration/qa/formkultur`; Chrome mit Mobil-/Touch-Emulation, keine physischen Mobilgeräte.

Der aktualisierte Build liegt in `frontend/dist` und wurde nicht veröffentlicht. Für den manuellen FTP-Upload den gesamten Inhalt dieses Ordners einschließlich `.htaccess` direkt in das Webverzeichnis der Subdomain übertragen. Die lokale Vorschau bleibt unter `http://127.0.0.1:4323/` aktiv.

## Austausch der Løvseth-Fotos vom 23. Oktober 2026

Auf erneuten Nutzerwunsch wurden alle elf bisherigen Løvseth-Bilder im Website-Bildordner entfernt und durch die sieben neu gelieferten Motive aus `01_Work/neu_img/Formkultur` ersetzt. Auch Übersicht und Hero verwenden ein neues Bild. Die sieben Dateien erhalten eigenständige, beschreibende Dateinamen für freigestellte Motive und Wohnraumansichten in Grau und Gelb sowie passende deutsche Alt-Texte. URLs und Seitenaufbau bleiben erhalten.

Die neuen JPEG-Kopien belegen zusammen 547.247 statt 2.347.232 Bytes (rund 77 % weniger) bei unveränderten Abmessungen und Seitenverhältnissen. Die Bildverarbeitung erzeugt dazu 28 AVIF-/WebP-Varianten. Die sieben Quelldateien in `neu_img` sind per SHA-256 als unverändert geprüft; alle elf alten JPEGs und ihre Varianten fehlen im neu erzeugten `dist`.

`npm run check` erfolgreich ohne Fehler, Warnungen oder Hinweise; Produktionsbuild für `https://hendrik.kreativdeck.dev` erfolgreich mit 33 HTML-Seiten, 236 Bildquellen und 552 Bildvarianten. Inhaltsvergleich mit normalisierter Build-Domain erfolgreich für alle 33 Seiten, 1.673 lokale Referenzen, 30 Sitemap-URLs, 255 erwartete Asset-Dateien und die Kontakt-API. Die Erwartungen der übrigen 31 Seiten sind unverändert.

Die kollaborative T3-Browserprüfung war diesmal verfügbar: beide Formkultur-Seiten bei 1440, 768, 390 und 320 Pixeln ohne defekte Bilder oder horizontalen Überlauf geprüft; alle sieben Bilder auf Desktop und Mobilbreite in der Lightbox geöffnet, geladen und einschließlich Reihenfolge und Beschriftung geprüft. Desktop- und Mobilansicht zusätzlich gesichtet. Bildzuordnung, Quellprüfsummen, entfernte Dateinamen und Browserergebnisse stehen unter `.migration/qa/lovseth-replacement/`. Die Sonnet-Delegierung scheiterte mit „Claude API rate limit reached. Try again later.“; die Umsetzung erfolgte gemäß der bestehenden Nutzerfreigabe durch GPT-6.1-Sol.

Der Build in `frontend/dist` ist aktuell. Es wurde nichts hochgeladen. Die Vorschau auf Port 4323 läuft weiter; der FTP-Upload erfolgt durch den Nutzer.

## Korrektur: Solveig-Menüpunkt wiederhergestellt (23. Oktober 2026)

Die frühere Entfernung des Solveig-Menüpunkts (siehe Einträge oben) erfolgte ohne Auftrag und ist damit zurückgenommen; die älteren Einträge bleiben als Historie bestehen. Unter Formkultur steht wieder der Menüpunkt „Solveig“ mit der ursprünglichen URL `/formkultur/solveig/` und `aria-current` auf der aktiven Seite.

- Neue echte Astro-Seite `src/pages/formkultur/solveig.astro` als Platzhalter mit H1 „Solveig“ und sichtbarem Text „Coming Soon“, im vorhandenen `BaseLayout` mit Header, Footer und denselben Abständen wie die übrigen Textseiten. Es wurden weder Fotos noch Galerieinhalte erfunden.
- `src/content/pages.json`: SEO-Eintrag „Solveig | Hendrik Lampe“ mit passender Coming-Soon-Beschreibung und `noindex: true`; der Platzhalter erscheint nicht in der Sitemap und trägt kein JSON-LD. Die Sitemap umfasst weiterhin 30 URLs.
- `tests/site-expectations.json`: Navigationslink `/formkultur/solveig/` bei allen bisherigen Seiten sowie neuer Eintrag für die Solveig-Seite ergänzt. `tests/legacy-parity` blieb unverändert. Formkultur-Übersicht, Løvseth und die sieben neuen Løvseth-Bilder wurden nicht angefasst.
- `npm run check`: 0 Fehler, 0 Warnungen, 0 Hinweise. Produktionsbuild mit `SITE_URL=https://hendrik.kreativdeck.dev`: 34 HTML-Seiten, 552 responsive Bildvarianten. Inhaltsvergleich mit normalisierter Build-Domain erfolgreich für 34 Seiten, 1.743 lokale Referenzen, 30 Sitemap-URLs, 255 Original-Assets und die Kontakt-API.
- Abschließende Prüfung im kollaborativen T3-Browser: Menüfolge Übersicht/Løvseth/Solveig, Navigation zur neuen Seite, aktive Kennzeichnung, rote Formkultur-Markierung und sichtbarer Text „Coming Soon“ bei 1440, 768, 390 und 320 Pixeln erfolgreich. Keine horizontalen Überläufe, defekten Bilder oder Konsolenfehler; Desktop und Mobilansicht zusätzlich gesichtet. Ergebnisse unter `.migration/qa/solveig-coming-soon/`. Der Hauptagent hat den Inhaltsvergleich für alle 34 Seiten zusätzlich erfolgreich ausgeführt und den FTP-Build von Finder-Metadaten bereinigt.
- Es wurde nichts veröffentlicht, committed oder hochgeladen; die Vorschau auf Port 4323 läuft weiter. Die alte PHP-Quelle wurde nicht verändert. `frontend/dist` enthält die wiederhergestellte Solveig-Seite und ist für den manuellen FTP-Upload aktuell.

## Korrektur: Solveig-Kachel in der Formkultur-Übersicht (23. Oktober 2026)

In `/formkultur/` fehlten nach der Wiederherstellung von Menüpunkt und Coming-Soon-Seite noch Bild und Text für Solveig. Die Übersicht zeigt nun beide Kacheln gleichwertig: Løvseth und Solveig, jeweils mit Bild, Überschrift, Text und Link „Mehr erfahren“. Die Solveig-Kachel verlinkt auf `/formkultur/solveig/`.

- Ausschließlich Daten und ein Asset ergänzt, ohne Änderung an Komponenten, Layout oder Menü: `src/content/sections/formkultur.json` enthält die neue Kategorie `solveig` (Label „Solveig“, Tönung `bg-tint-2`, Text „Coming Soon – weitere Informationen folgen in Kürze.“, Ordner `Formkultur/Solveig`) samt Beschreibungseintrag für den Platzhalter.
- Neues, selbst erzeugtes Platzhalterbild `public/assets/images/Formkultur/Solveig/solveig-coming-soon.svg` (1200 × 1200, neutraler Grund, dezentes Bildsymbol, Text „Bild folgt“; SHA-256 `b2b752e4c71b137f06191e5a6ff34d878f57821139ed8895a17b15eb0e7b22dd`). Es ist kein Möbelfoto und keine fremde Produktaufnahme. Für SVG erzeugt `SiteImage` ein einfaches `<img>` ohne `picture` und ohne responsive Rastervarianten; die vorhandenen Klassen `aspect-square size-full object-cover` gelten unverändert.
- `tests/site-expectations.json`: nur die Erwartung der Seite `formkultur` (zusätzlicher Text, Solveig-Link, zusätzliches Bild) sowie die SHA-256-Summe des neuen SVG unter `originalAssets` ergänzt. Die übrigen 33 Seitenerwartungen und `tests/legacy-parity.json` blieben unverändert.
- `npm run check`: 0 Fehler, 0 Warnungen, 0 Hinweise. Produktionsbuild mit `SITE_URL=https://hendrik.kreativdeck.dev`: 34 HTML-Seiten, 8 SVG-Dateien, weiterhin 552 responsive Rastervarianten. Inhaltsvergleich auf einer Kopie des Builds mit normalisierter Domain (`hendrik.kreativdeck.dev` → `www.deinedomain.de`) erfolgreich für 34 Seiten, 1.745 lokale Referenzen, 30 Sitemap-URLs, 256 Original-Assets und die Kontakt-API. Das produktive `dist` blieb dabei unverändert.
- Løvseth-Kachel, die sieben Løvseth-Bilder, Menü und Coming-Soon-Seite sind unverändert; die alte PHP-Quelle und `neu_img` wurden nicht angefasst. Es wurde nichts veröffentlicht oder committed; die Vorschau auf Port 4323 läuft weiter.
- Abschließende Prüfung durch den Hauptagenten im kollaborativen T3-Browser bei 1440, 768, 390 und 320 Pixeln: beide vollständigen Kacheln vorhanden, Dummy-Bild geladen und quadratisch ohne Verzerrung, kein horizontaler Überlauf und keine defekten Bilder. Beide Kachellinks geöffnet und Ziele geprüft (Løvseth mit sieben Galeriebildern, Solveig mit „Coming Soon“); Menüfolge Übersicht/Løvseth/Solveig auf Desktop und Mobil erfolgreich geprüft. Desktop- und Mobilansicht einschließlich der Solveig-Kachel zusätzlich gesichtet, keine Konsolenfehler. Ergebnisse unter `.migration/qa/solveig-overview/`.
- Inhaltsvergleich aller 34 Seiten durch den Hauptagenten erneut erfolgreich; die sieben Løvseth-Bilder sind in `public` und `dist` anhand der Prüfsummen des Bildmanifests unverändert bestätigt. Der aktuelle FTP-Build enthält `.htaccess` und wurde von Finder-Metadaten bereinigt. Es wurde nichts hochgeladen.

## Umbenennung der Bereiche, Hero ohne Text und 301-Weiterleitungen (23. Oktober 2026)

Beauftragte Änderungen an Navigation und URLs; die Bildordner unter `public/assets/images/` (`Holzobjekte`, `Materialen`, `Formkultur`) und alle Bilddateinamen blieben unverändert, ebenso deren URLs.

- Neue Bereichs-URLs und Navigationslabels: „Möbel“ `/holzobjekte/` → „Interior“ `/interior/`, „Formkultur“ `/formkultur/` → „Formcultur“ `/formcultur/`, „Materialen“ `/materialen/` → „Materials“ `/materials/`. Die Unterseiten-Slugs bleiben gleich (`wohnen`, `kochen`, `essen`, `schlafen`, `baden`, `arbeiten`, `holzobjekte`; `lovseth`, `solveig`; `holzarten`, `oberflaechen`, `messingkanten`, `farben`). Die Landoak-URLs (`/landoak/`, `/landoak/furniture/`, `/landoak/accessoires/`, `/landoak/farben/`) waren stimmig und blieben unverändert.
- Umbenannt: `src/pages/{holzobjekte,formkultur,materialen}[.astro]` → `{interior,formcultur,materials}`, `src/content/sections/{holzobjekte,formkultur,materialen}.json` → `{interior,formcultur,materials}.json`; Schlüssel in `src/content/pages.json`, Header-Navigation, Startseitenkarten (Karte „Interior – Möbel & Holzobjekte“, Bild unverändert), SEO-Titel, Breadcrumbs und JSON-LD angepasst. Fließtext mit „Möbel“ und „Materialien“ blieb.
- Alle Hero-Bildbereiche (Startseite, Über mich, Referenzen, Works, Lookbook, Two Stripes Oak, alle Interior-/Landoak-/Materials-Unterseiten, Løvseth) zeigen keinen sichtbaren Text mehr. `Hero.astro` rendert die H1 als `sr-only`; Lead-Text und der dunkle Textverlauf wurden entfernt, Bild und Größe blieben (Ausnahme: bei 320 Pixeln Breite war der Hero zuvor durch den Text bis zu 48 Pixel höher). Die Startseite nutzt nun dieselbe `Hero`-Komponente. Übersichtsüberschriften, Solveig-„Coming Soon“ und alle Texte außerhalb der Heroes blieben.
- Formcultur-Übersicht: Die Løvseth-Kachel verwendet das gelbe Wohnraumbild `formkultur-lovseth-polsterliege-07-gelb-sitzgruppe-wohnraum-hendrik-lampe.jpg` über das neue optionale Feld `overviewCover` (AVIF-/WebP-Varianten aus der vorhandenen Pipeline, u. a. `-960.avif`). Das Hero-Bild der Seite `/formcultur/lovseth/` (Feld `cover`) blieb bewusst unverändert. Alle sieben Løvseth-Bilder, Solveig-Menüpunkt, Coming-Soon-Seite und Dummy-Kachel sind erhalten.
- 301-Weiterleitungen in `public/.htaccess`, vor den Datei-/Verzeichnisprüfungen und der 404-Regel, da die alten Serververzeichnisse noch existieren können. Je Bereich zwei Regeln (Übersicht und eine Unterseitenebene), jeweils mit optionalem `/index.html` und ohne Slash; ein Querystring bleibt durch mod_rewrite erhalten. Dateien (Pfade mit Punkt, z. B. Bilder) und die Bildpfade `/assets/images/Holzobjekte|Formkultur|Materialen/…` sind ausgenommen. Zuordnung maschinenlesbar in `.migration/qa/navigation-urls/redirect-map.json`.
- Prüfskripte angepasst: `scripts/interaction-check.mjs` (Navlabels, neue URLs, Hero ohne sichtbaren Text, Solveig), `scripts/browser-check.mjs` (neue Screenshot-Schlüssel, Hero-Textprüfung). `tests/site-expectations.json` bewusst auf neue Hrefs, Metadaten, Hero-Texte und die `.htaccess`-Prüfsumme aktualisiert; `tests/legacy-parity.json` blieb unverändert.
- Der Apache-Laufzeittest der Weiterleitungen war in der Entwicklungsumgebung nicht möglich (`httpd` kann die Konfiguration dort nicht öffnen). Die Regeln wurden statisch und per Regex-Emulation (`.migration/qa/navigation-urls/check-redirects.py`) geprüft; ein Test auf einem echten Apache steht aus. `npm run test:parity` erwartet die Standarddomain; für den Produktionsbuild normalisiert `.migration/qa/navigation-urls/run-parity-prod.py` die Erwartungsdatei zur Laufzeit auf `SITE_URL`, ohne `dist` zu verändern.

## Nachtrag: Two-Stripes-Galerie und Løvseth-Wohnraumbild (23. Oktober 2026)

- **Two Stripes Oak:** `holzmoebel-two-stripes-oak-sitzbank-tisch-hendrik-lampe.jpg` erscheint nicht mehr in der Galerie. Umgesetzt über das vorhandene Feld `exclude` in `src/content/sections/two-stripes-oak.json`; die Quelldatei bleibt in `public` (und damit in `originalAssets`). Cover und die übrigen acht Bilder samt Lightbox sind unverändert; die Galerie hat jetzt genau 8 statt 9 Bilder. Die Beschreibung des ausgeschlossenen Bildes bleibt in `descriptions` erhalten.
- **Løvseth:** Das graue Wohnraumbild „04“ wurde ersetzt, in Galerie und Hero (`cover`). Neue Quelle `neu_img/Formkultur/4effcb42-34fd-f812-7b88-8469f2681dc0.jpeg` (1280 × 951, 210.276 Byte, SHA-256 `de286863…ce4f`, unverändert geblieben) wurde mit sharp (`rotate`, JPEG-Qualität 86, mozjpeg, native Auflösung, ohne Metadaten) zu `public/assets/images/Formkultur/Lovseth/formkultur-lovseth-polsterliege-04-grau-wohnraum-sessel-hendrik-lampe.jpg` optimiert (121.958 Byte, SHA-256 `27ed9385…ff47`). Die alte Datei `…-04-grau-sitzgruppe-wohnraum-…jpg` wurde aus dem Projekt entfernt; ihre Varianten sind im neuen Build nicht mehr enthalten. Neue Alt-Beschreibung in `formcultur.json`. Das gelbe Bild 07 (`overviewCover`) und die Bilder 01–03 und 05–07 sowie Solveig (Kachel, Text, Link, Coming Soon) blieben unverändert; die Løvseth-Galerie hat weiterhin 7 Bilder.
- `tests/site-expectations.json` gezielt angepasst: Felder `images` und `galleries` der Seiten `two-stripes-oak` und `formcultur/lovseth` sowie der `originalAssets`-Eintrag des neuen Bildes (alter Eintrag ersetzt). Alle übrigen Seiten und `tests/legacy-parity.json` unverändert; Vorher-Stand in `.migration/qa/gallery-image-updates/site-expectations.before.json`.
- Prüfungen: `npm run check` 0/0/0; Produktionsbuild (`SITE_URL=https://hendrik.kreativdeck.dev`) mit 34 Seiten und 552 Varianten; Parität über `run-parity-prod.py` mit 34 Seiten, 1.744 Referenzen, 30 Sitemap-URLs, 256 Original-Assets; `test:browser` und `test:visual` (136 Ansichten) gegen die Vorschau auf Port 4323 ohne Fehler. Gezielte Desktop-/Mobilprüfung (390/1440 px) von Hero, Galerie, Lightbox und Übersicht in `.migration/qa/gallery-image-updates/` (Manifest mit SHA-256/Bytes/Maßen, `browser-results.json`). Nichts hochgeladen oder veröffentlicht; `dist` ist von `.DS_Store`/`._*` bereinigt.
