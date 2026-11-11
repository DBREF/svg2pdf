#!/usr/bin/env python3
"""
SVG zu PDF Konverter mit Multiprocessing
=========================================

Dieses eigenständige Tool konvertiert SVG-Dateien zu PDF-Dateien.

Features:
- Multiprocessing für parallele Konvertierung
- Erhaltung der Ordnerstruktur
- Progress-Anzeige
- Robuste Fehlerbehandlung
- Windows-optimiert

Autor: Fabian Schöpflin
Version: 1.0.0
"""

# --- Standardbibliotheken ---
import argparse
import gc
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import BrokenExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# --- Drittanbieter-Bibliotheken (PDF) ---
try:
    from reportlab.graphics import renderPDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from svglib.svglib import svg2rlg

    LIBRARIES_AVAILABLE = True

    # Konstanten
    MARGIN_MM = 10
    PAGE_SIZE = A4

except ImportError as e:
    print(f"Fehler: Erforderliche Bibliotheken nicht gefunden: {e}")
    print("Installieren Sie: pip install svglib reportlab")
    LIBRARIES_AVAILABLE = False
    # Fallback-Werte
    MARGIN_MM = 10
    PAGE_SIZE = (595.276, 841.890)  # A4-Größe in Punkten

# ProcessPoolExecutor erlaubt unter Windows höchstens 61 Worker-Prozesse
MAX_WORKERS = 61 if sys.platform == "win32" else 1024


def convert_single_svg_to_pdf(
    svg_path: str, pdf_path: str
) -> tuple[bool, str, str | None]:
    """
    Konvertiert eine einzelne SVG-Datei zu PDF.

    Args:
        svg_path: Pfad zur SVG-Datei
        pdf_path: Zielpfad für PDF-Datei

    Returns:
        Tupel aus (success, svg_filename, error_message)
    """
    svg_filename = os.path.basename(svg_path)

    if not LIBRARIES_AVAILABLE:
        return False, svg_filename, "Erforderliche Bibliotheken nicht verfügbar"

    try:
        # SVG laden
        drawing = svg2rlg(svg_path)  # pyright: ignore[reportPossiblyUnboundVariable] – Import-Guard, Flag oben geprüft
        if drawing is None:
            return False, svg_filename, "SVG konnte nicht geladen werden"
        if drawing.width <= 0 or drawing.height <= 0:
            return False, svg_filename, "SVG hat keine gültige Breite/Höhe"

        # PDF-Layout-Berechnungen
        page_w, page_h = PAGE_SIZE
        margin = MARGIN_MM * mm  # pyright: ignore[reportPossiblyUnboundVariable] – Import-Guard, Flag oben geprüft
        avail_w = page_w - 2 * margin
        avail_h = page_h - 2 * margin
        scale = min(avail_w / drawing.width, avail_h / drawing.height)
        x = margin + (avail_w - drawing.width * scale) / 2
        y = margin + (avail_h - drawing.height * scale) / 2

        # PDF erstellen
        pdf_path_normalized = os.path.normpath(pdf_path)
        os.makedirs(os.path.dirname(pdf_path_normalized), exist_ok=True)

        c = canvas.Canvas(pdf_path_normalized, pagesize=PAGE_SIZE)  # pyright: ignore[reportPossiblyUnboundVariable] – Import-Guard, Flag oben geprüft
        c.saveState()
        c.translate(x, y)
        c.scale(scale, scale)
        renderPDF.draw(drawing, c, 0, 0)  # pyright: ignore[reportPossiblyUnboundVariable] – Import-Guard, Flag oben geprüft
        c.restoreState()
        c.showPage()
        c.save()

        # Aufräumen
        del c
        del drawing
        gc.collect()

    # Worker dürfen nie werfen: jeder Fehler wird als Ergebnis zurückgegeben,
    # damit eine fehlerhafte Datei den Pool nicht abbricht
    except Exception as e:  # noqa: BLE001
        return False, svg_filename, str(e)
    else:
        return True, svg_filename, None


def find_svg_files(
    input_dir: str, min_date: datetime | None = None
) -> list[tuple[str, str]]:
    """
    Findet alle SVG-Dateien in einem Verzeichnis (rekursiv).

    WICHTIG: Macht keine Annahmen über Ordnerstruktur!
    - Dateien können im Hauptordner oder beliebig tief verschachtelt sein
    - Jede gefundene SVG-Datei wird 1:1 mit relativem Pfad übernommen
    - Keine Logik, keine Erwartungen an Ordnernamen oder -struktur

    Args:
        input_dir: Eingabeverzeichnis
        min_date: Minimales Erstellungsdatum (None = alle Dateien)

    Returns:
        Liste von (svg_path, relative_path) Tupeln
    """
    svg_files = []
    input_path = Path(input_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Eingabeverzeichnis existiert nicht: {input_dir}")

    filtered_count = 0
    total_count = 0

    for svg_file in input_path.rglob("*.svg"):
        if svg_file.is_file():
            total_count += 1

            # Datumsfilter anwenden wenn angegeben
            if min_date is not None:
                try:
                    # Erstellungsdatum der Datei abrufen
                    creation_time = svg_file.stat().st_birthtime
                    file_date = datetime.fromtimestamp(creation_time)

                    if file_date < min_date:
                        filtered_count += 1
                        continue  # Datei ist zu alt, überspringen
                except (AttributeError, OSError, OverflowError, ValueError):
                    # Erstellungsdatum nicht ermittelbar (z. B. kein st_birthtime
                    # vor Python 3.12 unter Windows): Datei einschließen
                    pass

            relative_path = svg_file.relative_to(input_path)
            svg_files.append((str(svg_file), str(relative_path)))

    if min_date is not None and filtered_count > 0:
        print(
            f"🗓️ {filtered_count} von {total_count} SVG-Dateien wegen Datumsfilter übersprungen"
        )

    return svg_files


def create_output_path(input_dir: str, relative_path: str, output_dir: str) -> str:
    """
    Erstellt den Ausgabepfad für eine PDF-Datei.

    1:1 Struktur-Übertragung:
    - Nimmt relativen Pfad der SVG-Datei
    - Ändert nur die Dateiendung von .svg zu .pdf
    - Behält komplette Ordnerstruktur bei

    Args:
        input_dir: Eingabeverzeichnis (wird nicht verwendet, nur für API-Konsistenz)
        relative_path: Relativer Pfad der SVG-Datei (z.B. "ordner/datei.svg")
        output_dir: Ausgabeverzeichnis

    Returns:
        Vollständiger Pfad zur PDF-Datei (z.B. "output_dir/ordner/datei.pdf")
    """
    # Einfach: .svg → .pdf, alles andere bleibt gleich
    pdf_relative_path = str(Path(relative_path).with_suffix(".pdf"))
    return os.path.join(output_dir, pdf_relative_path)


def process_svg_file(args: tuple[str, str, str]) -> tuple[bool, str, str | None]:
    """
    Wrapper-Funktion für Multiprocessing.

    Args:
        args: Tupel von (svg_path, relative_path, output_dir)

    Returns:
        Ergebnis der Konvertierung
    """
    svg_path, relative_path, output_dir = args
    pdf_path = create_output_path("", relative_path, output_dir)
    return convert_single_svg_to_pdf(svg_path, pdf_path)


def main() -> None:
    """Hauptfunktion des SVG-zu-PDF-Konverters."""
    parser = argparse.ArgumentParser(
        description="Konvertiert SVG-Dateien zu PDF-Dateien mit Multiprocessing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python svg2pdf.py
  python svg2pdf.py --workers 8 --verbose
  python svg2pdf.py "C:\\Profile\\SVG" "C:\\Profile\\PDF"
  python svg2pdf.py "C:\\Profile\\SVG" "C:\\Profile\\PDF" --min-date "01.01.2024"
  python svg2pdf.py --min-date "15.09.2025" --verbose
        """,
    )

    parser.add_argument(
        "input_dir",
        nargs="?",
        default=r"C:\Profile\SVG",
        help="Eingabeverzeichnis mit SVG-Dateien (rekursiv durchsucht)",
    )

    parser.add_argument(
        "output_dir",
        nargs="?",
        default=r"C:\Profile\PDF",
        help="Ausgabeverzeichnis für PDF-Dateien (Ordnerstruktur wird beibehalten)",
    )

    parser.add_argument(
        "--min-date",
        type=str,
        default=None,
        help="Minimales Erstellungsdatum (DD.MM.YYYY) für SVG-Dateien (Standard: alle)",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=12,
        help=f"Anzahl paralleler Worker-Prozesse (1-{MAX_WORKERS}, Standard: 12)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Detaillierte Ausgabe"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, was konvertiert würde (keine Konvertierung)",
    )

    args = parser.parse_args()

    # Bibliotheken prüfen
    if not LIBRARIES_AVAILABLE:
        sys.exit(1)

    # Eingabe validieren
    if not os.path.exists(args.input_dir):
        print(f"❌ Fehler: Eingabeverzeichnis existiert nicht: {args.input_dir}")
        sys.exit(1)

    if not os.path.isdir(args.input_dir):
        print(f"❌ Fehler: Eingabepfad ist kein Verzeichnis: {args.input_dir}")
        sys.exit(1)

    if not 1 <= args.workers <= MAX_WORKERS:
        print(f"❌ Ungültige Worker-Anzahl: {args.workers} (erlaubt: 1-{MAX_WORKERS})")
        sys.exit(1)

    # Datumsfilter verarbeiten
    min_date = None
    if args.min_date is not None:
        try:
            min_date = datetime.strptime(args.min_date, "%d.%m.%Y")
            print(f"🗓️ Datumsfilter: Nur SVG-Dateien ab {args.min_date}")
        except ValueError:
            print(f"❌ Ungültiges Datumsformat: {args.min_date} (erwartet: DD.MM.YYYY)")
            sys.exit(1)
    else:
        print("🗓️ Datumsfilter: Alle SVG-Dateien")

    # SVG-Dateien finden
    print(f"🔍 Suche SVG-Dateien in: {args.input_dir}")
    try:
        svg_files = find_svg_files(args.input_dir, min_date)
    except OSError as e:
        print(f"❌ Fehler beim Durchsuchen des Verzeichnisses: {e}")
        sys.exit(1)

    if not svg_files:
        print("❌ Keine SVG-Dateien gefunden!")
        sys.exit(1)

    print(f"✅ {len(svg_files)} SVG-Dateien gefunden")

    if args.verbose:
        print("\nGefundene SVG-Dateien:")
        for _, rel_path in svg_files[:10]:  # Erste 10 anzeigen
            print(f"  📄 {rel_path}")
        if len(svg_files) > 10:
            print(f"  ... und {len(svg_files) - 10} weitere")

    # Pfad-Informationen anzeigen
    print(f"📂 Eingabepfad: {args.input_dir}")
    print(f"📁 Ausgabepfad: {args.output_dir}")

    if args.dry_run:
        print(f"\n🔍 Dry-Run Modus: Würde {len(svg_files)} Dateien konvertieren")
        print(f"🔧 Worker-Prozesse: {args.workers}")
        if min_date:
            print(f"🗓️ Datumsfilter aktiv: ab {args.min_date}")

        # Beispiel der Ordnerstruktur-Erhaltung zeigen
        if svg_files and args.verbose:
            print("\n📁 Beispiel Ordnerstruktur-Erhaltung:")
            for _, rel_path in svg_files[:3]:
                pdf_rel_path = str(Path(rel_path).with_suffix(".pdf"))
                print(f"   📄 {rel_path} → {pdf_rel_path}")
            if len(svg_files) > 3:
                print(f"   ... und {len(svg_files) - 3} weitere")
        return

    # Ausgabeverzeichnis erstellen (nicht im Dry-Run)
    os.makedirs(args.output_dir, exist_ok=True)

    # Konvertierung starten
    print(f"\n🚀 Starte Konvertierung mit {args.workers} Worker-Prozessen...")

    # Argumente für Worker vorbereiten
    worker_args = [
        (svg_path, rel_path, args.output_dir) for svg_path, rel_path in svg_files
    ]

    successful = 0
    failed = 0
    start_time = time.time()

    executor = ProcessPoolExecutor(max_workers=args.workers)
    try:
        # Alle Tasks starten
        future_to_svg = {
            executor.submit(process_svg_file, arg): arg[1] for arg in worker_args
        }

        # Ergebnisse sammeln
        for future in as_completed(future_to_svg):
            rel_path = future_to_svg[future]
            try:
                success, _, error = future.result()
            except BrokenExecutor as e:
                # Worker-Prozess abgestürzt (z. B. Speichermangel)
                failed += 1
                print(f"❌ {rel_path}: Worker-Prozess abgebrochen: {e}")
            else:
                if success:
                    successful += 1
                    if args.verbose:
                        print(f"✅ {rel_path}")
                else:
                    failed += 1
                    print(f"❌ {rel_path}: {error}")

            # Fortschritt anzeigen
            total_processed = successful + failed
            if total_processed % 10 == 0 or total_processed == len(svg_files):
                progress = (total_processed / len(svg_files)) * 100
                elapsed = time.time() - start_time
                rate = total_processed / elapsed if elapsed > 0 else 0
                print(
                    f"📊 Fortschritt: {total_processed}/{len(svg_files)} ({progress:.1f}%) - {rate:.1f} Dateien/s"
                )

    except KeyboardInterrupt:
        # Ausstehende Tasks verwerfen, statt auf alle zu warten
        executor.shutdown(wait=False, cancel_futures=True)
        print("\n⚠️ Konvertierung durch Benutzer abgebrochen!")
        print(f"📊 Status: {successful} erfolgreich, {failed} fehlgeschlagen")
        sys.exit(1)
    finally:
        executor.shutdown(wait=True)

    # Ergebnis anzeigen
    end_time = time.time()
    duration = end_time - start_time
    total_files = len(svg_files)

    print("\n🎉 Konvertierung abgeschlossen!")
    print("📊 Ergebnis:")
    print(
        f"   ✅ Erfolgreich: {successful}/{total_files} ({successful / total_files * 100:.1f}%)"
    )
    print(
        f"   ❌ Fehlgeschlagen: {failed}/{total_files} ({failed / total_files * 100:.1f}%)"
    )
    rate = successful / duration if duration > 0 else 0
    print(f"⏱️ Dauer: {duration:.1f} Sekunden ({rate:.1f} PDF/s)")
    print(f"📁 PDF-Dateien gespeichert in: {args.output_dir}")

    if failed > 0:
        print(
            f"\n⚠️ {failed} Dateien konnten nicht konvertiert werden. Verwenden Sie --verbose für Details."
        )
        sys.exit(1)


if __name__ == "__main__":
    # Multiprocessing-Fix für Windows
    mp.freeze_support()
    main()
