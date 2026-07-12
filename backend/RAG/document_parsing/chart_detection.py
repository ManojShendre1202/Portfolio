import re
import numpy as np
import fitz

SPACE_GAP_FACTOR      = 0.2
DEFAULT_GAP_FACTOR    = 1.6
MIN_GAP_SAMPLES       = 4
FULL_WIDTH_RATIO      = 0.7
GAP_FACTOR_PERCENTILE = 0.95
GAP_FACTOR_BUFFER     = 1.3

FIGURE_CAPTION_RE = re.compile(r"^\s*(figure|fig\.?)\s*[A-Za-z]?\d+", re.IGNORECASE)

SHORT_TEXT_MAX_CHARS = 100
CLUSTER_PADDING      = 10
COLUMN_GAP_MIN_PTS   = 10


# ---------------------------------------------------------------------------
# Paragraph detection
# ---------------------------------------------------------------------------

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


def build_paragraphs(page, excluded_regions=None):
    blocks     = _extract_blocks(page)
    gap_factor = _compute_gap_factor(blocks)
    merged     = _merge_paragraph_blocks(blocks, gap_factor)
    page_width = page.rect.width

    paragraphs = []
    for lines in merged:
        text       = lines[0]["text"]
        is_caption = bool(FIGURE_CAPTION_RE.match(text))
        bbox       = _merge_bbox(lines)
        is_wide    = bbox.width >= FULL_WIDTH_RATIO * page_width
        char_count = sum(len(l["text"].replace(" ", "")) for l in lines)

        if excluded_regions:
            if any(bbox.intersects(r) for r in excluded_regions):
                continue

        paragraphs.append({
            "lines": lines, "bbox": bbox,
            "is_caption": is_caption, "is_wide": is_wide,
            "char_count": char_count,
        })
    return paragraphs


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _cluster_rects(rects, max_gap, keep_singles=True):
    if not rects:
        return []
    clusters     = [fitz.Rect(r) for r in rects]
    merged_flags = [False] * len(rects)
    changed      = True
    while changed:
        changed   = False
        merged    = []
        new_flags = []
        used      = [False] * len(clusters)
        for i, a in enumerate(clusters):
            if used[i]:
                continue
            expanded  = fitz.Rect(a.x0 - max_gap, a.y0 - max_gap,
                                  a.x1 + max_gap, a.y1 + max_gap)
            group     = fitz.Rect(a)
            did_merge = merged_flags[i]
            for j, b in enumerate(clusters):
                if i == j or used[j]:
                    continue
                if expanded.intersects(b):
                    group    |= b
                    used[j]   = True
                    changed   = True
                    did_merge = True
            merged.append(group)
            new_flags.append(did_merge)
            used[i] = True
        clusters     = merged
        merged_flags = new_flags
    if keep_singles:
        return clusters
    return [r for r, flag in zip(clusters, merged_flags) if flag]


def _bounding_rect(boxes, padding):
    return fitz.Rect(
        min(b.x0 for b in boxes) - padding,
        min(b.y0 for b in boxes) - padding,
        max(b.x1 for b in boxes) + padding,
        max(b.y1 for b in boxes) + padding,
    )


def _count_vector_shapes_in(rect, drawings):
    return sum(1 for d in drawings if fitz.Rect(d["rect"]).intersects(rect))


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def _detect_column_boundaries(body_paragraphs, page_width):
    if not body_paragraphs:
        return [(0, page_width)]

    coverage = np.zeros(int(page_width) + 1, dtype=bool)
    for p in body_paragraphs:
        x0 = max(0, int(p["bbox"].x0))
        x1 = min(int(page_width), int(p["bbox"].x1))
        coverage[x0:x1] = True

    gaps = []
    in_gap, g_start = False, 0
    for x, covered in enumerate(coverage):
        if not covered and not in_gap:
            in_gap, g_start = True, x
        elif covered and in_gap:
            in_gap = False
            if x - g_start >= COLUMN_GAP_MIN_PTS:
                gaps.append((g_start, x))
    if in_gap and int(page_width) - g_start >= COLUMN_GAP_MIN_PTS:
        gaps.append((g_start, int(page_width)))

    if not gaps:
        return [(0, page_width)]

    cols, left = [], 0
    for g0, g1 in gaps:
        if g0 > left:
            cols.append((left, g0))
        left = g1
    if left < page_width:
        cols.append((left, page_width))
    return cols if cols else [(0, page_width)]


def _find_column_for_rect(rect, columns):
    cx = (rect.x0 + rect.x1) / 2
    return min(columns, key=lambda c: abs((c[0] + c[1]) / 2 - cx))


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def _get_zone(bbox, fence_ys):
    cy = (bbox.y0 + bbox.y1) / 2
    for i, fy in enumerate(fence_ys):
        if cy < fy:
            return i
    return len(fence_ys)


def _cluster_orange_boxes(orange_bboxes, zone_ids):
    if not orange_bboxes:
        return []
    clusters = []
    for zone in sorted(set(zone_ids)):
        zone_boxes = [orange_bboxes[i] for i, z in enumerate(zone_ids) if z == zone]
        if not zone_boxes:
            continue
        centers    = [((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2) for b in zone_boxes]
        assigned   = [-1] * len(zone_boxes)
        cluster_id = 0
        for i in range(len(zone_boxes)):
            if assigned[i] != -1:
                continue
            queue = [i]
            assigned[i] = cluster_id
            while queue:
                cur = queue.pop()
                cx, cy = centers[cur]
                for j in range(len(zone_boxes)):
                    if assigned[j] != -1:
                        continue
                    jx, jy = centers[j]
                    if ((cx - jx) ** 2 + (cy - jy) ** 2) ** 0.5 <= 60:
                        assigned[j] = cluster_id
                        queue.append(j)
            cluster_id += 1
        label_to_boxes = {}
        for lbl, box in zip(assigned, zone_boxes):
            label_to_boxes.setdefault(lbl, []).append(box)
        clusters.extend(label_to_boxes.values())
    return clusters


def _sidebyside_groups(caption_bboxes):
    if not caption_bboxes:
        return []
    sorted_caps = sorted(caption_bboxes, key=lambda b: b.y0)
    groups, current = [], [sorted_caps[0]]
    for cap in sorted_caps[1:]:
        if any(not (cap.y1 < c.y0 or cap.y0 > c.y1) for c in current):
            current.append(cap)
        else:
            groups.append(sorted(current, key=lambda b: b.x0))
            current = [cap]
    groups.append(sorted(current, key=lambda b: b.x0))
    return groups


def _assign_images_to_captions(all_images, caption_bboxes):
    cap_unions = {}
    for img in all_images:
        best_idx, best_dist = None, float("inf")
        for i, cap in enumerate(caption_bboxes):
            dist = max(0, img.y0 - cap.y1, cap.y0 - img.y1)
            if dist < best_dist:
                best_dist = dist
                best_idx  = i
        if best_idx is not None:
            cap_unions[best_idx] = cap_unions.get(best_idx, fitz.Rect()) | img
    return cap_unions


def _split_rect_by_captions(merged_rect, sidebyside_caps):
    relevant = sorted(
        [c for c in sidebyside_caps if not (c.x1 < merged_rect.x0 or c.x0 > merged_rect.x1)],
        key=lambda b: b.x0,
    )
    if len(relevant) <= 1:
        return [merged_rect]
    slices, left = [], merged_rect.x0
    for cap in relevant[1:]:
        slices.append(fitz.Rect(left, merged_rect.y0, cap.x0, merged_rect.y1))
        left = cap.x0
    slices.append(fitz.Rect(left, merged_rect.y0, merged_rect.x1, merged_rect.y1))
    return slices


# ---------------------------------------------------------------------------
# Chart detection (public)
# ---------------------------------------------------------------------------

def detect(page: fitz.Page, paragraphs: list[dict], eq_rects: list[fitz.Rect] = None, debug: bool = False) -> list[fitz.Rect]:
    """
    One caption → one box.  The box is built from content strictly within that
    caption's vertical zone (between the previous caption/page-top and this
    caption's top edge).  Nothing crosses caption boundaries.
    """
    eq_rects = eq_rects or []

    caption_paras = []
    body_paras    = []

    for para in paragraphs:
        if para["is_caption"]:
            caption_paras.append(para)
        elif para["char_count"] >= SHORT_TEXT_MAX_CHARS:
            body_paras.append(para)

    if not caption_paras:
        if debug:
            print(f"  [chart] no captions found — skipping page")
        return []

    # Sort captions top-to-bottom
    caption_paras.sort(key=lambda p: p["bbox"].y0)

    drawings      = [d for d in page.get_drawings() if d.get("rect")]
    raster_images = [fitz.Rect(info["bbox"]) for info in page.get_image_info()]
    columns       = _detect_column_boundaries(body_paras, page.rect.width)
    page_h        = page.rect.height

    if debug:
        print(f"  [chart] {len(caption_paras)} caption(s), {len(raster_images)} raster image(s), {len(drawings)} vector drawings")

    final_rects = []

    for idx, cap_para in enumerate(caption_paras):
        cap_bbox = cap_para["bbox"]
        cap_text = cap_para["lines"][0]["text"][:70] if cap_para["lines"] else ""

        # Vertical zone for this caption: from previous caption bottom (or page top)
        # up to this caption's top edge.
        zone_top    = caption_paras[idx - 1]["bbox"].y1 if idx > 0 else 0
        zone_bottom = cap_bbox.y0  # strictly above the caption line

        if debug:
            print(f"  [chart] caption {idx}: {cap_text!r}")
            print(f"    zone y={zone_top:.0f}–{zone_bottom:.0f}")

        # Column for this caption (figure content should be in same column)
        col_x0, col_x1 = _find_column_for_rect(cap_bbox, columns)
        # Widen column bounds if caption itself is wider than one column
        for c_x0, c_x1 in columns:
            if cap_bbox.x0 < c_x1 and cap_bbox.x1 > c_x0:
                col_x0 = min(col_x0, c_x0)
                col_x1 = max(col_x1, c_x1)

        zone = fitz.Rect(col_x0, zone_top, col_x1, zone_bottom)

        # --- try raster image first ---
        images_in_zone = [r for r in raster_images if zone.intersects(r)]
        if images_in_zone:
            fig_rect = _bounding_rect(images_in_zone, CLUSTER_PADDING)
            fig_rect = fitz.Rect(max(fig_rect.x0, col_x0), max(fig_rect.y0, zone_top),
                                 min(fig_rect.x1, col_x1), min(fig_rect.y1, zone_bottom))
            if debug:
                print(f"    → raster image hit: {fig_rect}")
            final_rects.append(fig_rect)
            continue

        # --- try vector drawings in zone ---
        drawings_in_zone = [fitz.Rect(d["rect"]) for d in drawings
                            if zone.intersects(fitz.Rect(d["rect"]))]

        if len(drawings_in_zone) < 3:
            if debug:
                print(f"    → only {len(drawings_in_zone)} vector shapes in zone, skipped")
            continue

        # Cluster drawings; pick the group closest to the caption bottom edge
        clusters = _cluster_rects(drawings_in_zone, max_gap=15, keep_singles=False)
        if not clusters:
            clusters = _cluster_rects(drawings_in_zone, max_gap=15, keep_singles=True)

        best = min(clusters, key=lambda r: abs(r.y1 - zone_bottom))
        count = _count_vector_shapes_in(best, drawings)

        if count < 3:
            if debug:
                print(f"    → best cluster {best} only {count} shapes, skipped")
            continue

        fig_rect = fitz.Rect(max(best.x0 - CLUSTER_PADDING, col_x0),
                             max(best.y0 - CLUSTER_PADDING, zone_top),
                             min(best.x1 + CLUSTER_PADDING, col_x1),
                             min(best.y1 + CLUSTER_PADDING, zone_bottom))
        if debug:
            print(f"    → vector cluster accepted: {fig_rect} ({count} shapes)")
        final_rects.append(fig_rect)

    if debug:
        print(f"  [chart] final detections: {len(final_rects)}")

    return final_rects


# ---------------------------------------------------------------------------
# Complex equation detection (public)
# ---------------------------------------------------------------------------

_MATH_FONT_RE = re.compile(
    r"^(CMMI|CMSY|CMEX|MSAM|MSBM|EUFM|EURM|EUSM"
    r"|STIXMath|STIXGeneral|Asana"
    r"|CambriaMath|LMMath|NeoEuler"
    r"|MathJax|LatinModernMath)",
    re.IGNORECASE,
)
_LARGE_OP_RE = re.compile(r"^CMEX", re.IGNORECASE)

_SUBSUP_RATIO              = 0.68
_SUBSUP_Y_OFFSET           = 1.5
_LARGE_OP_THRESHOLD        = 2
_STRUCTURED_LINE_THRESHOLD = 4
_DENSE_INLINE_THRESHOLD    = 8


def _line_has_subsup(spans: list) -> bool:
    if len(spans) < 3:
        return False
    sizes = [s["size"] for s in spans if s["text"].strip()]
    if not sizes:
        return False
    max_size = max(sizes)
    if max_size == 0:
        return False
    y_mids = sorted((s["bbox"][1] + s["bbox"][3]) / 2 for s in spans if s["text"].strip())
    baseline_y = y_mids[len(y_mids) // 2]
    subsup_count = 0
    for span in spans:
        if not span["text"].strip():
            continue
        if span["size"] / max_size > _SUBSUP_RATIO:
            continue
        y_mid = (span["bbox"][1] + span["bbox"][3]) / 2
        if abs(y_mid - baseline_y) >= _SUBSUP_Y_OFFSET:
            subsup_count += 1
    return subsup_count >= 2


def _line_has_inline_math(spans: list) -> bool:
    has_math = has_plain = False
    for span in spans:
        if not span["text"].strip():
            continue
        if _MATH_FONT_RE.match(span["font"]):
            has_math = True
        else:
            has_plain = True
        if has_math and has_plain:
            return True
    return False


def _score_page(page: fitz.Page) -> tuple[int, list[str]]:
    text_dict = page.get_text("dict")
    large_op_count = structured_lines = dense_inline_lines = 0

    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            for span in spans:
                if _LARGE_OP_RE.match(span.get("font", "")):
                    large_op_count += 1
            if _line_has_subsup(spans):
                structured_lines += 1
            if _line_has_inline_math(spans):
                dense_inline_lines += 1

    reasons = []
    if large_op_count >= _LARGE_OP_THRESHOLD:
        reasons.append("large_operators")
    if structured_lines >= _STRUCTURED_LINE_THRESHOLD:
        reasons.append("super_subscripts")
    if dense_inline_lines >= _DENSE_INLINE_THRESHOLD:
        reasons.append("dense_inline_math")
    return len(reasons), reasons


def has_complex_equations(doc: fitz.Document) -> dict:
    flagged_pages: list[int] = []
    all_reasons:  set[str]   = set()

    for page_num in range(len(doc)):
        score, reasons = _score_page(doc[page_num])
        if score >= 1:
            flagged_pages.append(page_num)
            all_reasons.update(reasons)

    return {
        "has_complex_equations": bool(flagged_pages),
        "flagged_pages": flagged_pages,
        "reason_summary": ", ".join(sorted(all_reasons)) if all_reasons else "none",
    }
