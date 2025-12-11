"""HTTP client for consuming the backend API."""

import httpx


class APIClient:
    """Async HTTP client for the BMECatDemo backend API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the API client.

        Args:
            base_url: Base URL of the backend API (e.g., http://localhost:9019)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a GET request to the API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()

    async def search(
        self,
        q: str | None = None,
        manufacturer: str | None = None,
        eclass_id: str | None = None,
        eclass_segment: str | None = None,
        order_unit: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        price_band: str | None = None,
        page: int = 1,
        size: int = 25,
    ) -> dict:
        """Search products with filters.

        Args:
            q: Search query text
            manufacturer: Filter by manufacturer name
            eclass_id: Filter by ECLASS ID
            eclass_segment: Filter by ECLASS segment (first 2 digits)
            order_unit: Filter by order unit (C62, MTR, etc.)
            price_min: Minimum price filter
            price_max: Maximum price filter
            price_band: Filter by price band (0-10, 10-50, etc.)
            page: Page number (1-indexed)
            size: Results per page

        Returns:
            Search response with results, total count, and facets
        """
        params: dict = {"page": page, "size": size}
        if q:
            params["q"] = q
        if manufacturer:
            params["manufacturer"] = manufacturer
        if eclass_id:
            params["eclass_id"] = eclass_id
        if eclass_segment:
            params["eclass_segment"] = eclass_segment
        if order_unit:
            params["order_unit"] = order_unit
        if price_min is not None:
            params["price_min"] = price_min
        if price_max is not None:
            params["price_max"] = price_max
        if price_band:
            params["price_band"] = price_band
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
