import csv
import random
import sys
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Path to your ChromeDriver
CHROMEDRIVER_PATH = (
    r""# FILL THIS!
)

# Accept URL from command line
URL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "https://www.dia.es/arroz-pastas-y-legumbres/pastas/c/L2044"
)


def setup_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scroll_until_all_loaded(driver, wait_time=1, max_tries=20):
    last_height = driver.execute_script("return document.body.scrollHeight")
    last_count = 0
    tries = 0

    while tries < max_tries:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time + random.uniform(0.2, 0.5))

        product_elements = driver.find_elements(
            By.CSS_SELECTOR, "li[data-test-id='product-card-list-item']"
        )
        current_count = len(product_elements)

        print(f"🔍 Loaded {current_count} products so far...")

        if current_count == last_count:
            print("✅ All products loaded.")
            break

        last_count = current_count
        tries += 1


def extract_product_data(product, index, driver):
    """Extracts product data. Returns dict and success flag."""
    try:
        driver.execute_script("arguments[0].scrollIntoView();", product)
        time.sleep(0.2)
        name = product.find_element(
            By.CSS_SELECTOR, "p.search-product-card__product-name"
        ).text.strip()
        price = product.find_element(
            By.CSS_SELECTOR, "p[data-test-id='search-product-card-unit-price']"
        ).text.strip()
        price_kg = product.find_element(
            By.CSS_SELECTOR, "p[data-test-id='search-product-card-kilo-price']"
        ).text.strip()

        print(f"[{index}] {name} | {price} | {price_kg}")
        return {"name": name, "price": price, "price_per_kg": price_kg}, True
    except Exception as e:
        print(f"[{index}] ❌ Failed to extract: {e}")
        return {"name": None, "price": None, "price_per_kg": None}, False


def scrape_data(driver):
    driver.get(URL)
    wait = WebDriverWait(driver, 15)
    wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "li[data-test-id='product-card-list-item']")
        )
    )

    scroll_until_all_loaded(driver)

    products = driver.find_elements(
        By.CSS_SELECTOR, "li[data-test-id='product-card-list-item']"
    )
    print(f"\n🔢 Total products found: {len(products)}\n")

    results = []
    failed_indexes = []

    for index, product in enumerate(products, start=1):
        data, success = extract_product_data(product, index, driver)
        results.append(data)
        if not success:
            failed_indexes.append(index - 1)  # store index for retry (0-based)

    # Retry failed ones
    if failed_indexes:
        print(f"\n🔁 Retrying {len(failed_indexes)} failed items...\n")
        time.sleep(1.5)

        products = driver.find_elements(
            By.CSS_SELECTOR, "li[data-test-id='product-card-list-item']"
        )
        for retry_index in failed_indexes:
            product = products[retry_index]
            data, success = extract_product_data(product, retry_index + 1, driver)
            results[retry_index] = data  # Overwrite

    # Summary
    success_count = sum(1 for r in results if r["name"])
    fail_count = len(results) - success_count
    print(f"\n✅ Scraping completed. {success_count} succeeded, {fail_count} failed.\n")

    return results


def save_to_csv(data, filename="products.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"💾 Data saved to {filename}")


def main():
    driver = setup_driver()
    try:
        print("🚀 Starting scraping...")
        data = scrape_data(driver)
        save_to_csv(data)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
