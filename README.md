# Shopify Product Tag Manager

A Python script for bulk managing product tags in a Shopify store. Specifically designed to filter out certain product categories and add the "Premier Gear" tag to selected products.

## Features

- Fetches all products from Shopify using GraphQL API
- Stores product data in a local SQLite database
- Removes products with specific excluded tags:
  - "Like New & Gently Used Saddles"
  - "Outlet"
  - "Like New"
  - "Saddles"
  - "Gift Card"
  - "Premier Gear"
- Adds "Premier Gear" tag to remaining products
- Supports dry-run mode for testing
- Allows limiting the number of products to update

## Prerequisites

- Python 3.x
- Shopify Admin API access
- Required Python packages (install via pip):
  - requests
  - python-dotenv
  - sqlite3 (usually included with Python)

## Setup

1. Clone this repository
2. Create a `.env` file with your Shopify credentials:

```
SHOPIFY_SHOP_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-access-token
```

## Usage

Basic usage (dry run):

```bash
python main.py
```

DRY RUN FIRST! Update products with limit:

```bash
python main.py --limit 1
```

Apply changes to 1 product:

```bash
python main.py --apply --limit 1
```

Apply changes to all products:

```bash
python main.py --apply
```

Options:

- `--apply`: Actually apply changes to Shopify (without this flag, runs in dry-run mode)
- `--limit n`: Process only n products (useful for testing)

## Safety Features

- Dry-run mode by default
- Local database backup of all products
- Pagination handling for large product catalogs
- Detailed logging of all operations
- Error handling for API requests

## Warning

Always run in dry-run mode first and verify the changes before using the --apply flag to make actual changes to your Shopify store.
