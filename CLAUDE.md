# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BMECatExplorer is a Python utility for converting BMECat XML product catalogs to JSON Lines format. BMECat is a standardized XML format for electronic product catalogs commonly used in B2B e-commerce.

## Commands

```bash
# Install dependencies
uv sync

# Run the converter
uv run python main.py data/input.xml data/output.jsonl
```

## Architecture

Single-script converter (`main.py`) that:

- Uses `lxml.etree.iterparse` for memory-efficient streaming of large XML files
- Pre-compiled XPath expressions for faster repeated queries
- Parses BMECat 1.2 namespace (`http://www.bmecat.org/bmecat/1.2/bmecat_new_catalog`)
- Extracts ARTICLE elements with supplier ID, descriptions, manufacturer, EAN, ECLASS classification, pricing, and images
- Outputs one JSON object per line (JSONL format)

The streaming approach with element cleanup (`elem.clear()` and parent deletion) is essential for handling large catalog files (~800MB / 2M+ articles).

## Dependencies

- Python 3.12+
- lxml (add via `uv add lxml`)