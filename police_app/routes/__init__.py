from math import ceil


def pagination(total, page, per_page):
    pages = max(1, ceil((total or 0) / per_page))
    page = min(max(1, page), pages)
    start = (page - 1) * per_page + 1 if total else 0
    end = min(page * per_page, total or 0)
    window = [p for p in range(max(1, page - 2), min(pages, page + 2) + 1)]
    return {"page": page, "pages": pages, "total": total or 0, "start": start, "end": end, "window": window,
            "per_page": per_page}


def page_arg(request):
    try:
        return max(1, int(request.args.get("page", 1)))
    except ValueError:
        return 1
