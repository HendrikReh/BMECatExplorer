/**
 * BMECat Explorer Frontend - Minimal JavaScript helpers
 */

// Modal functions
function openModal() {
    document.getElementById('product-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('product-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modal on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeModal();
        hideAutocomplete();
    }
});

// Autocomplete functions
function selectSuggestion(suggestion) {
    const searchInput = document.getElementById('search-input');
    searchInput.value = suggestion;
    hideAutocomplete();
    // Trigger HTMX search
    htmx.trigger(searchInput, 'search');
}

function hideAutocomplete() {
    const autocomplete = document.getElementById('autocomplete-results');
    if (autocomplete) {
        autocomplete.classList.add('hidden');
        autocomplete.innerHTML = '';
    }
}

// Show autocomplete when results arrive
document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'autocomplete-results') {
        const autocomplete = document.getElementById('autocomplete-results');
        if (autocomplete.innerHTML.trim()) {
            autocomplete.classList.remove('hidden');
        } else {
            autocomplete.classList.add('hidden');
        }
    }
});

// Hide autocomplete when clicking outside
document.addEventListener('click', function(event) {
    const autocomplete = document.getElementById('autocomplete-results');
    const searchInput = document.getElementById('search-input');

    if (autocomplete && searchInput) {
        if (!autocomplete.contains(event.target) && event.target !== searchInput) {
            hideAutocomplete();
        }
    }
});

// Hide autocomplete when search input loses focus (with delay for click handling)
document.getElementById('search-input')?.addEventListener('blur', function() {
    setTimeout(hideAutocomplete, 200);
});

// Scroll to top when pagination changes
document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'results-container') {
        // Check if this was a pagination click (page parameter in URL)
        const requestUrl = event.detail.pathInfo?.requestPath || '';
        if (requestUrl.includes('page=')) {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }
});

// Update visibility of all clear filter buttons based on active selections
function updateClearButtonVisibility() {
    // Category (eclass_segment)
    const categoryBtn = document.getElementById('clear-category-btn');
    const hasCategory = document.querySelectorAll('[name="eclass_segment"]:checked').length > 0;
    if (categoryBtn) categoryBtn.classList.toggle('hidden', !hasCategory);

    // Price band
    const priceBtn = document.getElementById('clear-price-btn');
    const priceRadio = document.querySelector('[name="price_band"]:checked');
    const hasPrice = priceRadio && priceRadio.value !== '';
    if (priceBtn) priceBtn.classList.toggle('hidden', !hasPrice);

    // Unit (order_unit)
    const unitBtn = document.getElementById('clear-unit-btn');
    const hasUnit = document.querySelectorAll('#unit-list input[name="order_unit"]:checked').length > 0 ||
                    document.querySelectorAll('#selected-units input[name="order_unit"]').length > 0;
    if (unitBtn) unitBtn.classList.toggle('hidden', !hasUnit);

    // Manufacturer
    const mfrBtn = document.getElementById('clear-manufacturer-btn');
    const hasMfr = document.querySelectorAll('#manufacturer-list input[name="manufacturer"]:checked').length > 0 ||
                   document.querySelectorAll('#selected-manufacturers input[name="manufacturer"]').length > 0;
    if (mfrBtn) mfrBtn.classList.toggle('hidden', !hasMfr);

    // ECLASS ID
    const eclassBtn = document.getElementById('clear-eclass-id-btn');
    const hasEclass = document.querySelectorAll('#eclass-id-list input[name="eclass_id"]:checked').length > 0 ||
                      document.querySelectorAll('#selected-eclass-ids input[name="eclass_id"]').length > 0;
    if (eclassBtn) eclassBtn.classList.toggle('hidden', !hasEclass);
}

// Clear category filter only
function clearCategoryFilter() {
    const eclassSegmentCheckboxes = document.querySelectorAll('[name="eclass_segment"]');
    eclassSegmentCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    updateClearButtonVisibility();
    triggerSearch();
}

// Clear price filter only
function clearPriceFilter() {
    const priceBandRadios = document.querySelectorAll('[name="price_band"]');
    priceBandRadios.forEach(radio => {
        radio.checked = (radio.value === '');
    });
    updateClearButtonVisibility();
    triggerSearch();
}

// Clear manufacturer filter only
function clearManufacturerFilter() {
    // Clear all manufacturer checkboxes
    const manufacturerCheckboxes = document.querySelectorAll('#manufacturer-list input[name="manufacturer"]');
    manufacturerCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    // Clear selected chips
    const selectedContainer = document.getElementById('selected-manufacturers');
    if (selectedContainer) {
        selectedContainer.innerHTML = '';
    }
    // Clear search
    const searchBox = document.getElementById('manufacturer-search');
    if (searchBox) {
        searchBox.value = '';
        filterManufacturers('');
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Clear ECLASS ID filter only
function clearEclassIdFilter() {
    // Clear all ECLASS ID checkboxes
    const eclassIdCheckboxes = document.querySelectorAll('#eclass-id-list input[name="eclass_id"]');
    eclassIdCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    // Clear selected chips
    const selectedContainer = document.getElementById('selected-eclass-ids');
    if (selectedContainer) {
        selectedContainer.innerHTML = '';
    }
    // Clear search
    const searchBox = document.getElementById('eclass-id-search');
    if (searchBox) {
        searchBox.value = '';
        filterEclassIds('');
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Clear Unit filter only
function clearUnitFilter() {
    // Clear all unit checkboxes
    const unitCheckboxes = document.querySelectorAll('#unit-list input[name="order_unit"]');
    unitCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    // Clear selected chips
    const selectedContainer = document.getElementById('selected-units');
    if (selectedContainer) {
        selectedContainer.innerHTML = '';
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Handle manufacturer checkbox change
function handleManufacturerChange(checkbox) {
    updateClearButtonVisibility();
    triggerSearch();
}

// Remove a manufacturer from selection
function removeManufacturer(name) {
    // Uncheck the checkbox if it exists
    const checkbox = document.querySelector(`#manufacturer-list input[value="${CSS.escape(name)}"]`);
    if (checkbox) {
        checkbox.checked = false;
    }
    // Remove the chip
    const chip = document.querySelector(`#selected-manufacturers input[value="${CSS.escape(name)}"]`)?.parentElement;
    if (chip) {
        chip.remove();
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Handle ECLASS ID checkbox change
function handleEclassIdChange(checkbox) {
    updateClearButtonVisibility();
    triggerSearch();
}

// Remove an ECLASS ID from selection
function removeEclassId(eclassId) {
    // Uncheck the checkbox if it exists
    const checkbox = document.querySelector(`#eclass-id-list input[value="${CSS.escape(eclassId)}"]`);
    if (checkbox) {
        checkbox.checked = false;
    }
    // Remove the chip
    const chip = document.querySelector(`#selected-eclass-ids input[value="${CSS.escape(eclassId)}"]`)?.parentElement;
    if (chip) {
        chip.remove();
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Handle Unit checkbox change
function handleUnitChange(checkbox) {
    updateClearButtonVisibility();
    triggerSearch();
}

// Remove a Unit from selection
function removeUnit(unit) {
    // Uncheck the checkbox if it exists
    const checkbox = document.querySelector(`#unit-list input[value="${CSS.escape(unit)}"]`);
    if (checkbox) {
        checkbox.checked = false;
    }
    // Remove the chip
    const chip = document.querySelector(`#selected-units input[value="${CSS.escape(unit)}"]`)?.parentElement;
    if (chip) {
        chip.remove();
    }
    updateClearButtonVisibility();
    triggerSearch();
}

// Filter manufacturer list based on search input
function filterManufacturers(searchTerm) {
    const term = searchTerm.toLowerCase().trim();
    const listContainer = document.getElementById('manufacturer-list');
    const allManufacturers = document.getElementById('all-manufacturers');

    if (!listContainer || !allManufacturers) return;

    // Get currently selected manufacturers
    const selectedValues = new Set();
    document.querySelectorAll('#selected-manufacturers input[name="manufacturer"]').forEach(input => {
        selectedValues.add(input.value);
    });
    document.querySelectorAll('#manufacturer-list input[name="manufacturer"]:checked').forEach(input => {
        selectedValues.add(input.value);
    });

    if (term.length === 0) {
        // Show top 20 (default view)
        const items = allManufacturers.querySelectorAll('div');
        let html = '';
        let count = 0;
        items.forEach(item => {
            if (count >= 20) return;
            const value = item.dataset.value;
            const name = item.dataset.name;
            const itemCount = item.dataset.count;
            const checked = selectedValues.has(value) ? 'checked' : '';
            html += `
                <label class="manufacturer-item flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded" data-name="${name}">
                    <input type="checkbox" name="manufacturer" value="${escapeHtml(value)}" ${checked}
                        onchange="handleManufacturerChange(this)"
                        class="rounded text-primary focus:ring-primary">
                    <span class="flex-1 truncate" title="${escapeHtml(value)}">${escapeHtml(value)}</span>
                    <span class="text-gray-400 text-xs flex-shrink-0">${Number(itemCount).toLocaleString()}</span>
                </label>
            `;
            count++;
        });
        listContainer.innerHTML = html;
    } else {
        // Filter and show matching manufacturers
        const items = allManufacturers.querySelectorAll('div');
        let html = '';
        let count = 0;
        items.forEach(item => {
            if (count >= 30) return; // Show up to 30 matches
            const value = item.dataset.value;
            const name = item.dataset.name;
            const itemCount = item.dataset.count;
            if (name.includes(term)) {
                const checked = selectedValues.has(value) ? 'checked' : '';
                html += `
                    <label class="manufacturer-item flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded" data-name="${name}">
                        <input type="checkbox" name="manufacturer" value="${escapeHtml(value)}" ${checked}
                            onchange="handleManufacturerChange(this)"
                            class="rounded text-primary focus:ring-primary">
                        <span class="flex-1 truncate" title="${escapeHtml(value)}">${escapeHtml(value)}</span>
                        <span class="text-gray-400 text-xs flex-shrink-0">${Number(itemCount).toLocaleString()}</span>
                    </label>
                `;
                count++;
            }
        });
        if (count === 0) {
            html = '<p class="text-sm text-gray-500 p-2">No manufacturers found</p>';
        }
        listContainer.innerHTML = html;
    }
}

// Filter ECLASS ID list based on search input
function filterEclassIds(searchTerm) {
    const term = searchTerm.toLowerCase().trim();
    const listContainer = document.getElementById('eclass-id-list');
    const allEclassIds = document.getElementById('all-eclass-ids');

    if (!listContainer || !allEclassIds) return;

    // Get currently selected ECLASS IDs
    const selectedValues = new Set();
    document.querySelectorAll('#selected-eclass-ids input[name="eclass_id"]').forEach(input => {
        selectedValues.add(input.value);
    });
    document.querySelectorAll('#eclass-id-list input[name="eclass_id"]:checked').forEach(input => {
        selectedValues.add(input.value);
    });

    if (term.length === 0) {
        // Show top 20 (default view)
        const items = allEclassIds.querySelectorAll('div');
        let html = '';
        let count = 0;
        items.forEach(item => {
            if (count >= 20) return;
            const value = item.dataset.value;
            const name = item.dataset.name;
            const itemCount = item.dataset.count;
            const checked = selectedValues.has(value) ? 'checked' : '';
            html += `
                <label class="eclass-id-item flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded" data-value="${value}">
                    <input type="checkbox" name="eclass_id" value="${escapeHtml(value)}" ${checked}
                        onchange="handleEclassIdChange(this)"
                        class="rounded text-primary focus:ring-primary">
                    <span class="flex-1 truncate" title="${escapeHtml(name || value)}">${escapeHtml(value)}</span>
                    <span class="text-gray-400 text-xs flex-shrink-0">${Number(itemCount).toLocaleString()}</span>
                </label>
            `;
            count++;
        });
        listContainer.innerHTML = html;
    } else {
        // Filter and show matching ECLASS IDs
        const items = allEclassIds.querySelectorAll('div');
        let html = '';
        let count = 0;
        items.forEach(item => {
            if (count >= 30) return; // Show up to 30 matches
            const value = item.dataset.value;
            const name = item.dataset.name;
            const itemCount = item.dataset.count;
            // Search in both value and name
            if (value.includes(term) || name.includes(term)) {
                const checked = selectedValues.has(value) ? 'checked' : '';
                html += `
                    <label class="eclass-id-item flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1 rounded" data-value="${value}">
                        <input type="checkbox" name="eclass_id" value="${escapeHtml(value)}" ${checked}
                            onchange="handleEclassIdChange(this)"
                            class="rounded text-primary focus:ring-primary">
                        <span class="flex-1 truncate" title="${escapeHtml(name || value)}">${escapeHtml(value)}</span>
                        <span class="text-gray-400 text-xs flex-shrink-0">${Number(itemCount).toLocaleString()}</span>
                    </label>
                `;
                count++;
            }
        });
        if (count === 0) {
            html = '<p class="text-sm text-gray-500 p-2">No ECLASS IDs found</p>';
        }
        listContainer.innerHTML = html;
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Trigger search with all current filter values
function triggerSearch() {
    // Clear selections when search/filter changes since results will be different
    selectedProducts.clear();

    htmx.ajax('GET', '/search', {
        target: '#results-container',
        source: document.body,
        values: buildSearchParams(),
    });
}

// Change page size and trigger search
function changePageSize(size) {
    // Clear selections when page size changes
    selectedProducts.clear();

    const params = buildSearchParams();
    params.size = size;
    params.page = 1; // Reset to first page when changing page size
    htmx.ajax('GET', '/search', {
        target: '#results-container',
        source: document.body,
        values: params,
    });
}

// Set sort field/order and trigger search
function setSort(sortBy, order) {
    const sortByInput = document.getElementById('sort-by');
    const sortOrderInput = document.getElementById('sort-order');
    if (sortByInput) sortByInput.value = sortBy;
    if (sortOrderInput) sortOrderInput.value = order;

    selectedProducts.clear();
    const params = buildSearchParams();
    params.page = 1;
    htmx.ajax('GET', '/search', {
        target: '#results-container',
        source: document.body,
        values: params,
    });
}

// Build search parameters from all filter inputs
function buildSearchParams() {
    const params = {};

    // Search query
    const searchInput = document.getElementById('search-input');
    if (searchInput?.value) params.q = searchInput.value;

    // Price band
    const priceBand = document.querySelector('[name="price_band"]:checked');
    if (priceBand?.value) params.price_band = priceBand.value;

    // ECLASS segments (multi-select)
    const segments = [];
    document.querySelectorAll('[name="eclass_segment"]:checked').forEach(cb => {
        if (cb.value) segments.push(cb.value);
    });
    if (segments.length > 0) params.eclass_segment = segments;

    // Manufacturers (multi-select) - from checkboxes and hidden inputs in chips
    const manufacturers = new Set();
    document.querySelectorAll('#manufacturer-list input[name="manufacturer"]:checked').forEach(cb => {
        if (cb.value) manufacturers.add(cb.value);
    });
    document.querySelectorAll('#selected-manufacturers input[name="manufacturer"]').forEach(input => {
        if (input.value) manufacturers.add(input.value);
    });
    if (manufacturers.size > 0) params.manufacturer = Array.from(manufacturers);

    // ECLASS IDs (multi-select) - from checkboxes and hidden inputs in chips
    const eclassIds = new Set();
    document.querySelectorAll('#eclass-id-list input[name="eclass_id"]:checked').forEach(cb => {
        if (cb.value) eclassIds.add(cb.value);
    });
    document.querySelectorAll('#selected-eclass-ids input[name="eclass_id"]').forEach(input => {
        if (input.value) eclassIds.add(input.value);
    });
    if (eclassIds.size > 0) params.eclass_id = Array.from(eclassIds);

    // Order units (multi-select) - from checkboxes and hidden inputs in chips
    const orderUnits = new Set();
    document.querySelectorAll('#unit-list input[name="order_unit"]:checked').forEach(cb => {
        if (cb.value) orderUnits.add(cb.value);
    });
    document.querySelectorAll('#selected-units input[name="order_unit"]').forEach(input => {
        if (input.value) orderUnits.add(input.value);
    });
    if (orderUnits.size > 0) params.order_unit = Array.from(orderUnits);

    // Page size (preserve current selection)
    const pageSize = document.getElementById('page-size');
    if (pageSize?.value) params.size = pageSize.value;

    // Exact match toggle
    const exactMatch = document.getElementById('exact-match');
    if (exactMatch?.checked) params.exact_match = 'true';

    // Sorting
    const sortByInput = document.getElementById('sort-by');
    const sortOrderInput = document.getElementById('sort-order');
    if (sortByInput?.value) params.sort_by = sortByInput.value;
    if (sortOrderInput?.value) params.sort_order = sortOrderInput.value;

    return params;
}

// Clear filters and search
function clearFilters() {
    // Clear search input
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = '';

    // Clear price band radio buttons (select "Any price")
    const priceBandRadios = document.querySelectorAll('[name="price_band"]');
    priceBandRadios.forEach(radio => {
        radio.checked = (radio.value === '');
    });

    // Clear eclass segment checkboxes
    const eclassSegmentCheckboxes = document.querySelectorAll('[name="eclass_segment"]');
    eclassSegmentCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear manufacturer checkboxes
    const manufacturerCheckboxes = document.querySelectorAll('#manufacturer-list input[name="manufacturer"]');
    manufacturerCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear selected manufacturer chips
    const selectedManufacturers = document.getElementById('selected-manufacturers');
    if (selectedManufacturers) {
        selectedManufacturers.innerHTML = '';
    }

    // Clear manufacturer search
    const manufacturerSearch = document.getElementById('manufacturer-search');
    if (manufacturerSearch) {
        manufacturerSearch.value = '';
        filterManufacturers('');
    }

    // Clear ECLASS ID checkboxes
    const eclassIdCheckboxes = document.querySelectorAll('#eclass-id-list input[name="eclass_id"]');
    eclassIdCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear selected ECLASS ID chips
    const selectedEclassIds = document.getElementById('selected-eclass-ids');
    if (selectedEclassIds) {
        selectedEclassIds.innerHTML = '';
    }

    // Clear ECLASS ID search
    const eclassIdSearch = document.getElementById('eclass-id-search');
    if (eclassIdSearch) {
        eclassIdSearch.value = '';
        filterEclassIds('');
    }

    // Clear unit checkboxes
    const unitCheckboxes = document.querySelectorAll('#unit-list input[name="order_unit"]');
    unitCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    // Clear selected unit chips
    const selectedUnits = document.getElementById('selected-units');
    if (selectedUnits) {
        selectedUnits.innerHTML = '';
    }

    // Clear exact match toggle
    const exactMatch = document.getElementById('exact-match');
    if (exactMatch) {
        exactMatch.checked = false;
    }

    // Clear sorting
    const sortByInput = document.getElementById('sort-by');
    const sortOrderInput = document.getElementById('sort-order');
    if (sortByInput) sortByInput.value = '';
    if (sortOrderInput) sortOrderInput.value = '';

    // Update clear button visibility
    updateClearButtonVisibility();

    // Trigger a fresh search with cleared params
    htmx.ajax('GET', '/search', {
        target: '#results-container',
    });
}

// Initialize clear button visibility on page load
document.addEventListener('DOMContentLoaded', function() {
    updateClearButtonVisibility();

    // Add change listeners for Category and Price filters (they use HTMX directly)
    document.querySelectorAll('[name="eclass_segment"]').forEach(checkbox => {
        checkbox.addEventListener('change', updateClearButtonVisibility);
    });
    document.querySelectorAll('[name="price_band"]').forEach(radio => {
        radio.addEventListener('change', updateClearButtonVisibility);
    });
});

// Product selection tracking
// Store selected products across page navigation
let selectedProducts = new Map(); // supplier_aid -> product data

// Update selection count display
function updateSelectionCount() {
    // Sync checkboxes with stored selection
    document.querySelectorAll('.product-select').forEach(checkbox => {
        if (checkbox.checked) {
            const productData = JSON.parse(checkbox.dataset.product);
            selectedProducts.set(checkbox.value, productData);
        } else {
            selectedProducts.delete(checkbox.value);
        }
    });

    const count = selectedProducts.size;
    const selectionInfo = document.getElementById('selection-info');
    const selectionCount = document.getElementById('selection-count');

    if (selectionInfo && selectionCount) {
        if (count > 0) {
            selectionInfo.classList.remove('hidden');
            selectionInfo.classList.add('flex');
            selectionCount.textContent = count;
        } else {
            selectionInfo.classList.add('hidden');
            selectionInfo.classList.remove('flex');
        }
    }

    // Update select-all checkbox state
    updateSelectAllState();
}

// Update select-all checkbox based on current page selection
function updateSelectAllState() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.product-select');
    if (!selectAll || checkboxes.length === 0) return;

    const checkedCount = document.querySelectorAll('.product-select:checked').length;
    selectAll.checked = checkedCount === checkboxes.length;
    selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

// Toggle select all on current page
function toggleSelectAll(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll('.product-select');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    updateSelectionCount();
}

// Clear all selections
function clearSelection() {
    selectedProducts.clear();
    document.querySelectorAll('.product-select').forEach(checkbox => {
        checkbox.checked = false;
    });
    const selectAll = document.getElementById('select-all');
    if (selectAll) selectAll.checked = false;
    updateSelectionCount();
}

// Restore checkbox state after HTMX swap (page navigation)
function restoreSelectionState() {
    document.querySelectorAll('.product-select').forEach(checkbox => {
        if (selectedProducts.has(checkbox.value)) {
            checkbox.checked = true;
        }
    });
    updateSelectAllState();

    // Update selection info display
    const count = selectedProducts.size;
    const selectionInfo = document.getElementById('selection-info');
    const selectionCount = document.getElementById('selection-count');
    if (selectionInfo && selectionCount) {
        if (count > 0) {
            selectionInfo.classList.remove('hidden');
            selectionInfo.classList.add('flex');
            selectionCount.textContent = count;
        } else {
            selectionInfo.classList.add('hidden');
        }
    }
}

// Track last search params to detect filter/search changes
let lastSearchParams = '';

// Listen for HTMX requests to detect search/filter changes
document.body.addEventListener('htmx:beforeRequest', function(event) {
    if (event.detail.target?.id === 'results-container') {
        const requestPath = event.detail.pathInfo?.requestPath || '';
        // Extract search params (everything except page parameter)
        const url = new URL(requestPath, window.location.origin);
        url.searchParams.delete('page'); // Ignore page changes
        const currentParams = url.searchParams.toString();

        // If search/filter params changed (not just pagination), clear selections
        if (currentParams !== lastSearchParams) {
            selectedProducts.clear();
            lastSearchParams = currentParams;
        }
    }
});

// Listen for HTMX swaps to restore selection state
document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'results-container') {
        restoreSelectionState();
    }
});

// Get current search parameters for export metadata
function getCurrentSearchParams() {
    const params = {};

    const searchInput = document.getElementById('search-input');
    if (searchInput?.value) params.query = searchInput.value;

    const priceBand = document.querySelector('[name="price_band"]:checked');
    if (priceBand?.value) params.price_band = priceBand.value;

    const segments = [];
    document.querySelectorAll('[name="eclass_segment"]:checked').forEach(cb => {
        if (cb.value) segments.push(cb.value);
    });
    if (segments.length > 0) params.eclass_segments = segments;

    const manufacturers = [];
    document.querySelectorAll('#manufacturer-list input[name="manufacturer"]:checked').forEach(cb => {
        if (cb.value) manufacturers.push(cb.value);
    });
    document.querySelectorAll('#selected-manufacturers input[name="manufacturer"]').forEach(input => {
        if (input.value && !manufacturers.includes(input.value)) manufacturers.push(input.value);
    });
    if (manufacturers.length > 0) params.manufacturers = manufacturers;

    const eclassIds = [];
    document.querySelectorAll('#eclass-id-list input[name="eclass_id"]:checked').forEach(cb => {
        if (cb.value) eclassIds.push(cb.value);
    });
    document.querySelectorAll('#selected-eclass-ids input[name="eclass_id"]').forEach(input => {
        if (input.value && !eclassIds.includes(input.value)) eclassIds.push(input.value);
    });
    if (eclassIds.length > 0) params.eclass_ids = eclassIds;

    const orderUnits = [];
    document.querySelectorAll('#unit-list input[name="order_unit"]:checked').forEach(cb => {
        if (cb.value) orderUnits.push(cb.value);
    });
    document.querySelectorAll('#selected-units input[name="order_unit"]').forEach(input => {
        if (input.value && !orderUnits.includes(input.value)) orderUnits.push(input.value);
    });
    if (orderUnits.length > 0) params.order_units = orderUnits;

    return params;
}

// Generate timestamp for filename
function getTimestamp() {
    const now = new Date();
    return now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

// Export selected products
function exportSelected(format) {
    const products = Array.from(selectedProducts.values());

    if (products.length === 0) {
        alert('Please select at least one product to export.');
        return;
    }

    const searchParams = getCurrentSearchParams();
    const timestamp = getTimestamp();
    const filename = `product-export_${timestamp}.${format}`;

    // Get catalog stats from the page using IDs
    const totalProducts = document.getElementById('stat-total-products')?.textContent || 'N/A';
    const manufacturerCount = document.getElementById('stat-manufacturer-count')?.textContent || 'N/A';
    const categoryEl = document.getElementById('stat-category-count');
    const categoryCount = categoryEl?.textContent || 'N/A';
    const eclassIdCount = categoryEl?.dataset.eclassIdCount || 'N/A';

    const metadata = {
        export_timestamp: new Date().toISOString(),
        export_format: format.toUpperCase(),
        selected_count: products.length,
        search_parameters: searchParams,
        catalog_stats: {
            total_products_in_search: totalProducts,
            manufacturer_count: manufacturerCount,
            category_segments_count: categoryCount,
            eclass_id_count: eclassIdCount
        }
    };

    if (format === 'json') {
        exportAsJson(products, metadata, filename);
    } else {
        exportAsCsv(products, metadata, filename);
    }
}

// Export as JSON
function exportAsJson(products, metadata, filename) {
    const exportData = {
        metadata: metadata,
        products: products
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    downloadBlob(blob, filename);
}

// Export as CSV
function exportAsCsv(products, metadata, filename) {
    const lines = [];

    // Add metadata as comments
    lines.push('# BMECat Explorer - Product Export');
    lines.push(`# Export Timestamp: ${metadata.export_timestamp}`);
    lines.push(`# Selected Products: ${metadata.selected_count}`);
    if (metadata.search_parameters.query) {
        lines.push(`# Search Query: ${metadata.search_parameters.query}`);
    }
    if (metadata.search_parameters.manufacturers?.length > 0) {
        lines.push(`# Manufacturers Filter: ${metadata.search_parameters.manufacturers.join(', ')}`);
    }
    if (metadata.search_parameters.eclass_ids?.length > 0) {
        lines.push(`# ECLASS IDs Filter: ${metadata.search_parameters.eclass_ids.join(', ')}`);
    }
    if (metadata.search_parameters.eclass_segments?.length > 0) {
        lines.push(`# Categories Filter: ${metadata.search_parameters.eclass_segments.join(', ')}`);
    }
    if (metadata.search_parameters.order_units?.length > 0) {
        lines.push(`# Units Filter: ${metadata.search_parameters.order_units.join(', ')}`);
    }
    if (metadata.search_parameters.price_band) {
        lines.push(`# Price Band: ${metadata.search_parameters.price_band}`);
    }
    lines.push(`# Catalog Total Products: ${metadata.catalog_stats.total_products_in_search}`);
    lines.push(`# Catalog Manufacturers: ${metadata.catalog_stats.manufacturer_count}`);
    lines.push(
        `# Catalog Categories (segments): ${metadata.catalog_stats.category_segments_count}`
    );
    lines.push(`# Catalog ECLASS IDs: ${metadata.catalog_stats.eclass_id_count}`);
    lines.push('');

    // CSV headers
    const headers = ['supplier_aid', 'ean', 'manufacturer_aid', 'manufacturer_name', 'description_short', 'eclass_id', 'eclass_name', 'price_amount', 'price_currency', 'order_unit'];
    lines.push(headers.join(','));

    // CSV rows
    products.forEach(product => {
        const row = headers.map(header => {
            const value = product[header] ?? '';
            // Escape CSV values
            const strValue = String(value);
            if (strValue.includes(',') || strValue.includes('"') || strValue.includes('\n')) {
                return `"${strValue.replace(/"/g, '""')}"`;
            }
            return strValue;
        });
        lines.push(row.join(','));
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    downloadBlob(blob, filename);
}

// Download blob as file
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Delayed tooltips (data-tooltip)
// ---------------------------------------------------------------------------

(() => {
    const DELAY_MS = 1000;
    let tooltipEl = null;
    let showTimer = null;

    function ensureTooltip() {
        if (tooltipEl) return tooltipEl;
        tooltipEl = document.createElement('div');
        tooltipEl.id = 'custom-tooltip';
        tooltipEl.className = 'custom-tooltip hidden';
        document.body.appendChild(tooltipEl);
        return tooltipEl;
    }

    function positionTooltip(target) {
        if (!tooltipEl || tooltipEl.classList.contains('hidden')) return;

        const rect = target.getBoundingClientRect();
        const padding = 8;
        const top = rect.bottom + padding + window.scrollY;
        let left = rect.left + rect.width / 2 + window.scrollX;

        tooltipEl.style.top = `${top}px`;
        tooltipEl.style.left = `${left}px`;

        // Keep within viewport horizontally.
        const tooltipRect = tooltipEl.getBoundingClientRect();
        const minLeft = 8;
        const maxLeft = window.innerWidth - tooltipRect.width - 8;
        const currentLeft = tooltipRect.left;
        if (currentLeft < minLeft) {
            left += minLeft - currentLeft;
            tooltipEl.style.left = `${left}px`;
        } else if (currentLeft > maxLeft) {
            left -= currentLeft - maxLeft;
            tooltipEl.style.left = `${left}px`;
        }
    }

    function showTooltip(target) {
        const text = target.dataset.tooltip;
        if (!text) return;
        const el = ensureTooltip();
        el.textContent = text;
        el.classList.remove('hidden');
        positionTooltip(target);
    }

    function hideTooltip() {
        if (showTimer) {
            clearTimeout(showTimer);
            showTimer = null;
        }
        if (tooltipEl) {
            tooltipEl.classList.add('hidden');
        }
    }

    function bindTooltip(target) {
        if (target.dataset.tooltipBound) return;
        target.dataset.tooltipBound = 'true';

        const onEnter = () => {
            if (showTimer) clearTimeout(showTimer);
            showTimer = setTimeout(() => showTooltip(target), DELAY_MS);
        };

        target.addEventListener('mouseenter', onEnter);
        target.addEventListener('focus', onEnter);
        target.addEventListener('mouseleave', hideTooltip);
        target.addEventListener('blur', hideTooltip);
        target.addEventListener('mousemove', () => positionTooltip(target));
    }

    function initTooltips(root = document) {
        root.querySelectorAll('[data-tooltip]').forEach(bindTooltip);
    }

    document.addEventListener('DOMContentLoaded', () => initTooltips());

    // Re-bind after HTMX swaps partials.
    document.body.addEventListener('htmx:afterSwap', (event) => {
        if (event.detail?.target) {
            initTooltips(event.detail.target);
        }
    });
})();
