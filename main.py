import argparse
import os
import sqlite3
from typing import Dict, List

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

shop_url = os.getenv('SHOPIFY_SHOP_URL')
access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

def create_database():
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect('shopify_products.db')
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        shopify_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        tags TEXT
    )
    ''')
    
    conn.commit()
    return conn

def get_all_products_graphql():
    products = []
    cursor = None
    has_next_page = True
    
    while has_next_page:
        query = """
        {
            products(first: 250 %s) {
                edges {
                    cursor
                    node {
                        id
                        title
                        tags
                        status
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """ % (', after: "%s"' % cursor if cursor else '')
        
        url = f"{shop_url}/admin/api/2024-10/graphql.json"
        
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json={'query': query}, headers=headers)
            response.raise_for_status()
            
            json_response = response.json()
            
            if 'errors' in json_response:
                print("GraphQL errors:", json_response['errors'])
                break
                
            data = json_response['data']['products']
            
            # Extract products from the response
            for edge in data['edges']:
                if edge['node'].get('status') == 'ACTIVE':
                    products.append(edge['node'])
                cursor = edge['cursor']
            
            has_next_page = data['pageInfo']['hasNextPage']
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break
            
    return products

def save_products_to_db(products, conn):
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM products')
    
    # Insert all products
    for product in products:
        cursor.execute(
            'INSERT INTO products (shopify_id, title, tags) VALUES (?, ?, ?)',
            (
                product['id'],
                product['title'],
                ','.join(product['tags']) if product['tags'] else ''
            )
        )
    
    conn.commit()

def clean_products_by_tags(conn):
    cursor = conn.cursor()
    
    # Tags to exclude
    exclude_tags = [
        "Like New & Gently Used Saddles",
        "Outlet",
        "Like New",
        "Saddles",
        "Gift Card",
        "Premier Gear"
    ]
    
    # Count products before cleanup
    cursor.execute('SELECT COUNT(*) FROM products')
    count_before = cursor.fetchone()[0]
    
    # Build the SQL query dynamically
    conditions = []
    for tag in exclude_tags:
        conditions.append(f"tags LIKE '%{tag}%'")
    
    where_clause = ' OR '.join(conditions)
    delete_query = f'DELETE FROM products WHERE {where_clause}'
    
    # Execute the deletion
    cursor.execute(delete_query)
    conn.commit()
    
    # Count products after cleanup
    cursor.execute('SELECT COUNT(*) FROM products')
    count_after = cursor.fetchone()[0]
    
    removed_count = count_before - count_after
    print(f"Removed {removed_count} products with excluded tags")
    print(f"Remaining products in database: {count_after}")

def add_premier_gear_tag(conn):
    cursor = conn.cursor()
    
    # Count products before update
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    
    # Update all remaining products to add "Premier Gear" tag
    cursor.execute('''
        UPDATE products 
        SET tags = CASE
            WHEN tags = '' OR tags IS NULL THEN 'Premier Gear'
            ELSE tags || ',Premier Gear'
        END
    ''')
    
    conn.commit()
    print(f"Added 'Premier Gear' tag to {count} products")

def get_products_to_update(conn, limit: int = None) -> List[Dict]:
    """Get products from SQLite that need tag updates"""
    cursor = conn.cursor()
    
    if limit:
        cursor.execute('SELECT shopify_id, title, tags FROM products LIMIT ?', (limit,))
    else:
        cursor.execute('SELECT shopify_id, title, tags FROM products')
        
    products = cursor.fetchall()
    
    return [
        {
            'id': product[0],
            'title': product[1],
            'tags': product[2].split(',') if product[2] else []
        }
        for product in products
    ]

def update_shopify_products(products: List[Dict], dry_run: bool = True):
    """Update Shopify products with new tags"""
    
    update_mutation = """
    mutation productUpdate($input: ProductInput!) {
        productUpdate(input: $input) {
            product {
                id
                title
                tags
                status
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    url = f"{shop_url}/admin/api/2024-10/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    print(f"{'DRY RUN: ' if dry_run else ''}Preparing to update {len(products)} products...")
    
    success_count = 0
    error_count = 0
    
    for product in products:
        variables = {
            "input": {
                "id": product['id'],
                "tags": product['tags']
            }
        }
        
        if dry_run:
            print(f"Would update {product['title']}: {product['tags']}")
            success_count += 1
            continue
        
        try:
            response = requests.post(
                url,
                json={'query': update_mutation, 'variables': variables},
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'errors' in result:
                print(f"GraphQL errors for {product['title']}: {result['errors']}")
                error_count += 1
                continue
                
            user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
            if user_errors:
                print(f"User errors for {product['title']}: {user_errors}")
                error_count += 1
            else:
                success_count += 1
                print(f"Updated {product['title']}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {product['title']}: {e}")
            error_count += 1
    
    status = "Would have updated" if dry_run else "Updated"
    print(f"\n{status} {success_count} products successfully")
    if not dry_run and error_count:
        print(f"Failed to update {error_count} products")

# Main execution
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Update Shopify product tags')
    parser.add_argument('--apply', action='store_true', 
                      help='Actually apply the changes to Shopify (default is dry-run)')
    parser.add_argument('--limit', type=int,
                      help='Number of products to update (default is all products)')
    args = parser.parse_args()
    
    # Create or connect to database
    conn = create_database()
    
    # Get all products
    all_products = get_all_products_graphql()
    print(f"Total products found: {len(all_products)}")
    
    # Save to database
    save_products_to_db(all_products, conn)
    print("Products saved to shopify_products.db")
    
    # Clean up products with excluded tags
    clean_products_by_tags(conn)
    
    # Add Premier Gear tag to remaining products
    add_premier_gear_tag(conn)
    
    # Get products to update from SQLite (with limit if specified)
    products_to_update = get_products_to_update(conn, args.limit)
    
    # Update Shopify products (dry run by default)
    update_shopify_products(products_to_update, dry_run=not args.apply)
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    main()