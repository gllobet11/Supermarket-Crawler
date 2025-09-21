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
    r"c:\Users\gerar\Desktop\random\web-scraping\Supermercats\drivers\chromedriver.exe"
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
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scroll_until_all_loaded(driver, wait_time=1, max_tries=20):
    last_count = 0
    tries = 0

    # Definir selectores múltiples para encontrar productos (basados en debug)
    product_selectors = [
        "div.search-product-card",
        ".search-product-card",
        "div[class*='search-product-card']",
        "li[data-test-id='product-card-list-item']",
        ".product-card-list-item",
        "[data-testid='product-card']",
        ".product-card",
        ".product-item",
    ]

    while tries < max_tries:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time + random.uniform(0.2, 0.5))

        # Intentar con todos los selectores
        product_elements = []
        for selector in product_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                product_elements = elements
                break

        current_count = len(product_elements)
        print(f"🔍 Cargados {current_count} productos hasta ahora...")

        if current_count == last_count:
            print("✅ Todos los productos cargados.")
            break

        last_count = current_count
        tries += 1


def extract_product_data(product, index, driver):
    """Extracts product data. Returns dict and success flag."""
    try:
        driver.execute_script("arguments[0].scrollIntoView();", product)
        time.sleep(0.2)

        # Múltiples selectores para el nombre del producto
        name_selectors = [
            "p.search-product-card__product-name",
            ".product-name",
            ".product-title",
            "h3",
            "h2",
            "[data-test*='product-name']",
            "[data-testid*='product-name']",
        ]

        name = None
        for selector in name_selectors:
            try:
                name_element = product.find_element(By.CSS_SELECTOR, selector)
                name = name_element.text.strip()
                if name:
                    break
            except Exception:
                continue

        # Múltiples selectores para el precio
        price_selectors = [
            "p[data-test-id='search-product-card-unit-price']",
            ".price",
            ".current-price",
            "[data-test*='price']",
            "[class*='price']",
            ".price-current",
        ]

        price = None
        for selector in price_selectors:
            try:
                price_element = product.find_element(By.CSS_SELECTOR, selector)
                price = price_element.text.strip()
                if price:
                    break
            except Exception:
                continue

        # Múltiples selectores para precio por kg
        price_kg_selectors = [
            "p[data-test-id='search-product-card-kilo-price']",
            ".price-per-unit",
            ".unit-price",
            "[data-test*='kilo-price']",
            "[data-test*='unit-price']",
            "[class*='unit-price']",
        ]

        price_kg = None
        for selector in price_kg_selectors:
            try:
                price_kg_element = product.find_element(By.CSS_SELECTOR, selector)
                price_kg = price_kg_element.text.strip()
                if price_kg:
                    break
            except Exception:
                continue

        print(f"[{index}] {name} | {price} | {price_kg}")
        return {"name": name, "price": price, "price_per_kg": price_kg}, True
    except Exception as e:
        print(f"[{index}] ❌ Failed to extract: {e}")
        return {"name": None, "price": None, "price_per_kg": None}, False


def debug_page_structure(driver):
    """Función para depurar la estructura de la página"""
    print("🔍 Depurando estructura de la página...")

    # Buscar cualquier elemento que contenga 'product' en su clase o id
    product_like_elements = driver.find_elements(
        By.XPATH, "//*[contains(@class, 'product') or contains(@id, 'product')]"
    )
    print(f"Elementos con 'product' en clase/id: {len(product_like_elements)}")

    for i, elem in enumerate(product_like_elements[:5]):  # Mostrar solo los primeros 5
        try:
            print(
                f"  [{i}] Tag: {elem.tag_name}, Class: {elem.get_attribute('class')}, ID: {elem.get_attribute('id')}"
            )
        except Exception:
            pass

    # Buscar elementos lista (li, ul)
    list_elements = driver.find_elements(By.TAG_NAME, "li")
    print(f"Elementos <li> encontrados: {len(list_elements)}")

    # Buscar elementos con data-test
    data_test_elements = driver.find_elements(
        By.XPATH, "//*[@data-test-id or @data-testid or @data-test]"
    )
    print(f"Elementos con data-test*: {len(data_test_elements)}")

    for i, elem in enumerate(data_test_elements[:10]):  # Mostrar solo los primeros 10
        try:
            data_test = (
                elem.get_attribute("data-test-id")
                or elem.get_attribute("data-testid")
                or elem.get_attribute("data-test")
            )
            print(f"  [{i}] Tag: {elem.tag_name}, data-test: {data_test}")
        except Exception:
            pass


def scrape_data(driver):
    print(f"🌐 Navegando a: {URL}")
    driver.get(URL)
    time.sleep(3)  # Esperar que cargue la página

    # Intentar aceptar cookies si aparecen
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(text(), 'Aceptar') or contains(text(), 'Accept')]",
                )
            )
        )
        cookie_button.click()
        print("✅ Cookies aceptadas")
        time.sleep(2)
    except Exception:
        print("ℹ️ No se encontró banner de cookies")

    # Ejecutar función de debug
    debug_page_structure(driver)

    # Buscar elementos de productos con múltiples selectores basados en el debug
    product_selectors = [
        "div.search-product-card",
        ".search-product-card",
        "div[class*='search-product-card']",
        "li[data-test-id='product-card-list-item']",
        ".product-card-list-item",
        "[data-testid='product-card']",
        ".product-card",
        ".product-item",
    ]

    products = []
    for selector in product_selectors:
        try:
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            products = driver.find_elements(By.CSS_SELECTOR, selector)
            if products:
                print(f"✅ Encontrados productos con selector: {selector}")
                break
        except Exception as e:
            print(f"❌ Selector {selector} falló: {e}")
            continue

    if not products:
        print("❌ No se encontraron productos con ningún selector")
        return []

    scroll_until_all_loaded(driver)

    # Buscar productos usando el mismo método de múltiples selectores
    final_products = []
    for selector in product_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            final_products = elements
            print(f"✅ Usando selector final: {selector}")
            break

    print(f"\n🔢 Total productos encontrados: {len(final_products)}\n")

    results = []
    failed_indexes = []

    for index, product in enumerate(final_products, start=1):
        data, success = extract_product_data(product, index, driver)
        results.append(data)
        if not success:
            failed_indexes.append(index - 1)  # store index for retry (0-based)

    # Retry failed ones
    if failed_indexes:
        print(f"\n🔁 Reintentando {len(failed_indexes)} elementos fallidos...\n")
        time.sleep(1.5)

        # Buscar productos nuevamente para el retry
        retry_products = []
        for selector in product_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                retry_products = elements
                break

        for retry_index in failed_indexes:
            if retry_index < len(retry_products):
                product = retry_products[retry_index]
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
