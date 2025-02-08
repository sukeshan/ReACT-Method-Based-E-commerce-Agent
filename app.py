import streamlit as st

from src.Agent import productSearch

def get_search_products(query):
    sample_product = {
        "platform": "Amazon",
        "product_id": "1",
        "name": "Sample Product",
        "price": 10.0,
        "product_url": "http://example.com/product",
        "img_url": "https://via.placeholder.com/150",
        "ratings": 4.5,
        "delivery_info": "Delivered in 2 days",
        "size": 4,
    }
    products = [dict(sample_product, product_id=str(i), name=f"Product {i}") for i in range(1, 16)]
    return products

def get_price_comparison(results):
    return [
        [
            results[platform].get("min_price", None),
            results[platform].get("max_price", None),
            platform,
            results[platform].get("product", [{}])[0].get("name", "Unknown Product")
        ]
        for platform in results.keys()
    ]

@st.cache_resource
def get_database_session():
    return productSearch()

def main():
    st.set_page_config(page_title="Sh🍓ppin' app", layout="wide")
    st.title("Sh🍓ppin Search")
    query = st.text_input("Enter your search query", value="")
    engine = get_database_session()
    
    if query:
        results, tools, observation = engine.search(query)
        if tools['search_products']:
            aggregated_products = []
            for platform in results.keys():
                platform_products = results[platform]['products'][:25]
                aggregated_products.extend(platform_products)
            aggregated_products = sorted(aggregated_products, key=lambda x: x['price'])
            
            if not aggregated_products:
                st.info("Not found anything")
            else:
                st.subheader("Search Results")
                st.write(observation)
                for product in aggregated_products:
                    html = f"""
                    <a href="{product['product_url']}" target="_blank" style="text-decoration: none; color: inherit;">
                        <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; display: flex; align-items: center;">
                            <img src="{product['img_url']}" width="150" style="margin-right: 20px;">
                            <div>
                                <h4>{product['name']}</h4>
                                <p><strong>Price:</strong> ${product['price']}</p>
                                <p><strong>Platform:</strong> {product['platform']}</p>
                            </div>
                        </div>
                    </a>
                    """
                    st.markdown(html, unsafe_allow_html=True)
            
            first_platform = list(results.keys())[0]
            if tools['check_discount']:
                if results[first_platform]['discount_validity']:
                    st.sidebar.info("Coupon applicable on these products!")
                else:
                    st.sidebar.info("Coupon is not applicable on these products!")
        
        if tools['price_comparison']:
            st.subheader("Price Comparison")
            comparison_list = get_price_comparison(results)
            for comp in comparison_list:
                min_price, max_price, platform, prod_name = comp
                st.markdown(
                    f"""
                    <div style="text-align: center; font-size: 20px; margin: 20px 0;">
                        Product price starts from <b>${min_price}</b> up to <b>${max_price}</b> on <b>{platform}</b> for <b>{prod_name}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

if __name__ == "__main__":
    main()
