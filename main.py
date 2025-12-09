#!/usr/bin/env python3
"""BMECat 1.2 XML to JSON Lines converter optimized for large files."""

import json
import sys
from lxml import etree

BMECAT_NS = "http://www.bmecat.org/bmecat/1.2/bmecat_new_catalog"
NS = {"bc": BMECAT_NS}

# Pre-compute namespaced tag for iterparse
ARTICLE_TAG = f"{{{BMECAT_NS}}}ARTICLE"

# XPath expressions (compiled once)
XPATH_SUPPLIER_AID = etree.XPath("bc:SUPPLIER_AID/text()", namespaces=NS)
XPATH_SHORT_DESC = etree.XPath("bc:ARTICLE_DETAILS/bc:DESCRIPTION_SHORT/text()", namespaces=NS)
XPATH_LONG_DESC = etree.XPath("bc:ARTICLE_DETAILS/bc:DESCRIPTION_LONG/text()", namespaces=NS)
XPATH_EAN = etree.XPath("bc:ARTICLE_DETAILS/bc:EAN/text()", namespaces=NS)
XPATH_MANUFACTURER_AID = etree.XPath("bc:ARTICLE_DETAILS/bc:MANUFACTURER_AID/text()", namespaces=NS)
XPATH_MANUFACTURER_NAME = etree.XPath("bc:ARTICLE_DETAILS/bc:MANUFACTURER_NAME/text()", namespaces=NS)
XPATH_DELIVERY_TIME = etree.XPath("bc:ARTICLE_DETAILS/bc:DELIVERY_TIME/text()", namespaces=NS)
XPATH_PRICES = etree.XPath("bc:ARTICLE_PRICE_DETAILS/bc:ARTICLE_PRICE", namespaces=NS)
XPATH_PRICE_AMOUNT = etree.XPath("bc:PRICE_AMOUNT/text()", namespaces=NS)
XPATH_PRICE_CURRENCY = etree.XPath("bc:PRICE_CURRENCY/text()", namespaces=NS)
XPATH_TAX = etree.XPath("bc:TAX/text()", namespaces=NS)
XPATH_ORDER_UNIT = etree.XPath("bc:ARTICLE_ORDER_DETAILS/bc:ORDER_UNIT/text()", namespaces=NS)
XPATH_PRICE_QUANTITY = etree.XPath("bc:ARTICLE_ORDER_DETAILS/bc:PRICE_QUANTITY/text()", namespaces=NS)
XPATH_QUANTITY_MIN = etree.XPath("bc:ARTICLE_ORDER_DETAILS/bc:QUANTITY_MIN/text()", namespaces=NS)
XPATH_ECLASS_ID = etree.XPath("bc:ARTICLE_FEATURES/bc:REFERENCE_FEATURE_GROUP_ID/text()", namespaces=NS)
XPATH_MIME_SOURCE = etree.XPath("bc:MIME_INFO/bc:MIME/bc:MIME_SOURCE/text()", namespaces=NS)


def first_or_none(results: list):
    """Return first element from XPath result or None."""
    return results[0] if results else None


def extract_article(elem) -> dict:
    """Extract article data using pre-compiled XPath expressions."""
    data = {}

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

    # Delivery and ordering
    if val := first_or_none(XPATH_DELIVERY_TIME(elem)):
        data["delivery_time"] = int(val)
    if val := first_or_none(XPATH_ORDER_UNIT(elem)):
        data["order_unit"] = val
    if val := first_or_none(XPATH_PRICE_QUANTITY(elem)):
        data["price_quantity"] = int(val)
    if val := first_or_none(XPATH_QUANTITY_MIN(elem)):
        data["quantity_min"] = int(val)

    # Classification (ECLASS)
    if val := first_or_none(XPATH_ECLASS_ID(elem)):
        data["eclass_id"] = val

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

    # Image
    if val := first_or_none(XPATH_MIME_SOURCE(elem)):
        data["image"] = val.strip()

    return data


def bmecat_to_jsonlines(input_xml_path: str, output_jsonl_path: str) -> int:
    """
    Convert BMECat XML to JSON Lines format.

    Returns the number of articles processed.
    """
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
    if len(sys.argv) != 3:
        print("Usage: python main.py input.xml output.jsonl", file=sys.stderr)
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    print(f"Converting {input_path} -> {output_path}", file=sys.stderr)

    count = bmecat_to_jsonlines(input_path, output_path)
    print(f"Done. Converted {count:,} articles.", file=sys.stderr)


if __name__ == "__main__":
    main()
