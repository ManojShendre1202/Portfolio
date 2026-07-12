import fitz


def draw_equation_boxes(page: fitz.Page, eq_rects: list[fitz.Rect]) -> None:
    """Draw red bounding boxes around detected equations on the page."""
    for rect in eq_rects:
        page.draw_rect(rect, color=(1, 0, 0), width=1.5)


def draw_paragraph_boxes(page: fitz.Page, paragraphs: list[dict]) -> None:
    """Draw blue bounding boxes around detected paragraphs on the page."""
    for para in paragraphs:
        page.draw_rect(para["bbox"], color=(0, 0, 1), width=1.0)


def write_text_output(all_pages: list[dict], output_txt: str) -> None:
    """Write clean and removed text blocks to a text file."""
    with open(output_txt, "w", encoding="utf-8") as f:
        for result in all_pages:
            f.write(f"PAGE {result['page_num']}\n{'=' * 60}\n\n")
            for block in result["clean_blocks"]:
                f.write(block + "\n\n")
            if result["removed_blocks"]:
                f.write("--- REMOVED (equations) ---\n")
                for block in result["removed_blocks"]:
                    f.write(f"  {block}\n\n")
