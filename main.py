import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

shop_url = os.getenv('SHOPIFY_SHOP_URL')
access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

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

# Get and print all products
all_products = get_all_products_graphql()
print(f"Total products found: {len(all_products)}")
# Print first product's tags as an example
if all_products:
    print(f"Example - First product tags: {all_products[0]['tags']}")