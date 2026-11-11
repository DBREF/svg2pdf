# SVG2PDF

Eigenständiges Kommandozeilenwerkzeug zur Stapelkonvertierung von SVG- in PDF-Dateien (svglib → ReportLab) mit Multiprocessing. Ausgelegt für Windows.

| Pfad / Datei       | Inhalt                                                                |
| ------------------ | --------------------------------------------------------------------- |
| `svg2pdf.py`       | Konverter – gesamter Quelltext                                        |
| `svg2pdf_run.bat`  | Interaktiver Aufruf unter Windows (fragt Ordner, Datum und Worker ab) |
| `requirements.txt` | Python-Abhängigkeiten (`reportlab`, `svglib`)                         |
| `biome.json`       | Linter und Formatierer für Markdown/JSON (Biome, Standardregeln)      |

## Funktionen

- **Multiprocessing:** parallele Konvertierung mit konfigurierbarer Worker-Anzahl
- **Ordnerstruktur:** 1:1-Übertragung der Verzeichnisstruktur in den Ausgabeordner
- **Datumsfilter:** nur SVG-Dateien ab einem Erstellungsdatum (`--min-date`)
- **Dry-Run:** Vorschau ohne Konvertierung (`--dry-run`)
- **Fehlerbehandlung:** fehlerhafte SVG-Dateien brechen den Lauf nicht ab, sondern werden gemeldet
- **PDF-Layout:** jede SVG auf eine A4-Hochformatseite, proportional eingepasst und zentriert

## Einrichtung

Voraussetzung: **Python 3.12 oder neuer** (entwickelt mit 3.15). Der Datumsfilter benötigt unter Windows `st_birthtime`, das es erst ab 3.12 gibt.

```powershell
py -3.15 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Geprüft und formatiert wird mit [Ruff](https://docs.astral.sh/ruff/) für Python und [Biome](https://biomejs.dev/) für Markdown/JSON (in VS Code über die jeweiligen Erweiterungen). Von der Kommandozeile, ohne Installation im Repository:

```powershell
.venv\Scripts\python.exe -m pip install ruff
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format .

npx @biomejs/biome check .           # prüfen
npx @biomejs/biome check --write .   # sichere Korrekturen und Formatierung anwenden
```

## Verwendung

### Über das Batch-Skript

```bat
svg2pdf_run.bat
```

Das Skript fragt interaktiv nach Eingabe-/Ausgabeordner, Minimaldatum und Worker-Anzahl. Es verwendet `python` aus dem `PATH`, nicht die `.venv`.

### Über die Kommandozeile

```powershell
# Standardpfade verwenden (C:\Profile\SVG → C:\Profile\PDF)
.venv\Scripts\python.exe svg2pdf.py

# Eigene Pfade angeben
.venv\Scripts\python.exe svg2pdf.py "C:\Profile\SVG" "C:\Profile\PDF"

# Mit Datumsfilter und Worker-Anzahl
.venv\Scripts\python.exe svg2pdf.py "C:\Profile\SVG" "C:\Profile\PDF" --min-date "01.01.2024" --workers 8 --verbose

# Vorschau ohne Konvertierung
.venv\Scripts\python.exe svg2pdf.py "C:\Profile\SVG" "C:\Profile\PDF" --dry-run
```

Hinweis: `svglib` installiert ein gleichnamiges Programm `svg2pdf`. Im aktivierten venv startet `svg2pdf` daher das Werkzeug von svglib – immer `python svg2pdf.py` aufrufen.

### Parameter

| Parameter    | Kurz | Standard         | Beschreibung                                  |
| ------------ | ---- | ---------------- | --------------------------------------------- |
| `input_dir`  | –    | `C:\Profile\SVG` | Eingabeverzeichnis mit SVG-Dateien (rekursiv) |
| `output_dir` | –    | `C:\Profile\PDF` | Ausgabeverzeichnis für PDF-Dateien            |
| `--min-date` | –    | _(alle)_         | Minimales Erstellungsdatum (TT.MM.JJJJ)       |
| `--workers`  | `-w` | `12`             | Anzahl paralleler Worker-Prozesse (1–61)      |
| `--verbose`  | `-v` | –                | Detaillierte Ausgabe                          |
| `--dry-run`  | –    | –                | Nur Vorschau, keine Konvertierung             |

---

## Arbeitsweise

- `dev` ist der Entwicklungszweig, `main` erhält nur Releases.
- Änderungen entstehen in Git-Worktrees und gehen per Pull Request nach `dev`; direkte Commits nur im Ausnahmefall.
- Englische Bezeichner für Dateinamen, Funktionen, Methoden, Klassen und Variablen (Eigennamen ausgenommen).
- Issues und Pull Requests dürfen in Quelltext-Kommentaren genannt werden.

## Lizenz

[MIT](LICENSE) – Copyright © 2026 Fabian Schöpflin
