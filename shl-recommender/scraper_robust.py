import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

BASE = "https://www.shl.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TYPE_MAP = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations"
}


def get_data_path(filename):
    """Get the correct path to data files, relative to the script's location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "data", filename)


def scrape_page(start):
    url = f"{BASE}/solutions/products/product-catalog/?start={start}&type=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        assessments = []
        seen_hrefs = set()

        # Find the Individual Test Solutions table (Table 1 based on debug)
        tables = soup.find_all("table")
        target_table = None
        for table in tables:
            header = table.get_text()
            if "Individual Test Solutions" in header:
                target_table = table
                break

        if not target_table and tables:
            target_table = tables[-1]  # fallback to last table

        if not target_table:
            return []

        rows = target_table.find_all("tr")[1:]  # skip header row

        for row in rows:
            link = row.find("a")
            if not link:
                continue

            href = link.get("href", "")
            name = link.get_text(strip=True)

            if not href or not name or href in seen_hrefs:
                continue

            seen_hrefs.add(href)
            full_url = BASE + href if href.startswith("/") else href

            # Test types - look for catalogue__circle spans or single letter spans
            test_types = []
            cells = row.find_all("td")
            for cell in cells:
                for span in cell.find_all("span"):
                    txt = span.get_text(strip=True)
                    if txt in TYPE_MAP:
                        test_types.append(TYPE_MAP[txt])

            # Remote / Adaptive - look for -yes class circles
            remote = "No"
            adaptive = "No"
            circles = row.find_all("span", class_=lambda c: c and "-yes" in c)
            # Based on table header: col order = Name, Remote Testing, Adaptive/IRT, Test Type
            if len(cells) >= 3:
                remote_cell = cells[1] if len(cells) > 1 else None
                adaptive_cell = cells[2] if len(cells) > 2 else None

                if remote_cell:
                    rc = remote_cell.find("span", class_=lambda c: c and "-yes" in (c if isinstance(c, str) else " ".join(c)))
                    if rc:
                        remote = "Yes"

                if adaptive_cell:
                    ac = adaptive_cell.find("span", class_=lambda c: c and "-yes" in (c if isinstance(c, str) else " ".join(c)))
                    if ac:
                        adaptive = "Yes"

            assessments.append({
                "name": name,
                "url": full_url,
                "test_type": test_types if test_types else [],
                "remote_support": remote,
                "adaptive_support": adaptive,
                "description": f"{name} - SHL Assessment",
                "duration": 0
            })

        return assessments

    except Exception as e:
        print(f"  Error at start={start}: {e}")
        import traceback; traceback.print_exc()
        return []


def enrich_assessment(a):
    try:
        r = requests.get(a["url"], headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["nav", "footer", "header", "script", "style"]):
            tag.decompose()

        # Description
        paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
        if paras:
            a["description"] = " ".join(paras[:3])[:600]

        # Duration
        text = soup.get_text()
        m = re.search(r'(\d+)\s*(?:minutes?|mins?)', text, re.IGNORECASE)
        if m:
            a["duration"] = int(m.group(1))

        # Remote/Adaptive from detail page
        text_lower = text.lower()
        if "remote testing" in text_lower or "remotely" in text_lower:
            a["remote_support"] = "Yes"
        if "adaptive" in text_lower:
            a["adaptive_support"] = "Yes"

        # Enrich test types if missing
        if not a["test_type"]:
            for label in TYPE_MAP.values():
                if label.lower() in text_lower:
                    a["test_type"].append(label)

    except Exception as e:
        print(f"    Detail failed {a['name']}: {e}")
    return a


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    all_assessments = []
    seen_urls = set()

    print("=" * 50)
    print("Scraping SHL Individual Test Solutions...")
    print("=" * 50)

    consecutive_empty = 0

    for start in range(0, 600, 12):
        print(f"Page start={start}...", end=" ")
        results = scrape_page(start)

        new = [a for a in results if a["url"] not in seen_urls]
        for a in new:
            seen_urls.add(a["url"])
        all_assessments.extend(new)

        print(f"{len(new)} new | Total: {len(all_assessments)}")

        if len(new) == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print("2 empty pages in a row — stopping.")
                break
        else:
            consecutive_empty = 0

        time.sleep(0.6)

    print(f"\nTotal scraped: {len(all_assessments)}")

    # Enrich
    print(f"\nEnriching with detail pages...")
    for i, a in enumerate(all_assessments):
        print(f"  [{i+1}/{len(all_assessments)}] {a['name']}")
        all_assessments[i] = enrich_assessment(a)
        time.sleep(0.35)

    with open(get_data_path("shl_assessments.json"), "w", encoding="utf-8") as f:
        json.dump(all_assessments, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(all_assessments)} assessments to data/shl_assessments.json")

    # Quick stats
    with_types = sum(1 for a in all_assessments if a["test_type"])
    remote_yes = sum(1 for a in all_assessments if a["remote_support"] == "Yes")
    print(f"   With test types: {with_types}")
    print(f"   Remote testing:  {remote_yes}")
