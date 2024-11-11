import os
import sqlite3

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
        # Build the query with cursor if it exists
        query = """
        {
            products(first: 250 %s) {
                edges {
                    cursor
                    node {
                        id
                        title
                        tags
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """ % (', after: "%s"' % cursor if cursor else '')
        
        url = f"{shop_url}/admin/api/2023-04/graphql.json"
        
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json={'query': query}, headers=headers)
        
        if response.status_code == 200:
            json_response = response.json()
            
            # Check for GraphQL errors
            if 'errors' in json_response:
                print("GraphQL errors:", json_response['errors'])
                break
                
            data = json_response['data']['products']
            
            # Extract products from the response
            for edge in data['edges']:
                products.append(edge['node'])
                cursor = edge['cursor']
            
            has_next_page = data['pageInfo']['hasNextPage']
        else:
            print("Request failed with status code:", response.status_code)
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

# Main execution
def main():
    # Create or connect to database
    conn = create_database()
    
    # Get all products
    all_products = get_all_products_graphql()
    print(f"Total products found: {len(all_products)}")
    
    # Save to database
    save_products_to_db(all_products, conn)
    print("Products saved to shopify_products.db")
    
    # Verify data (optional)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    print(f"Products in database: {count}")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    main()