# CLAUDE.md

SVG2PDF: eigenständiges CLI-Tool zur Stapelkonvertierung von SVG- zu PDF-Dateien (svglib → ReportLab) mit Multiprocessing. Windows-fokussiert, Ausgaben und Docstrings auf Deutsch. Der gesamte Code liegt in `svg2pdf.py` – kein Package, keine Tests, kein Build-Schritt. Überblick und Befehle: README.md.

## Regeln

- Englische Bezeichner für Dateinamen, Funktionen, Methoden, Klassen und Variablen (Eigennamen ausgenommen). Bestehende deutsche Bezeichner nicht nebenbei umbenennen; eine Umstellung erfolgt ggf. separat und geplant.
- Branches: `dev` ist der Entwicklungszweig (Default auf GitHub), `main` erhält nur Releases. Nach `dev` wird nur per PR gemergt; direkte Commits nur im Ausnahmefall.
- Grundsätzlich in Git-Worktrees arbeiten. Ablage unter `.claude/worktrees/<name>` (ignoriert): `git worktree add .claude/worktrees/<name> -b <branch> origin/dev`, danach `.gitignore` hineinkopieren (nur lokal, nicht versioniert). `EnterWorktree` scheitert hier an der Schreibweise des Laufwerks (`e:` vs. `E:`). PR: `gh pr create --base dev`. Nach dem Merge: `git worktree remove …` (scheitert mit „Permission denied“, solange VS Code den Ordner offen hat – dann Ordner später löschen), Branch lokal und remote löschen.
- Claude wird weder in Kommentaren erwähnt noch als Co-Autor eingetragen.
- Issues und PRs dürfen in Quelltext-Kommentaren genannt werden.
- Projektsprache Deutsch (Kommentare, Docstrings, Doku, Ausgaben) mit korrekten Umlauten.
- Repository ist öffentlich → MIT-Lizenz (`LICENSE`).

## Befehle

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # Python 3.15 in .venv; enthält requirements.txt

.venv\Scripts\python.exe svg2pdf.py                                      # Defaults C:\Profile\SVG → C:\Profile\PDF
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --workers 8 --verbose   # Default: 12 Worker
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --dry-run
.venv\Scripts\python.exe svg2pdf.py "<in>" "<out>" --min-date "01.01.2024"

.venv\Scripts\ruff.exe check .; .venv\Scripts\ruff.exe format .
.venv\Scripts\python.exe -m pyright   # Konfiguration in pyrightconfig.json
npx @biomejs/biome@2.6.6 check .   # Version wie $schema in biome.json

# Smoke-Test (keine Testsuite) – prüft Konvertierung + Strukturerhalt, außerhalb des Repos
$t = "$env:TEMP\svg2pdf-test"; mkdir -Force "$t\in\unter\tief", "$t\out"
'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect width="100" height="50" fill="#36c"/></svg>' | Set-Content "$t\in\unter\tief\test.svg"
.venv\Scripts\python.exe svg2pdf.py "$t\in" "$t\out" --workers 2 --verbose
# erwartet: $t\out\unter\tief\test.pdf
```

## Hinweise

- Linting/Formatierung: Ruff für Python (Defaults, kein `ruff.toml`/`pyproject.toml`; Version fest in `requirements-dev.txt`; die Defaults von Ruff 0.17 enthalten u. a. BLE001/S110), Biome (`biome.json`, Standardregeln) für Markdown/JSON; `.vscode/` ist lokal und nicht versioniert. Reine Formatierungsänderungen getrennt von inhaltlichen committen.
- **Typprüfung:** Pyright (Version fest in `requirements-dev.txt`, gemeinsam mit den übrigen InfraGeo-Repositorys anheben), Stufe `standard` in `pyrightconfig.json`, `pythonVersion` 3.15. Ausnahmen nur als `# pyright: ignore[<regel>]` mit Begründung im selben Kommentar, kein pauschales `# type: ignore`. Die Namen aus dem Import-Guard gelten für Pyright als möglicherweise ungebunden; ihre Verwendungen in `convert_single_svg_to_pdf()` tragen deshalb `reportPossiblyUnboundVariable`-Ausnahmen.
- **CI:** `.github/workflows/checks.yml` prüft jede PR nach `dev`/`main` auf Windows mit Ruff (check, format), Biome (`ci --error-on-warnings`, Version aus `biome.json`) und Pyright, immer den ganzen Bestand. Werkzeugversionen nur in `requirements-dev.txt` ändern.
- `.gitignore` ist bewusst nicht versioniert (ignoriert sich selbst).
- Zeilenenden LF (`.gitattributes`), `*.bat` mit CRLF. Python-Skripte, die Dateien schreiben, mit `newline="\n"`.
- Ablauf: `main()` → `find_svg_files()` (rglob + optionaler Datumsfilter) → `ProcessPoolExecutor` über `process_svg_file()` → `create_output_path()` + `convert_single_svg_to_pdf()`.
- **Import-Guard:** `reportlab`/`svglib` werden in `try/except ImportError` importiert, das zugleich `LIBRARIES_AVAILABLE`, `MARGIN_MM` und `PAGE_SIZE` setzt. Neue Layout-Konstanten gehören in **beide** Zweige. `convert_single_svg_to_pdf()` prüft das Flag erneut, weil bei `spawn` jeder Worker das Modul neu importiert.
- **Multiprocessing (Windows/spawn):** `process_svg_file()` muss auf Modulebene bleiben und ein einzelnes picklebares Tupel entgegennehmen. `mp.freeze_support()` im `__main__`-Block. Worker geben `(success, filename, error)` zurück statt Exceptions zu werfen (bewusstes `except Exception` mit `noqa: BLE001`); im Hauptprozess wird nur `BrokenExecutor` abgefangen. Nach jeder Konvertierung `gc.collect()` (ReportLab-Speicher).
- **1:1-Strukturübertragung:** `find_svg_files()` macht bewusst keine Annahmen über Ordnernamen oder -tiefe – keine Sonderbehandlung für bestimmte Ordner einbauen.
- **Seitenlayout:** jede SVG auf genau eine A4-Hochformatseite, mit `MARGIN_MM` Rand eingepasst und zentriert (kleine SVGs werden hochskaliert). SVGs ohne Breite/Höhe werden vorab als Dateifehler gemeldet.
- **Datumsfilter:** ohne `--min-date` (Default `None`) kein Filter. Gefiltert über `st_birthtime`; schlägt der Zugriff fehl, wird die Datei eingeschlossen.
- **Exit-Codes:** `sys.exit(1)` bei fehlenden Bibliotheken, ungültigem Eingabepfad/Datum, null SVGs, Ctrl+C (ausstehende Tasks werden verworfen), ungültiger Worker-Anzahl und mindestens einer fehlgeschlagenen Konvertierung. Der Batch-Wrapper wertet das nicht aus.
- **Namenskollision:** `svglib` installiert `.venv/Scripts/svg2pdf.exe`. Immer `python svg2pdf.py` aufrufen.
- `svg2pdf_run.bat` nutzt `python` aus dem `PATH`, nicht das `.venv`.
- `--dry-run` legt kein Ausgabeverzeichnis an; Exit-Code 0. `--workers` wird auf 1–61 geprüft (Windows-Grenze von `ProcessPoolExecutor`). Kein Skip bestehender PDFs – inkrementell nur über `--min-date`.
- Konventionen: Benutzerausgaben mit Emoji-Präfix (✅ ❌ 📊 🗓️ 🚀), Fortschritt alle 10 Dateien; Google-Style-Docstrings; moderne Type Hints. `create_output_path()` hat einen bewusst ungenutzten `input_dir`-Parameter – nicht „aufräumen“.
