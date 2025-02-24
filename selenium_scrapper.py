import re
import time
import json
import random
import os
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
JSON_FILE = "scraped_data.json"
DYNAMIC_WAIT = True  # Wait for dynamic content

# Delete old data file
if os.path.exists(JSON_FILE):
    os.remove(JSON_FILE)
    print("🗑️ Old data file removed. Starting fresh.")

def get_driver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={USER_AGENT}")
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl()

def extract_metadata(driver):
    return {
        "title": driver.title,
        "meta_tags": {
            meta.get_attribute('name') or meta.get_attribute('property'): meta.get_attribute('content')
            for meta in driver.find_elements(By.TAG_NAME, 'meta')
            if meta.get_attribute('content') and (meta.get_attribute('name') or meta.get_attribute('property'))
        },
        "headers": {
            f"h{i}": [h.text for h in driver.find_elements(By.TAG_NAME, f"h{i}") if h.text.strip()]
            for i in range(1, 7)
        }
    }

def extract_links(driver, base_domain, current_url):
    links = []
    for a in driver.find_elements(By.TAG_NAME, 'a'):
        href = a.get_attribute('href')
        if href:
            full_url = urljoin(current_url, href)
            normalized = normalize_url(full_url)
            links.append({
                "url": normalized,
                "text": a.text.strip(),
                "is_internal": urlparse(normalized).netloc == base_domain
            })
    return links

def scrape_site(start_url, driver, scraped_data):
    base_domain = urlparse(start_url).netloc
    queue = [start_url]
    visited = set()

    while queue:
        current_url = queue.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        print(f"🌐 Scraping: {current_url}")
        try:
            driver.get(current_url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            if DYNAMIC_WAIT:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(1, 2))

            links = extract_links(driver, base_domain, current_url)
            metadata = extract_metadata(driver)

            scraped_data.append({
                "url": current_url,
                "metadata": metadata,
                "content_text": driver.find_element(By.TAG_NAME, 'body').text.strip(),
                "content_html": driver.page_source,
                "internal_links": [link["url"] for link in links if link["is_internal"]],
                "external_links": [link["url"] for link in links if not link["is_internal"]]
            })

            # Save progress
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(scraped_data, f, indent=4, ensure_ascii=False)
            print(f"💾 Saved {len(scraped_data)} pages")

            # Queue internal links
            queue.extend(link["url"] for link in links if link["is_internal"] and link["url"] not in visited)
            time.sleep(random.uniform(1, 3))

        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️ Error scraping {current_url}: {str(e)}")

# Main execution
if __name__ == "__main__":
    start_urls = ["https://clouxiplexi.com/"]
    driver = get_driver()
    scraped_data = []

    try:
        for url in start_urls:
            scrape_site(url, driver, scraped_data)
    finally:
        driver.quit()
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Scraping complete! Saved {len(scraped_data)} pages to {JSON_FILE}")
