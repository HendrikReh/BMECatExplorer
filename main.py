#!/usr/bin/env python3
"""BMECat 1.2 XML to JSON Lines converter optimized for large files."""

import json
import sys

from lxml import etree

BMECAT_NS = "http://www.bmecat.org/bmecat/1.2/bmecat_new_catalog"
NS = {"bc": BMECAT_NS}

# Pre-compute namespaced tags for iterparse
ARTICLE_TAG = f"{{{BMECAT_NS}}}ARTICLE"
HEADER_TAG = f"{{{BMECAT_NS}}}HEADER"

# XPath expressions for articles (compiled once)
XPATH_SUPPLIER_AID = etree.XPath("bc:SUPPLIER_AID/text()", namespaces=NS)
XPATH_SHORT_DESC = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:DESCRIPTION_SHORT/text()", namespaces=NS
)
XPATH_LONG_DESC = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:DESCRIPTION_LONG/text()", namespaces=NS
)
XPATH_EAN = etree.XPath("bc:ARTICLE_DETAILS/bc:EAN/text()", namespaces=NS)
XPATH_MANUFACTURER_AID = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:MANUFACTURER_AID/text()", namespaces=NS
)
XPATH_MANUFACTURER_NAME = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:MANUFACTURER_NAME/text()", namespaces=NS
)
XPATH_DELIVERY_TIME = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:DELIVERY_TIME/text()", namespaces=NS
)
XPATH_ARTICLE_STATUS = etree.XPath(
    "bc:ARTICLE_DETAILS/bc:ARTICLE_STATUS", namespaces=NS
)
XPATH_PRICES = etree.XPath("bc:ARTICLE_PRICE_DETAILS/bc:ARTICLE_PRICE", namespaces=NS)
XPATH_DAILY_PRICE = etree.XPath(
    "bc:ARTICLE_PRICE_DETAILS/bc:DAILY_PRICE/text()", namespaces=NS
)
XPATH_PRICE_AMOUNT = etree.XPath("bc:PRICE_AMOUNT/text()", namespaces=NS)
XPATH_PRICE_CURRENCY = etree.XPath("bc:PRICE_CURRENCY/text()", namespaces=NS)
XPATH_TAX = etree.XPath("bc:TAX/text()", namespaces=NS)
XPATH_ORDER_UNIT = etree.XPath(
    "bc:ARTICLE_ORDER_DETAILS/bc:ORDER_UNIT/text()", namespaces=NS
)
XPATH_PRICE_QUANTITY = etree.XPath(
    "bc:ARTICLE_ORDER_DETAILS/bc:PRICE_QUANTITY/text()", namespaces=NS
)
XPATH_QUANTITY_MIN = etree.XPath(
    "bc:ARTICLE_ORDER_DETAILS/bc:QUANTITY_MIN/text()", namespaces=NS
)
XPATH_QUANTITY_INTERVAL = etree.XPath(
    "bc:ARTICLE_ORDER_DETAILS/bc:QUANTITY_INTERVAL/text()", namespaces=NS
)
XPATH_ECLASS_ID = etree.XPath(
    "bc:ARTICLE_FEATURES/bc:REFERENCE_FEATURE_GROUP_ID/text()", namespaces=NS
)
XPATH_ECLASS_SYSTEM = etree.XPath(
    "bc:ARTICLE_FEATURES/bc:REFERENCE_FEATURE_SYSTEM_NAME/text()", namespaces=NS
)
XPATH_MIME_INFO = etree.XPath("bc:MIME_INFO/bc:MIME", namespaces=NS)
XPATH_MIME_TYPE = etree.XPath("bc:MIME_TYPE/text()", namespaces=NS)
XPATH_MIME_SOURCE = etree.XPath("bc:MIME_SOURCE/text()", namespaces=NS)
XPATH_MIME_DESCR = etree.XPath("bc:MIME_DESCR/text()", namespaces=NS)
XPATH_MIME_PURPOSE = etree.XPath("bc:MIME_PURPOSE/text()", namespaces=NS)

# XPath expressions for header
XPATH_CATALOG_ID = etree.XPath("bc:CATALOG/bc:CATALOG_ID/text()", namespaces=NS)
XPATH_CATALOG_VERSION = etree.XPath(
    "bc:CATALOG/bc:CATALOG_VERSION/text()", namespaces=NS
)
XPATH_CATALOG_NAME = etree.XPath("bc:CATALOG/bc:CATALOG_NAME/text()", namespaces=NS)
XPATH_LANGUAGE = etree.XPath("bc:CATALOG/bc:LANGUAGE/text()", namespaces=NS)
XPATH_TERRITORY = etree.XPath("bc:CATALOG/bc:TERRITORY/text()", namespaces=NS)
XPATH_CURRENCY = etree.XPath("bc:CATALOG/bc:CURRENCY/text()", namespaces=NS)
XPATH_GEN_DATE = etree.XPath(
    "bc:CATALOG/bc:DATETIME[@type='generation_date']/bc:DATE/text()", namespaces=NS
)
XPATH_GEN_TIME = etree.XPath(
    "bc:CATALOG/bc:DATETIME[@type='generation_date']/bc:TIME/text()", namespaces=NS
)
XPATH_SUPPLIER_ID = etree.XPath("bc:SUPPLIER/bc:SUPPLIER_ID/text()", namespaces=NS)
XPATH_SUPPLIER_NAME = etree.XPath("bc:SUPPLIER/bc:SUPPLIER_NAME/text()", namespaces=NS)
XPATH_BUYER_NAME = etree.XPath("bc:BUYER/bc:BUYER_NAME/text()", namespaces=NS)
XPATH_AGREEMENT_ID = etree.XPath("bc:AGREEMENT/bc:AGREEMENT_ID/text()", namespaces=NS)
XPATH_AGREEMENT_START = etree.XPath(
    "bc:AGREEMENT/bc:DATETIME[@type='agreement_start_date']/bc:DATE/text()",
    namespaces=NS,
)
XPATH_AGREEMENT_END = etree.XPath(
    "bc:AGREEMENT/bc:DATETIME[@type='agreement_end_date']/bc:DATE/text()", namespaces=NS
)


def first_or_none(results: list):
    """Return first element from XPath result or None."""
    return results[0] if results else None


def extract_header(input_xml_path: str) -> dict:
    """Extract catalog header metadata."""
    header = {}
    context = etree.iterparse(input_xml_path, events=("end",), tag=HEADER_TAG)

    for _, elem in context:
        # Catalog info
        if val := first_or_none(XPATH_CATALOG_ID(elem)):
            header["catalog_id"] = val
        if val := first_or_none(XPATH_CATALOG_VERSION(elem)):
            header["catalog_version"] = val
        if val := first_or_none(XPATH_CATALOG_NAME(elem)):
            header["catalog_name"] = val
        if val := first_or_none(XPATH_LANGUAGE(elem)):
            header["language"] = val
        if val := first_or_none(XPATH_TERRITORY(elem)):
            header["territory"] = val
        if val := first_or_none(XPATH_CURRENCY(elem)):
            header["currency"] = val

        # Generation timestamp
        gen_date = first_or_none(XPATH_GEN_DATE(elem))
        gen_time = first_or_none(XPATH_GEN_TIME(elem))
        if gen_date:
            header["generated_at"] = f"{gen_date}T{gen_time}" if gen_time else gen_date

        # Supplier info
        if val := first_or_none(XPATH_SUPPLIER_ID(elem)):
            header["supplier_id"] = val
        if val := first_or_none(XPATH_SUPPLIER_NAME(elem)):
            header["supplier_name"] = val

        # Buyer info
        if val := first_or_none(XPATH_BUYER_NAME(elem)):
            if val.strip():
                header["buyer_name"] = val

        # Agreement info
        if val := first_or_none(XPATH_AGREEMENT_ID(elem)):
            header["agreement_id"] = val
        if val := first_or_none(XPATH_AGREEMENT_START(elem)):
            header["agreement_start"] = val
        if val := first_or_none(XPATH_AGREEMENT_END(elem)):
            header["agreement_end"] = val

        elem.clear()
        break  # Only one header

    del context
    return header


def extract_article(elem) -> dict:
    """Extract article data using pre-compiled XPath expressions."""
    data = {}

    # Article mode attribute
    if mode := elem.get("mode"):
        data["mode"] = mode

    # Basic identifiers
    if val := first_or_none(XPATH_SUPPLIER_AID(elem)):
        data["supplier_aid"] = val
    if val := first_or_none(XPATH_EAN(elem)):
        data["ean"] = val
    if val := first_or_none(XPATH_MANUFACTURER_AID(elem)):
        data["manufacturer_aid"] = val
    if val := first_or_none(XPATH_MANUFACTURER_NAME(elem)):
        data["manufacturer_name"] = val

    # Descriptions
    if val := first_or_none(XPATH_SHORT_DESC(elem)):
        data["description_short"] = val
    if val := first_or_none(XPATH_LONG_DESC(elem)):
        data["description_long"] = val

    # Article status
    status_elem = first_or_none(XPATH_ARTICLE_STATUS(elem))
    if status_elem is not None:
        status = {}
        if status_elem.text:
            status["text"] = status_elem.text
        if status_type := status_elem.get("type"):
            status["type"] = status_type
        if status:
            data["article_status"] = status

    # Delivery and ordering
    if val := first_or_none(XPATH_DELIVERY_TIME(elem)):
        data["delivery_time"] = int(val)
    if val := first_or_none(XPATH_ORDER_UNIT(elem)):
        data["order_unit"] = val
    if val := first_or_none(XPATH_PRICE_QUANTITY(elem)):
        data["price_quantity"] = int(val)
    if val := first_or_none(XPATH_QUANTITY_MIN(elem)):
        data["quantity_min"] = int(val)
    if val := first_or_none(XPATH_QUANTITY_INTERVAL(elem)):
        data["quantity_interval"] = int(val)

    # Classification (ECLASS)
    if val := first_or_none(XPATH_ECLASS_ID(elem)):
        data["eclass_id"] = val
    if val := first_or_none(XPATH_ECLASS_SYSTEM(elem)):
        data["eclass_system"] = val

    # Daily price flag
    if val := first_or_none(XPATH_DAILY_PRICE(elem)):
        data["daily_price"] = val.upper() == "TRUE"

    # Price extraction
    price_elems = XPATH_PRICES(elem)
    if price_elems:
        prices = []
        for p in price_elems:
            price = {"price_type": p.get("price_type")}
            if amount := first_or_none(XPATH_PRICE_AMOUNT(p)):
                price["amount"] = float(amount)
            if currency := first_or_none(XPATH_PRICE_CURRENCY(p)):
                price["currency"] = currency
            if tax := first_or_none(XPATH_TAX(p)):
                price["tax"] = float(tax)
            prices.append(price)
        data["prices"] = prices

    # Media/images (all MIME entries)
    mime_elems = XPATH_MIME_INFO(elem)
    if mime_elems:
        media = []
        for m in mime_elems:
            mime_entry = {}
            if val := first_or_none(XPATH_MIME_SOURCE(m)):
                mime_entry["source"] = val.strip()
            if val := first_or_none(XPATH_MIME_TYPE(m)):
                mime_entry["type"] = val
            if val := first_or_none(XPATH_MIME_DESCR(m)):
                mime_entry["description"] = val
            if val := first_or_none(XPATH_MIME_PURPOSE(m)):
                mime_entry["purpose"] = val
            if mime_entry:
                media.append(mime_entry)
        if media:
            data["media"] = media

    return data


def bmecat_to_jsonlines(
    input_xml_path: str, output_jsonl_path: str, header_path: str | None = None
) -> int:
    """
    Convert BMECat XML to JSON Lines format.

    Returns the number of articles processed.
    """
    # Extract and save header if path provided
    if header_path:
        header = extract_header(input_xml_path)
        with open(header_path, "w", encoding="utf-8") as f:
            json.dump(header, f, ensure_ascii=False, indent=2)
        print(f"Header saved to {header_path}", file=sys.stderr)

    count = 0
    with open(output_jsonl_path, "w", encoding="utf-8") as fout:
        # Use iterparse with tag filter for memory-efficient streaming
        context = etree.iterparse(input_xml_path, events=("end",), tag=ARTICLE_TAG)

        for _, elem in context:
            rec = extract_article(elem)
            fout.write(json.dumps(rec, ensure_ascii=False))
            fout.write("\n")
            count += 1

            # Memory cleanup: clear element and remove processed siblings
            elem.clear(keep_tail=True)
            while elem.getprevious() is not None:
                del elem.getparent()[0]

            # Progress indicator every 100k articles
            if count % 100000 == 0:
                print(f"Processed {count:,} articles...", file=sys.stderr)

        del context

    return count


def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            "Usage: python main.py input.xml output.jsonl [header.json]",
            file=sys.stderr,
        )
        print(
            "  header.json: optional file to save catalog header metadata",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    header_path = sys.argv[3] if len(sys.argv) == 4 else None

    print(f"Converting {input_path} -> {output_path}", file=sys.stderr)

    count = bmecat_to_jsonlines(input_path, output_path, header_path)
    print(f"Done. Converted {count:,} articles.", file=sys.stderr)


if __name__ == "__main__":
    main()
