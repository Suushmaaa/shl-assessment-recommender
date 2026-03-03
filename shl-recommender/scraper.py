import requests
from bs4 import BeautifulSoup
import json
import os
import time

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


def get_data_path(filename):
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "data", filename)
def scrape_catalog():
    assessments = []
    
    # SHL catalog uses pagination with ?start= parameter
    start = 0
    page_size = 12  # SHL loads 12 per page
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    while True:
        url = f"{CATALOG_URL}?start={start}&type=1"  # type=1 = Individual Test Solutions
        print(f"Scraping: {url}")
        
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find assessment cards
        rows = soup.select("tr.product-catalogue-training-calendar__row")
        if not rows:
            # Try alternative selectors
            rows = soup.select("[data-course-id]") or soup.select(".product-catalogue__cell")
        
        if not rows:
            print(f"No more rows at start={start}")
            break
            
        for row in rows:
            try:
                # Extract name and URL
                link = row.select_one("a")
                if not link:
                    continue
                name = link.get_text(strip=True)
                href = link.get("href", "")
                full_url = BASE_URL + href if href.startswith("/") else href
                
                # Extract test types (the colored badges C P A B K etc.)
                type_badges = row.select(".product-catalogue__key")
                test_types = []
                type_map = {
                    "A": "Ability & Aptitude",
                    "B": "Biodata & Situational Judgement", 
                    "C": "Competencies",
                    "D": "Development & 360",
                    "E": "Assessment Exercises",
                    "K": "Knowledge & Skills",
                    "P": "Personality & Behavior",
                    "S": "Simulations"
                }
                for badge in type_badges:
                    code = badge.get_text(strip=True)
                    test_types.append(type_map.get(code, code))
                
                # Remote & Adaptive support
                remote = "Yes" if row.select_one(".remote-icon, [title*='remote'], [aria-label*='remote']") else "No"
                adaptive = "Yes" if row.select_one(".adaptive-icon, [title*='adaptive'], [aria-label*='adaptive']") else "No"
                
                assessments.append({
                    "name": name,
                    "url": full_url,
                    "test_type": test_types,
                    "remote_support": remote,
                    "adaptive_support": adaptive,
                    "description": "",
                    "duration": 0
                })
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        start += page_size
        time.sleep(0.5)  # Be polite
        
        # Safety: SHL has ~400 individual tests
        if start > 500:
            break
    
    print(f"\nTotal scraped: {len(assessments)}")
    return assessments


def scrape_detail(assessment):
    """Scrape individual assessment page for description and duration"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(assessment["url"], headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Description
        desc_el = soup.select_one(".product-catalogue-training-calendar__description, .field--name-body p")
        if desc_el:
            assessment["description"] = desc_el.get_text(strip=True)[:500]
        
        # Duration - look for patterns like "10 minutes", "untimed"
        text = soup.get_text()
        import re
        dur_match = re.search(r'(\d+)\s*(?:minutes?|mins?)', text, re.IGNORECASE)
        if dur_match:
            assessment["duration"] = int(dur_match.group(1))
            
    except Exception as e:
        print(f"Detail scrape failed for {assessment['name']}: {e}")
    
    return assessment


if __name__ == "__main__":
    print("Starting SHL catalog scrape...")
    assessments = scrape_catalog()
    
    # Enrich with detail pages (optional, adds time)
    print("\nEnriching with details...")
    for i, a in enumerate(assessments[:50]):  # Start with 50 for speed
        print(f"  {i+1}/{len(assessments)}: {a['name']}")
        assessments[i] = scrape_detail(a)
        time.sleep(0.3)
    
    with open(get_data_path("shl_assessments.json"), "w") as f:
        json.dump(assessments, f, indent=2)
    
    print(f"\n✅ Saved {len(assessments)} assessments to data/shl_assessments.json")
