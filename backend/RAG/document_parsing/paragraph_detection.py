import re
import fitz

SPACE_GAP_FACTOR      = 0.2
DEFAULT_GAP_FACTOR    = 1.6
MIN_GAP_SAMPLES       = 4
FULL_WIDTH_RATIO      = 0.7
GAP_FACTOR_PERCENTILE = 0.95
GAP_FACTOR_BUFFER     = 1.3

FIGURE_CAPTION_RE = re.compile(r"^\s*(figure|fig\.?)\s*[A-Za-z]?\d+", re.IGNORECASE)


def _join_spans(spans):
    parts = []
    prev_x1 = None
    for span in spans:
        text = span["text"]
        if not text:
            continue
        x0 = span["bbox"][0]
        if prev_x1 is not None and x0 - prev_x1 > SPACE_GAP_FACTOR * span["size"]:
            parts.append(" ")
        parts.append(text)
        prev_x1 = span["bbox"][2]
    return "".join(parts)


def _extract_blocks(page):
    blocks = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        block_lines = []
        for line in block["lines"]:
            spans = line["spans"]
            if not spans:
                continue
            text = _join_spans(spans).strip()
            if not text:
                continue
            size = max(s["size"] for s in spans)
            font = spans[0]["font"]
            block_lines.append({"text": text, "bbox": line["bbox"], "size": size, "font": font})
        if block_lines:
            blocks.append(block_lines)
    blocks.sort(key=lambda bl: (bl[0]["bbox"][1], bl[0]["bbox"][0]))
    return blocks


def _compute_gap_factor(blocks):
    ratios = []
    for block_lines in blocks:
        prev = None
        for line in block_lines:
            if prev is not None:
                gap = line["bbox"][1] - prev["bbox"][3]
                if gap >= 0:
                    ratios.append(gap / prev["size"])
            prev = line
    if len(ratios) < MIN_GAP_SAMPLES:
        return DEFAULT_GAP_FACTOR
    ratios.sort()
    idx = int(GAP_FACTOR_PERCENTILE * (len(ratios) - 1))
    return ratios[idx] * GAP_FACTOR_BUFFER


def _spans_overlap(a0, a1, b0, b1):
    return not (a1 < b0 or b1 < a0)


def _merge_paragraph_blocks(blocks, gap_factor):
    merged = []
    for block_lines in blocks:
        if merged:
            prev_last  = merged[-1][-1]
            next_first = block_lines[0]
            gap        = next_first["bbox"][1] - prev_last["bbox"][3]
            same_col   = _spans_overlap(
                prev_last["bbox"][0], prev_last["bbox"][2],
                next_first["bbox"][0], next_first["bbox"][2],
            )
            is_caption_block = bool(FIGURE_CAPTION_RE.match(block_lines[0]["text"]))
            if same_col and 0 <= gap <= gap_factor * prev_last["size"] and not is_caption_block:
                merged[-1].extend(block_lines)
                continue
        merged.append(list(block_lines))
    return merged


def _merge_bbox(lines):
    x0s, y0s, x1s, y1s = zip(*(l["bbox"] for l in lines))
    return fitz.Rect(min(x0s), min(y0s), max(x1s), max(y1s))


def detect(page: fitz.Page, excluded_regions: list[fitz.Rect] = None) -> list[dict]:
    """
    Detect body paragraphs on a page, excluding any region already claimed
    by equation, chart, or table detection.
    Returns list of paragraph dicts with keys: lines, bbox, text.
    """
    excluded_regions = excluded_regions or []

    blocks     = _extract_blocks(page)
    gap_factor = _compute_gap_factor(blocks)
    merged     = _merge_paragraph_blocks(blocks, gap_factor)
    page_width = page.rect.width

    paragraphs = []
    for lines in merged:
        bbox = _merge_bbox(lines)

        if any(bbox.intersects(r) for r in excluded_regions):
            continue

        is_caption = bool(FIGURE_CAPTION_RE.match(lines[0]["text"]))
        if is_caption:
            continue

        is_wide    = bbox.width >= FULL_WIDTH_RATIO * page_width
        char_count = sum(len(l["text"].replace(" ", "")) for l in lines)

        paragraphs.append({
            "lines":      lines,
            "bbox":       bbox,
            "text":       " ".join(l["text"] for l in lines),
            "is_wide":    is_wide,
            "char_count": char_count,
        })

    return paragraphs
