import re
import winreg
import time
import json
import random
import os
import hashlib
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
JSON_FILE = "scraped_data.json"
DYNAMIC_WAIT = True  # Wait for dynamic content

# Delete old data file
if os.path.exists(JSON_FILE):
    os.remove(JSON_FILE)
    print("🗑️ Old data file removed. Starting fresh.")

def get_default_browser_name():
    reg_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        return {"ChromeHTML": "Google Chrome", "MSEdgeHTM": "Microsoft Edge", "FirefoxURL": "Mozilla Firefox"}.get(prog_id, prog_id)
    except Exception:
        return "Google Chrome"

def get_driver(browser_choice):
    options = {
        "Google Chrome": (ChromeOptions, ["--headless=new", "--disable-gpu"]),
        "Mozilla Firefox": (FirefoxOptions, ["-headless"]),
        "Microsoft Edge": (EdgeOptions, ["--headless"])
    }.get(browser_choice, None)

    if not options:
        raise ValueError("Unsupported browser!")

    opt_class, args = options
    driver_options = opt_class()
    for arg in args:
        driver_options.add_argument(arg)
    driver_options.add_argument(f"user-agent={USER_AGENT}")

    if browser_choice == "Google Chrome":
        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=driver_options)
    elif browser_choice == "Mozilla Firefox":
        driver_options.set_preference("general.useragent.override", USER_AGENT)
        return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=driver_options)
    elif browser_choice == "Microsoft Edge":
        return webdriver.Edge(service=EdgeService(), options=driver_options)

def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl()

def extract_metadata(driver):
    return {
        "title": driver.title,
        "meta_tags": {
            meta.get_attribute('name') or meta.get_attribute('property'): meta.get_attribute('content')
            for meta in driver.find_elements(By.TAG_NAME, 'meta')
        },
        "headers": {
            f"h{i}": [h.text for h in driver.find_elements(By.TAG_NAME, f"h{i}")]
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
            WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
            if DYNAMIC_WAIT:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(1, 2))

            page_data = {
                "url": current_url,
                "metadata": extract_metadata(driver),
                "content": {
                    "text": driver.find_element(By.TAG_NAME, 'body').text.strip(),
                    "html": driver.page_source
                },
                "links": extract_links(driver, base_domain, current_url)
            }
            scraped_data[current_url] = page_data

            # Save progress
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(scraped_data, f, indent=4, ensure_ascii=False)
            print(f"💾 Saved {len(scraped_data)} pages")

            # Queue internal links
            internal_links = [link["url"] for link in page_data["links"] if link["is_internal"]]
            queue.extend(link for link in internal_links if link not in visited)
            time.sleep(random.uniform(1, 3))

        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️ Error scraping {current_url}: {str(e)}")

# Main execution
if __name__ == "__main__":
    start_urls = ["https://clouxiplexi.com/"]
    browser_choice = get_default_browser_name()
    print(f"🚀 Using {browser_choice} for scraping")
    
    driver = get_driver(browser_choice)
    scraped_data = {}

    try:
        for url in start_urls:
            scrape_site(url, driver, scraped_data)
    finally:
        driver.quit()
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Scraping complete! Saved {len(scraped_data)} pages to {JSON_FILE}")
