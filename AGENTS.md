# Projektkontext

Dieses Projekt verwendet Astro, Tailwind CSS und TypeScript.
Einrichtung und Dateistruktur stehen
in der [README.md](README.md).

- Die Astro-Anwendung liegt in `frontend/` und erzeugt zunächst statische Seiten.
- Verwendet werden npm und Node.js 24; Abhängigkeiten und Versionen stehen in `frontend/package.json` und dem zugehörigen Lockfile.
- Payload ist eine optionale Erweiterung im jeweiligen Kundenprojekt unter `backend/`. Die Basis benötigt weder CMS noch Datenbank oder Docker.
- Kundenprojekte sind unabhängig von der Vorlage. Design, Seiten und gegebenenfalls CMS-Inhalte richten sich nach dem jeweiligen Auftrag.

## Lokale Befehle

Im Ordner `frontend/`:

- `npm run dev`: Entwicklungsserver
- `npm run check`: Astro- und TypeScript-Prüfung
- `npm run build`: statische Website erzeugen
- `npm run preview`: erzeugte Website lokal ansehen

## Zusammenarbeit

Auf Deutsch kommunizieren. Vorhandene Änderungen erhalten und Zugangsdaten
vertraulich behandeln. Änderungen ihrem Umfang entsprechend prüfen und im
Ergebnis kurz benennen, was geprüft wurde und was gegebenenfalls offen bleibt.
