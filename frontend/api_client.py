"""HTTP client for consuming the backend API."""

import httpx


class APIClient:
    """Async HTTP client for the BMECat Explorer backend API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the API client.

        Args:
            base_url: Base URL of the backend API (e.g., http://localhost:9019)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a GET request to the API."""
        response = await self._client.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def search(
        self,
        q: str | None = None,
        manufacturers: list[str] | None = None,
        eclass_ids: list[str] | None = None,
        eclass_segments: list[str] | None = None,
        order_units: list[str] | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        price_band: str | None = None,
        exact_match: bool = False,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        size: int = 25,
    ) -> dict:
        """Search products with filters.

        Args:
            q: Search query text
            manufacturers: Filter by manufacturer names (multiple allowed)
            eclass_ids: Filter by ECLASS IDs (multiple allowed)
            eclass_segments: Filter by ECLASS segments (2-digit prefix), multiple
            order_units: Filter by order units (C62, MTR, etc.), multiple allowed
            price_min: Minimum price filter
            price_max: Maximum price filter
            price_band: Filter by price band (0-10, 10-50, etc.)
            exact_match: If True, search for exact matches on EAN, supplier ID, etc.
            sort_by: Optional sort field (supplier_aid, manufacturer_name,
                eclass_id, price_unit_amount)
            sort_order: Sort order (asc or desc)
            page: Page number (1-indexed)
            size: Results per page

        Returns:
            Search response with results, total count, and facets
        """
        params: list[tuple[str, str | int | float | bool]] = [
            ("page", page),
            ("size", size),
        ]
        if q:
            params.append(("q", q))
        if manufacturers:
            for mfr in manufacturers:
                params.append(("manufacturer", mfr))
        if eclass_ids:
            for eid in eclass_ids:
                params.append(("eclass_id", eid))
        if eclass_segments:
            for segment in eclass_segments:
                params.append(("eclass_segment", segment))
        if order_units:
            for unit in order_units:
                params.append(("order_unit", unit))
        if price_min is not None:
            params.append(("price_min", price_min))
        if price_max is not None:
            params.append(("price_max", price_max))
        if price_band:
            params.append(("price_band", price_band))
        if exact_match:
            params.append(("exact_match", "true"))
        if sort_by:
            params.append(("sort_by", sort_by))
        if sort_order:
            params.append(("sort_order", sort_order))
        return await self._get("/api/v1/search", params)

    async def autocomplete(self, q: str) -> list[str]:
        """Get autocomplete suggestions.

        Args:
            q: Partial search term (minimum 2 characters)

        Returns:
            List of suggestion strings
        """
        result = await self._get("/api/v1/search/autocomplete", {"q": q})
        return result.get("suggestions", [])

    async def get_product(self, supplier_aid: str) -> dict:
        """Get a single product by ID.

        Args:
            supplier_aid: Supplier article ID

        Returns:
            Product details
        """
        return await self._get(f"/api/v1/products/{supplier_aid}")

    async def get_facets(self) -> dict:
        """Get all available filter facets.

        Returns:
            Facets with manufacturers and eclass_ids
        """
        return await self._get("/api/v1/facets")

    async def get_catalogs(self) -> dict:
        """Get list of available catalogs.

        Returns:
            Catalog list with product counts
        """
        return await self._get("/api/v1/catalogs")
