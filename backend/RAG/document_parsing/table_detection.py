import fitz

TOL = 2
MIN_WORDS_IN_TABLE = 10
MIN_CROSSINGS = 4
MIN_EDGE_SPAN_RATIO = 0.5


def get_line_segments(page):
    horizontal, vertical = [], []

    for drawing in page.get_drawings():
        for item in drawing["items"]:
            kind = item[0]

            if kind == "l":
                p1, p2 = item[1], item[2]
                segments = [(p1, p2)]
            elif kind == "re":
                r = item[1]
                segments = [
                    (fitz.Point(r.x0, r.y0), fitz.Point(r.x1, r.y0)),
                    (fitz.Point(r.x0, r.y1), fitz.Point(r.x1, r.y1)),
                    (fitz.Point(r.x0, r.y0), fitz.Point(r.x0, r.y1)),
                    (fitz.Point(r.x1, r.y0), fitz.Point(r.x1, r.y1)),
                ]
            else:
                continue

            for p1, p2 in segments:
                if abs(p1.y - p2.y) <= TOL:
                    x0, x1 = sorted([p1.x, p2.x])
                    horizontal.append((x0, p1.y, x1, p1.y))
                elif abs(p1.x - p2.x) <= TOL:
                    y0, y1 = sorted([p1.y, p2.y])
                    vertical.append((p1.x, y0, p1.x, y1))

    return horizontal, vertical


def merge_collinear(segments, fixed_index, start_index, end_index):
    groups = []
    used = [False] * len(segments)

    for i, seg in enumerate(segments):
        if used[i]:
            continue
        group = [seg]
        used[i] = True
        fixed_val = seg[fixed_index]
        for j in range(i + 1, len(segments)):
            if used[j]:
                continue
            if abs(segments[j][fixed_index] - fixed_val) <= TOL:
                group.append(segments[j])
                used[j] = True
        groups.append(group)

    merged = []
    for group in groups:
        group.sort(key=lambda s: s[start_index])
        cur_start, cur_end = group[0][start_index], group[0][end_index]
        fixed_val = group[0][fixed_index]
        for seg in group[1:]:
            s, e = seg[start_index], seg[end_index]
            if s <= cur_end + TOL:
                cur_end = max(cur_end, e)
            else:
                merged.append((cur_start, cur_end, fixed_val))
                cur_start, cur_end = s, e
        merged.append((cur_start, cur_end, fixed_val))

    return merged


def get_merged_lines(page):
    horizontal, vertical = get_line_segments(page)
    merged_h = merge_collinear(horizontal, fixed_index=1, start_index=0, end_index=2)
    merged_horizontal = [(x0, y, x1, y) for x0, x1, y in merged_h]
    merged_v = merge_collinear(vertical, fixed_index=0, start_index=1, end_index=3)
    merged_vertical = [(x, y0, x, y1) for y0, y1, x in merged_v]
    return merged_horizontal, merged_vertical


def find_rectangles(horizontal, vertical):
    rectangles = []
    for i, (hx0, hy, hx1, _) in enumerate(horizontal):
        for hx0b, hy_b, hx1b, _ in horizontal[i + 1:]:
            top, bottom = sorted([hy, hy_b])
            if top == bottom:
                continue
            if abs(hx0 - hx0b) > TOL or abs(hx1 - hx1b) > TOL:
                continue
            left_x, right_x = hx0, hx1
            has_left = any(
                abs(vx - left_x) <= TOL and vy0 - TOL <= top and vy1 + TOL >= bottom
                for vx, vy0, _, vy1 in vertical
            )
            has_right = any(
                abs(vx - right_x) <= TOL and vy0 - TOL <= top and vy1 + TOL >= bottom
                for vx, vy0, _, vy1 in vertical
            )
            if has_left and has_right:
                rectangles.append(fitz.Rect(left_x, top, right_x, bottom))
    return rectangles


def merge_overlapping_rectangles(rectangles):
    rects = list(rectangles)
    changed = True
    while changed:
        changed = False
        merged = []
        while rects:
            r = rects.pop()
            i = 0
            while i < len(merged):
                if r.intersects(merged[i]):
                    r = r | merged[i]
                    merged.pop(i)
                    changed = True
                else:
                    i += 1
            merged.append(r)
        rects = merged
    return rects


def count_crossings(rect, horizontal, vertical):
    corners = {
        (round(rect.x0), round(rect.y0)),
        (round(rect.x0), round(rect.y1)),
        (round(rect.x1), round(rect.y0)),
        (round(rect.x1), round(rect.y1)),
    }
    points = set()
    for hx0, hy, hx1, _ in horizontal:
        if hy < rect.y0 - TOL or hy > rect.y1 + TOL:
            continue
        for vx, vy0, _, vy1 in vertical:
            if vx < rect.x0 - TOL or vx > rect.x1 + TOL:
                continue
            if (hx0 - TOL <= vx <= hx1 + TOL) and (vy0 - TOL <= hy <= vy1 + TOL):
                point = (round(vx), round(hy))
                if point in corners:
                    continue
                points.add(point)
    return len(points)


def edge_spanning_ratio(rect, horizontal, vertical):
    h_in_rect = [
        (hx0, hy, hx1) for hx0, hy, hx1, _ in horizontal
        if rect.y0 - TOL <= hy <= rect.y1 + TOL
        and hx1 >= rect.x0 - TOL and hx0 <= rect.x1 + TOL
    ]
    v_in_rect = [
        (vx, vy0, vy1) for vx, vy0, _, vy1 in vertical
        if rect.x0 - TOL <= vx <= rect.x1 + TOL
        and vy1 >= rect.y0 - TOL and vy0 <= rect.y1 + TOL
    ]
    h_full = sum(
        1 for hx0, _, hx1 in h_in_rect
        if abs(hx0 - rect.x0) <= TOL and abs(hx1 - rect.x1) <= TOL
    )
    v_full = sum(
        1 for _, vy0, vy1 in v_in_rect
        if abs(vy0 - rect.y0) <= TOL and abs(vy1 - rect.y1) <= TOL
    )
    h_ratio = h_full / len(h_in_rect) if h_in_rect else 0
    v_ratio = v_full / len(v_in_rect) if v_in_rect else 0
    return h_ratio, v_ratio


def count_words_in_rect(page, rect):
    words = page.get_text("words")
    count = 0
    for x0, y0, x1, y1, *_ in words:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if rect.contains(fitz.Point(cx, cy)):
            count += 1
    return count


def detect(page):
    """Return list of fitz.Rect for tables found on this page."""
    horizontal, vertical = get_merged_lines(page)
    rectangles = find_rectangles(horizontal, vertical)
    rectangles = merge_overlapping_rectangles(rectangles)
    tables = []
    for r in rectangles:
        if count_words_in_rect(page, r) < MIN_WORDS_IN_TABLE:
            continue
        if count_crossings(r, horizontal, vertical) < MIN_CROSSINGS:
            continue
        h_ratio, v_ratio = edge_spanning_ratio(r, horizontal, vertical)
        if h_ratio < MIN_EDGE_SPAN_RATIO and v_ratio < MIN_EDGE_SPAN_RATIO:
            continue
        tables.append(r)
    return tables
