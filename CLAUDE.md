# CLAUDE.md

SVG2PDF: eigenständiges CLI-Tool zur Stapelkonvertierung von SVG- zu PDF-Dateien (svglib → ReportLab) mit Multiprocessing. Windows-fokussiert, Ausgaben und Docstrings auf Deutsch. Der gesamte Code liegt in `svg2pdf.py` – kein Package, keine Tests, kein Build-Schritt. Überblick und Befehle: README.md.

## Regeln

- Englische Bezeichner für Dateinamen, Funktionen, Methoden, Klassen und Variablen (Eigennamen ausgenommen). Bestehende deutsche Bezeichner nicht nebenbei umbenennen; eine Umstellung erfolgt ggf. separat und geplant.
- Branches: `dev` ist der Entwicklungszweig (Default auf GitHub), `main` erhält nur Releases. Nach `dev` wird nur per PR gemergt; direkte Commits nur im Ausnahmefall.
- Grundsätzlich in Git-Worktrees arbeiten. Ablage unter `.claude/worktrees/<name>` (ignoriert): `git worktree add .claude/worktrees/<name> -b <branch> origin/dev`. `EnterWorktree` scheitert hier an der Schreibweise des Laufwerks (`e:` vs. `E:`).
- Claude wird weder in Kommentaren erwähnt noch als Co-Autor eingetragen.
- Issues und PRs dürfen in Quelltext-Kommentaren genannt werden.
- Projektsprache Deutsch (Kommentare, Docstrings, Doku, Ausgaben) mit korrekten Umlauten.
- Repository ist öffentlich → MIT-Lizenz (`LICENSE`).

## Befehle

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt   # Python 3.15 in .venv

.venv\Scripts\python.exe svg2pdf.py                                      # Defaults C:\Profile\SVG → C:\Profile\PDF
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --workers 8 --verbose   # Default: 12 Worker
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --dry-run
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --min-date "01.01.2024"

# Smoke-Test (keine Testsuite) – prüft Konvertierung + Strukturerhalt
mkdir -Force tmp\in\unter\tief, tmp\out
'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect width="100" height="50" fill="#36c"/></svg>' | Set-Content tmp\in\unter\tief\test.svg
.venv\Scripts\python.exe svg2pdf.py tmp\in tmp\out --workers 2 --verbose
# erwartet: tmp\out\unter\tief\test.pdf
```

## Hinweise

- Linting/Formatierung: Ruff für Python (Defaults, kein `ruff.toml`/`pyproject.toml`; CLI nicht im `.venv` – ggf. `pip install ruff`), Biome (`biome.json`, Standardregeln) für Markdown/JSON; `.vscode/` ist lokal und nicht versioniert. Reine Formatierungsänderungen getrennt von inhaltlichen committen.
- Zeilenenden LF (`.gitattributes`), `*.bat` mit CRLF. Python-Skripte, die Dateien schreiben, mit `newline="\n"`.
- Ablauf: `main()` → `find_svg_files()` (rglob + optionaler Datumsfilter) → `ProcessPoolExecutor` über `process_svg_file()` → `create_output_path()` + `convert_single_svg_to_pdf()`.
- **Import-Guard:** `reportlab`/`svglib` werden in `try/except ImportError` importiert, das zugleich `LIBRARIES_AVAILABLE`, `MARGIN_MM` und `PAGE_SIZE` setzt. Neue Layout-Konstanten gehören in **beide** Zweige. `convert_single_svg_to_pdf()` prüft das Flag erneut, weil bei `spawn` jeder Worker das Modul neu importiert.
- **Multiprocessing (Windows/spawn):** `process_svg_file()` muss auf Modulebene bleiben und ein einzelnes picklebares Tupel entgegennehmen. `mp.freeze_support()` im `__main__`-Block. Worker geben `(success, filename, error)` zurück statt Exceptions zu werfen. Nach jeder Konvertierung `gc.collect()` (ReportLab-Speicher).
- **1:1-Strukturübertragung:** `find_svg_files()` macht bewusst keine Annahmen über Ordnernamen oder -tiefe – keine Sonderbehandlung für bestimmte Ordner einbauen.
- **Seitenlayout:** jede SVG auf genau eine A4-Hochformatseite, mit `MARGIN_MM` Rand eingepasst und zentriert (kleine SVGs werden hochskaliert). `drawing.width/height == 0` → `ZeroDivisionError`, kommt als normaler Dateifehler zurück.
- **Datumsfilter:** Default `"01.01.1900"` ist ein Sentinel per String-Vergleich – explizit `--min-date "01.01.1900"` deaktiviert den Filter. Gefiltert über `st_birthtime`; schlägt der Zugriff fehl, wird die Datei eingeschlossen.
- **Exit-Codes:** `sys.exit(1)` bei fehlenden Bibliotheken, ungültigem Eingabepfad/Datum, null SVGs, Ctrl+C und mindestens einer fehlgeschlagenen Konvertierung. Der Batch-Wrapper wertet das nicht aus.
- **Namenskollision:** `svglib` installiert `.venv/Scripts/svg2pdf.exe`. Immer `python svg2pdf.py` aufrufen.
- `svg2pdf_run.bat` nutzt `python` aus dem `PATH`, nicht das `.venv`.
- `--dry-run` legt das Ausgabeverzeichnis trotzdem an; Exit-Code 0. Kein Skip bestehender PDFs – inkrementell nur über `--min-date`.
- Konventionen: Benutzerausgaben mit Emoji-Präfix (✅ ❌ 📊 🗓️ 🚀), Fortschritt alle 10 Dateien; Google-Style-Docstrings; moderne Type Hints. `create_output_path()` hat einen bewusst ungenutzten `input_dir`-Parameter – nicht „aufräumen“.
