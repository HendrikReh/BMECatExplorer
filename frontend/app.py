"""Web frontend application for BMECatDemo product catalog search."""

import csv
import io
import json
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from frontend.api_client import APIClient
from frontend.config import settings

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="BMECatDemo Admin",
    description="Web interface for product catalog exploration",
    docs_url=None,
    redoc_url=None,
)

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Register custom filters
templates.env.filters["format_price"] = lambda x: f"{x:,.2f}" if x else "-"
templates.env.filters["format_number"] = lambda x: f"{x:,}" if x else "0"

# API client instance
api = APIClient(base_url=settings.api_base_url)


def calculate_page_range(
    current_page: int, total_pages: int, max_pages: int = 7
) -> list[int]:
    """Calculate which page numbers to display in pagination."""
    if total_pages <= max_pages:
        return list(range(1, total_pages + 1))

    half = max_pages // 2
    if current_page <= half:
        return list(range(1, max_pages + 1))
    elif current_page >= total_pages - half:
        return list(range(total_pages - max_pages + 1, total_pages + 1))
    else:
        return list(range(current_page - half, current_page + half + 1))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main search page."""
    try:
        facets = await api.get_facets()
        results = await api.search(page=1, size=settings.default_page_size)
        page_size = settings.default_page_size
        total_pages = (results["total"] + page_size - 1) // page_size
        page_range = calculate_page_range(1, total_pages)
    except httpx.ConnectError:
        error_msg = "Cannot connect to API. Is the backend running?"
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": error_msg},
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "facets": facets,
            "results": results["results"],
            "total": results["total"],
            "page": 1,
            "size": settings.default_page_size,
            "total_pages": total_pages,
            "page_range": page_range,
            "query": None,
            "manufacturer": None,
            "eclass_id": None,
            "price_min": None,
            "price_max": None,
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str | None = Query(None),
    manufacturer: list[str] | None = Query(None),
    eclass_id: list[str] | None = Query(None),
    eclass_segment: list[str] | None = Query(None),
    order_unit: list[str] | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    price_band: str | None = Query(None),
    exact_match: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(default=None),
):
    """Search endpoint for HTMX partial updates."""
    if size is None:
        size = settings.default_page_size

    # Convert empty strings to None (HTMX sends empty strings for empty inputs)
    q = q if q else None
    price_band = price_band if price_band else None

    # Filter out empty strings from list parameters
    eclass_segments = [s for s in (eclass_segment or []) if s] or None
    manufacturers = [m for m in (manufacturer or []) if m] or None
    eclass_ids = [e for e in (eclass_id or []) if e] or None
    order_units = [u for u in (order_unit or []) if u] or None

    try:
        results = await api.search(
            q=q,
            manufacturers=manufacturers,
            eclass_ids=eclass_ids,
            eclass_segments=eclass_segments,
            order_units=order_units,
            price_min=price_min,
            price_max=price_max,
            price_band=price_band,
            exact_match=exact_match,
            page=page,
            size=size,
        )
    except httpx.ConnectError:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "API connection failed"},
        )

    total_pages = (results["total"] + size - 1) // size if results["total"] > 0 else 1
    page_range = calculate_page_range(page, total_pages)

    return templates.TemplateResponse(
        "partials/search_results.html",
        {
            "request": request,
            "results": results["results"],
            "total": results["total"],
            "facets": results.get("facets", {}),
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "page_range": page_range,
            "query": q,
            "manufacturers": manufacturers,
            "eclass_ids": eclass_ids,
            "eclass_segments": eclass_segments,
            "order_units": order_units,
            "price_min": price_min,
            "price_max": price_max,
            "price_band": price_band,
            "exact_match": exact_match,
        },
    )


@app.get("/autocomplete", response_class=HTMLResponse)
async def autocomplete(
    request: Request,
    q: str = Query(..., min_length=2),
):
    """Autocomplete suggestions endpoint."""
    try:
        suggestions = await api.autocomplete(q)
    except httpx.ConnectError:
        suggestions = []

    return templates.TemplateResponse(
        "partials/autocomplete.html",
        {"request": request, "suggestions": suggestions, "query": q},
    )


@app.get("/product/{supplier_aid}", response_class=HTMLResponse)
async def product_detail(request: Request, supplier_aid: str):
    """Load product detail for modal."""
    try:
        product = await api.get_product(supplier_aid)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return templates.TemplateResponse(
                "partials/error.html",
                {"request": request, "message": "Product not found"},
            )
        raise
    except httpx.ConnectError:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "API connection failed"},
        )

    return templates.TemplateResponse(
        "partials/product_detail.html",
        {"request": request, "product": product},
    )


@app.get("/export/csv")
async def export_csv(
    q: str | None = Query(None),
    manufacturer: str | None = Query(None),
    eclass_id: str | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
):
    """Export search results as CSV."""
    all_results = []
    page = 1
    batch_size = 100

    while len(all_results) < settings.max_export_rows:
        try:
            data = await api.search(
                q=q,
                manufacturer=manufacturer,
                eclass_id=eclass_id,
                price_min=price_min,
                price_max=price_max,
                page=page,
                size=batch_size,
            )
        except httpx.ConnectError:
            break

        all_results.extend(data["results"])
        if len(data["results"]) < batch_size:
            break
        page += 1

    # Generate CSV
    output = io.StringIO()
    fieldnames = [
        "supplier_aid",
        "ean",
        "manufacturer_aid",
        "manufacturer_name",
        "description_short",
        "eclass_id",
        "price_amount",
        "price_currency",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for product in all_results:
        writer.writerow({k: product.get(k, "") for k in fieldnames})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@app.get("/export/json")
async def export_json(
    q: str | None = Query(None),
    manufacturer: str | None = Query(None),
    eclass_id: str | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
):
    """Export search results as JSON."""
    all_results = []
    page = 1
    batch_size = 100

    while len(all_results) < settings.max_export_rows:
        try:
            data = await api.search(
                q=q,
                manufacturer=manufacturer,
                eclass_id=eclass_id,
                price_min=price_min,
                price_max=price_max,
                page=page,
                size=batch_size,
            )
        except httpx.ConnectError:
            break

        all_results.extend(data["results"])
        if len(data["results"]) < batch_size:
            break
        page += 1

    return StreamingResponse(
        iter([json.dumps(all_results, ensure_ascii=False, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=products.json"},
    )
