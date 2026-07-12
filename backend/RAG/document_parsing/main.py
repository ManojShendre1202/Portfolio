import fitz
import time
import os
import glob

from chart_detection import build_paragraphs as build_chart_paragraphs, detect as detect_charts
from table_detection import detect as detect_tables
from paragraph_detection import detect as detect_paragraphs

INPUT_FOLDER  = r"C:\Users\souls\Desktop\Manoj\Readar\dev_data\input_data"
OUTPUT_FOLDER = r"C:\Users\souls\Desktop\Manoj\Readar\dev_data\output"

CHART_COLOR = (0.5, 0, 0.5)    # purple
TABLE_COLOR = (1, 0.5, 0)      # orange
PARA_COLOR  = (0, 0, 1)        # blue


def process_pdf(input_path: str, output_path: str) -> None:
    doc = fitz.open(input_path)

    t_chart_total = 0.0
    t_table_total = 0.0
    t_para_total  = 0.0

    for page in doc:
        t0 = time.perf_counter()
        chart_paragraphs = build_chart_paragraphs(page)
        chart_rects      = detect_charts(page, chart_paragraphs)
        t_chart_total   += time.perf_counter() - t0

        t1 = time.perf_counter()
        table_rects = detect_tables(page)
        t_table_total += time.perf_counter() - t1

        t2 = time.perf_counter()
        excluded   = chart_rects + table_rects
        paragraphs = detect_paragraphs(page, excluded_regions=excluded)
        captions   = [p for p in chart_paragraphs if p["is_caption"]]
        paragraphs = paragraphs + captions
        t_para_total += time.perf_counter() - t2

        for rect in chart_rects:
            page.draw_rect(rect, color=CHART_COLOR, width=1.5)
        for rect in table_rects:
            page.draw_rect(rect, color=TABLE_COLOR, width=1.5)
        for para in paragraphs:
            page.draw_rect(para["bbox"], color=PARA_COLOR, width=1.0)

    doc.save(output_path)
    doc.close()

    print(f"  chart={t_chart_total:.2f}s  table={t_table_total:.2f}s  para={t_para_total:.2f}s")


def main() -> None:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = glob.glob(os.path.join(INPUT_FOLDER, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {INPUT_FOLDER}")
        return

    t_total = time.perf_counter()
    print(f"Processing {len(pdf_files)} PDF(s) from {INPUT_FOLDER}\n")

    for pdf_path in pdf_files:
        name        = os.path.basename(pdf_path)
        output_path = os.path.join(OUTPUT_FOLDER, name)
        print(f"[{name}]")
        process_pdf(pdf_path, output_path)

    print(f"\nDone — {len(pdf_files)} file(s) in {time.perf_counter() - t_total:.1f}s")
    print(f"Output → {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
