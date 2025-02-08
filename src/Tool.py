import calendar
from copy import deepcopy
import concurrent.futures
from datetime import datetime, timedelta
import http.client
import json
import os
import pytz
import re
import random
import urllib.parse

from dotenv import load_dotenv

from src.template import product_output_format

load_dotenv()

def convert_day_to_date(target_day):
    
    ist = pytz.timezone('Asia/Kolkata')
    # Get today's date and current weekday index
    today = datetime.now(ist)
    today_index = today.weekday()  

    # Convert input day name to an index (case insensitive)
    target_day = target_day.capitalize()  # Ensure first letter is uppercase
    if target_day not in calendar.day_name:
        return "Invalid day name. Please enter a valid day (e.g., 'Friday')."

     # Get index of target day
    target_index = list(calendar.day_name).index(target_day) 

    # Calculate days until the next occurrence of the given day
    days_until = (target_index - today_index) % 7 
    if days_until == 0:  
        days_until = 7

    next_day_date = today + timedelta(days=days_until)
    
    return next_day_date


# AMAZON API CLASS
class Amazon:
    def __init__(self):
        # Initialize the HTTPS connection and headers for the Amazon API.
        self.conn = http.client.HTTPSConnection("real-time-amazon-data.p.rapidapi.com")
        self.headers = {
            'x-rapidapi-key': os.getenv("RAPID_API_KEY"),
            'x-rapidapi-host': "real-time-amazon-data.p.rapidapi.com"
        }
        # To be set during a search
        self.params = {}   
        # To be set by the Tools class          
        self.product_op_format = {"platform": "amazon","product_id" : "","name": "" ,"price": 0,"product_url": '',"img_url" : '',"ratings" : '',"delivery_info" : '', "size" : 4,} 
         # List to store fetched & formatted products 
        self.all_products = []      

    def search(self):

        """
        Search for products on Amazon using the provided parameters.
        """
        
        params = self.params 

        # Remove keys that are not meant to be part of the query string.
        excluded_keys = {"deals_and_discounts", "platform", "max_price", "deadline"}
        filtered_params = {k: v for k, v in params.items() if k not in excluded_keys and v}

        # Build query 
        query_string = "&".join(f"{key}={urllib.parse.quote_plus(str(value))}"
                                for key, value in filtered_params.items())

        page_number = 1
        all_products = []

        # Loop to fetch paginated results
        while True:
            paginated_query = f"{query_string}&page={page_number}"
            url = f"/search?{paginated_query}"
            self.conn.request("GET", url, headers=self.headers)
            response = self.conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))
            # Check if valid product data is returned.
            if "data" in data and "products" in data["data"]:
                products = data["data"]["products"]
                if products:
                    all_products.extend(products)
                    page_number += 1
                else:
                    break
            else:
                break

            # Limit to only the first page 
            if page_number == 2:
                break

        # Format the raw products using the provided product output format.
        formatted_products = []
        for prod in all_products:
            prod_data = deepcopy(self.product_op_format)
            prod_data['platform'] = "amazon"
            prod_data['product_id'] = prod.get('asin')
            prod_data['name'] = prod.get('product_title')
            price_str = prod.get("product_price")
            # Remove non-digit characters and convert to float if possible.
            prod_data['price'] = float(re.sub(r"[^\d.]", "", price_str).replace(",", "")) if price_str else None
            prod_data['product_url'] = prod.get('product_url')
            prod_data['img_url'] = prod.get('product_photo')
            prod_data['ratings'] = prod.get('product_star_rating')
            prod_data['delivery_info'] = prod.get('delivery')
            prod_data['size'] = prod.get('size', params.get('size', 4))
            formatted_products.append(prod_data)

        # Filter out products that may have missing essential fields.
        formatted_products = [p for p in formatted_products if "None" not in str(p)]
        self.all_products = formatted_products
        # Sort the product based on the price

        return formatted_products

        
    def discount_check(self):
        
        """
        Calculates the discounted price as 90% of the original price.
        By default for all coupoun having 10%
        """

        for product in self.all_products:
            if product.get('price') is not None:
                product['discount_price'] = round(product['price'] * 0.9, 2)
            else:
                product['discount_price'] = None
        return  True
    
    def shipping_time_estimate(self):
        
        """
        Estimate shipping time by adding a random number (1-5) of days to the current date.
        The products are then sorted by their estimated delivery date.
        """

        params = self.params
        target_day = params['deadline'] 
        deadline_time  = convert_day_to_date(target_day)

        for idx,product in enumerate(self.all_products):
            rand_days = random.randint(1, 11)
            
            est_delivery_date = (datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days = rand_days))
            check_est_delivery = (deadline_time - est_delivery_date).days

            if check_est_delivery >= 0 :
                est_delivery = datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days=rand_days)
                product['delivery_info'] = est_delivery.strftime('%Y-%m-%d %H:%M')
            else:
                del self.all_products[idx]

        # Sort products based on the parsed delivery date.

        return self.all_products

    def return_policy(self):
        """
        Randomly assign a return policy to each product.
        If no return policy is applicable (randomly determined), the product is removed.
        """

        filtered_products = []
        for product in self.all_products:
            rand_n = random.randint(1, 3)
            if rand_n == 1:
                product['return_policy'] = "2 days Return Policy"
                filtered_products.append(product)
            elif rand_n == 2:
                product['return_policy'] = "3 days Return Policy"
                filtered_products.append(product)
            else:
                # Skip the product to simulate lack of a return policy.
                continue
        self.all_products = filtered_products
        return self.all_products


# WALMART API CLASS
class Walmart:
    def __init__(self):

        self.conn = http.client.HTTPSConnection("walmart-data.p.rapidapi.com")
        self.headers = {
            'x-rapidapi-key':  os.getenv("RAPID_API_KEY"),
            'x-rapidapi-host': "walmart-data.p.rapidapi.com"
        }
        # To be set during a search
        self.params = {}   
        # To be set by the Tools class                    
        self.product_op_format = {"platform": "amazon","product_id" : "","name": "" ,"price": 0,"product_url": '',"img_url" : '',"ratings" : '',"delivery_info" : '', "size" : 4,}
         # List to store fetched & formatted products
        self.all_products = []      

    def search(self):
        
        """
        Search for products on Amazon using the provided parameters.
        """
        
        params = self.params
        # URL-encode the query string.
        all_products = []
        page = 1

        # Loop to fetch paginated results 
        while True:
            request_url = f"/search?q={self.params['query'].replace(" ","%20")}&page={page}"
            self.conn.request("GET", request_url, headers=self.headers)
            response = self.conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            if data.get('searchResult'):
                # Assuming searchResult[0] is the list of products.
                products = data['searchResult'][0]
                if products:
                    all_products.extend(products)
                    page += 1
                else:
                    break
            else:
                break

            # Limit to only the first page.
            if page == 2:
                break

        # Format the raw products using the provided product output format.
        formatted_products = []
        for prod in all_products:
            prod_data = deepcopy(self.product_op_format)
            prod_data['platform'] = "walmart"
            prod_data['product_id'] = ""  # Walmart products may not have a unique id.
            prod_data['name'] = prod.get("name")
            prod_data['price'] = prod.get("price")
            prod_data['product_url'] = prod.get('productLink')
            prod_data['img_url'] = prod.get('image')
            # Extract ratings if available.
            prod_data['ratings'] = prod.get('rating', {}).get('averageRating') if prod.get('rating') else None
            # Format delivery info using fulfillment badge details if available.
            if prod.get('fulfillmentBadgeGroups'):
                badge = prod['fulfillmentBadgeGroups'][0]
                prod_data['delivery_info'] = f"{badge.get('text', '')} {badge.get('slaText', '')}".strip()
            else:
                prod_data['delivery_info'] = None
            prod_data['size'] = prod.get('size', params.get('size', 4))
            formatted_products.append(prod_data)

        # Filter out products with missing essential fields.
        formatted_products = [p for p in formatted_products if "None" not in str(p)]

        # Sort the product based on the price
        sorted(formatted_products, key = lambda x : x['price'])
        self.all_products = formatted_products

        return formatted_products

    def discount_check(self):
        """
       Calculates the discounted price as 90% of the original price.
       By default for all coupoun having 10%
        """
        for product in self.all_products:
            if product.get('price') is not None:
                product['discount_price'] = round(product['price'] * 0.9, 2)
            else:
                product['discount_price'] = None
        return True

    def shipping_time_estimate(self):
        
        """
        Estimate shipping time by adding a random number (1-5) of days to the current date.
        Then sort the products by the estimated delivery date.
        """
        
        params = self.params
        target_day = params['deadline'] 
        deadline_time  = convert_day_to_date(target_day)
        
        for idx,product in enumerate(self.all_products):
            rand_days = random.randint(1, 12)
            
            check_est_delivery = (deadline_time - datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days=rand_days)).days

            if check_est_delivery >= 0:
                est_delivery = datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days=rand_days)
                product['delivery_info'] = est_delivery.strftime('%Y-%m-%d %H:%M')
            else:
                del self.all_products[idx]
                
        # Sort products based on the parsed delivery date.
        return self.all_products

    def return_policy(self):
        
        """
        Randomly assign a return policy to each product.
        If no return policy is applicable (as determined randomly), the product is removed.
        """
        
        filtered_products = []
        for product in self.all_products:
            rand_n = random.randint(1, 3)
            if rand_n == 1:
                product['return_policy'] = "2 days Return Policy"
                filtered_products.append(product)
            elif rand_n == 2:
                product['return_policy'] = "3 days Return Policy"
                filtered_products.append(product)
            else:
                continue  # Exclude the product if no return policy applies.
        self.all_products = filtered_products
        return self.all_products


# TOOLS HELPER CLASS
class Tools:
    def __init__(self):
        """
        Initialize with the search/filter parameters.
        Set up the common output format and select the target platforms.
        """
        self.product_output_format = product_output_format
        # Map platform names to their instantiated objects.
        self.platforms_map = {
            "amazon": Amazon(),
            "walmart": Walmart()
        }
          
    def search_platform(self, platform_obj, platform: str, params: dict):
        
        """
        Call the search method for the given platform and return its products.
        Also, set the platform object's parameters and output format.
        """
        
        print(f"Searching for '{params.get('query')}' on {platform}")
        platform_obj.params = params
        platform_obj.product_op_format = self.product_output_format
        return platform_obj.search()

    def search_products(self):

        """
        Search for products concurrently across all selected platforms.
        """

        
        if not self.params.get("query"):
            print("No query provided for product search.")
            return

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_platform = {
                executor.submit(self.search_platform, platform_obj, platform, self.params): platform
                for platform, platform_obj in self.platform_objects.items()
            }
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    products = future.result()
                    self.searched_products[platform]['products'] = products
                    print(f"{str(len(products))} Products fetched from the {platform}")
                except Exception as e:
                    print(f"Error while searching on {platform}: {e}")

    def check_discount_coupon_site_wise(self, platform_obj, platform: str, params: dict):
        """
        Apply discount processing on the given platform.
        """
        print(f"Applying discount for '{params.get('query')}' on {platform}")

        platform_obj.params = params
        return platform_obj.discount_check()

    def check_discount(self):

        """
        If discount deals are enabled, apply discount processing concurrently.
        """
        self.params['coupon_code'] = "TEST LOGIC"
        if self.params.get('coupon_code'):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_platform = {
                    executor.submit(self.check_discount_coupon_site_wise, platform_obj, platform, self.params): platform
                    for platform, platform_obj in self.platform_objects.items()
                }
                for future in concurrent.futures.as_completed(future_to_platform):
                    platform = future_to_platform[future]
                    try:
                        self.searched_products[platform]['discount_validity'] = future.result()
                    except Exception as e:
                        print(f"Error while applying discount on {platform}: {e}")

    def price_condition(self, platform: str):
        """
        Filter the products from the given platform to those at or below max_price.
        """
        max_price = self.params.get('max_price', float('inf'))
        return [product for product in self.searched_products[platform]['products']
                if product.get('price', 0) <= max_price]

    def price_filter(self):
        """
        Filter products by price concurrently across platforms.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            print("1")
            future_to_platform = {
                executor.submit(self.price_condition, platform): platform
                for platform in self.searched_products
            }
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    self.searched_products[platform]['products'] = future.result()

                except Exception as e:
                    print(f"Error filtering products by price on {platform}: {e}")

    def shipping_time_site_wise(self, platform_obj, platform: str, params: dict):
        """
        Calculate shipping time estimation for the given platform.
        """
        print(f"Calculating shipping time for '{params.get('query')}' on {platform}")
        platform_obj.params = self.params
        return platform_obj.shipping_time_estimate()

    def check_shipping_time(self):
        """
        Calculate shipping time concurrently for all platforms.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_platform = {
                executor.submit(self.shipping_time_site_wise, platform_obj, platform, self.params): platform
                for platform, platform_obj in self.platform_objects.items()
            }
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    self.searched_products[platform]['products'] = future.result()
                except Exception as e:
                    print(f"Error while calculating shipping time on {platform}: {e}")

    def return_policy_site_wise(self, platform_obj, platform: str, params: dict):
        
        """
        Apply return policy processing for the given platform.
        """

        print(f"Checking return policy for '{params.get('query')}' on {platform}")
        
        platform_obj.params =self.params

        return platform_obj.return_policy()

    def check_return_policy(self):
       
        """
        Apply return policy processing concurrently for all platforms.
        """
       
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_platform = {
                executor.submit(self.return_policy_site_wise, platform_obj, platform, self.params): platform
                for platform, platform_obj in self.platform_objects.items()
            }
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    self.searched_products[platform]['products'] = future.result()
                    self.searched_products[platform]['return_policy'] = True
                except Exception as e:
                    print(f"Error while checking return policy on {platform}: {e}")

    def price_comparison(self):

        """
        Search for products concurrently across all selected platforms.
        """
        
        if not self.params.get("query"):
            print("No query provided for product search.")
            return
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_platform = {
                executor.submit(self.search_platform, platform_obj, platform, self.params): platform
                for platform, platform_obj in self.platform_objects.items()
            }
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                
                try:
                    products = future.result()
                    self.searched_products[platform]['products'] = sorted(products, key = lambda x : x['price'])
                    
                    self.searched_products[platform]['min_price'] = self.searched_products[platform]['products'][0]['price'] # Min Price
                    self.searched_products[platform]['max_price'] = self.searched_products[platform]['products'][-1]['price'] # Max Price

                except Exception as e:
                    print(f"Error while searching on {platform}: {e}")

    def main(self, params, tools):
        
        """
        Main execution flow:
         1. Search products across platforms.
         2. Apply discount if enabled.
         3. Estimate shipping times .
         4. Filter products by max price.
         5. Apply return policy processing if a deadline is provided and remove products doesn't provide return policy.
         6. Return the consolidated results.
        """
        
        self.params = params
        print("="*30)
        print('Tools Need to call :' , [k for k,v in tools.items() if v])
        print("Parameters : ", self.params)
        print("="*30)
        # Determine which platforms to search. If 'all' is specified, search both.
        selected_platforms = ["amazon", "walmart"] if self.params['platform'] == 'all' else [self.params['platform']]

        self.platform_objects = {platform: self.platforms_map[platform] for platform in selected_platforms}
  
        # Initialize a dictionary to hold search results from each platform.
        self.searched_products = {platform: {} for platform in self.platform_objects}
        
        if tools.get("search_products", None):
            print("Tool : Searching Product is called ")
            self.search_products() #  DONE
        
        if tools.get('check_discount', None):
            print("Tool : Check Discount is callled")
            self.check_discount() # DONE
        
        if tools.get('price_filter', None) :
            print("Tool : Price Filter is called")
            self.price_filter() # DONE

        if tools.get('check_shipping_time', None):
            print("Tool : Check Shipping Time is called")
            self.check_shipping_time() # DONE
        
        if tools.get('check_return_policy', None):
            print("Tool : Check Shipping Time is called")
            self.check_return_policy() # DONE
        
        if tools.get("price_comparison", None):
            print("Tool : Price Comparison is called ")
            self.price_comparison() # DONE
            
        return self.searched_products
