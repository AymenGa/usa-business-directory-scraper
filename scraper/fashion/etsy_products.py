"""
Fashion / Accessories — Etsy product scraper (marketplace data).
Scrapes product listings from Etsy /c/ category pages using undetected-chromedriver.
Uses /c/ URLs with locationQuery for real geographic filtering per city.
Paginates via &page=N for better product coverage and deduplication.
Prioritizes ad listings (they include shop names); falls back to non-ad + individual page fetch.

Run:
  python scraper/fashion/etsy_products.py --test   # 1 state, 25 rows
  python scraper/fashion/etsy_products.py          # all 50 states
"""

import argparse
import json
import os
import time
import random
import logging
from datetime import date
from urllib.parse import quote

import openpyxl
from bs4 import BeautifulSoup

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES_DIR = os.path.join(BASE_DIR, "output", "categories")
METADATA_FILE  = os.path.join(CATEGORIES_DIR, "metadata.json")

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── State abbreviations ──────────────────────────────────────────────────────
STATE_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY',
}

# ── States and cities ────────────────────────────────────────────────────────
STATES = {
    'Alabama': ['Huntsville', 'Birmingham', 'Montgomery', 'Mobile', 'Tuscaloosa'],
    'Alaska': ['Anchorage', 'Fairbanks', 'Juneau', 'Knik-Fairview', 'Badger'],
    'Arizona': ['Phoenix', 'Tucson', 'Mesa', 'Chandler', 'Gilbert'],
    'Arkansas': ['Little Rock', 'Fayetteville', 'Fort Smith', 'Springdale', 'Jonesboro'],
    'California': ['Los Angeles', 'San Diego', 'San Jose', 'San Francisco', 'Fresno'],
    'Colorado': ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins', 'Lakewood'],
    'Connecticut': ['Bridgeport', 'Stamford', 'New Haven', 'Hartford', 'Waterbury'],
    'Delaware': ['Wilmington', 'Dover', 'Newark', 'Middletown', 'Smyrna'],
    'Florida': ['Jacksonville', 'Miami', 'Tampa', 'Orlando', 'St. Petersburg'],
    'Georgia': ['Atlanta', 'Columbus', 'Augusta', 'Macon', 'Savannah'],
    'Hawaii': ['Honolulu', 'East Honolulu', 'Pearl City', 'Hilo', 'Kailua-Kona'],
    'Idaho': ['Boise', 'Meridian', 'Nampa', 'Idaho Falls', 'Caldwell'],
    'Illinois': ['Chicago', 'Aurora', 'Naperville', 'Joliet', 'Rockford'],
    'Indiana': ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend', 'Carmel'],
    'Iowa': ['Des Moines', 'Cedar Rapids', 'Davenport', 'Sioux City', 'Iowa City'],
    'Kansas': ['Wichita', 'Overland Park', 'Kansas City', 'Olathe', 'Topeka'],
    'Kentucky': ['Louisville', 'Lexington', 'Bowling Green', 'Owensboro', 'Covington'],
    'Louisiana': ['New Orleans', 'Baton Rouge', 'Shreveport', 'Lafayette', 'Lake Charles'],
    'Maine': ['Portland', 'Lewiston', 'Bangor', 'South Portland', 'Auburn'],
    'Maryland': ['Baltimore', 'Frederick', 'Gaithersburg', 'Rockville', 'Bowie'],
    'Massachusetts': ['Boston', 'Worcester', 'Springfield', 'Cambridge', 'Lowell'],
    'Michigan': ['Detroit', 'Grand Rapids', 'Warren', 'Sterling Heights', 'Ann Arbor'],
    'Minnesota': ['Minneapolis', 'St. Paul', 'Rochester', 'Bloomington', 'Duluth'],
    'Mississippi': ['Jackson', 'Gulfport', 'Southaven', 'Hattiesburg', 'Biloxi'],
    'Missouri': ['Kansas City', 'St. Louis', 'Springfield', 'Columbia', 'Independence'],
    'Montana': ['Billings', 'Missoula', 'Great Falls', 'Bozeman', 'Butte'],
    'Nebraska': ['Omaha', 'Lincoln', 'Bellevue', 'Grand Island', 'Kearney'],
    'Nevada': ['Las Vegas', 'Henderson', 'North Las Vegas', 'Reno', 'Enterprise'],
    'New Hampshire': ['Manchester', 'Nashua', 'Concord', 'Derry', 'Dover'],
    'New Jersey': ['Newark', 'Jersey City', 'Paterson', 'Elizabeth', 'Lakewood'],
    'New Mexico': ['Albuquerque', 'Las Cruces', 'Rio Rancho', 'Santa Fe', 'Roswell'],
    'New York': ['New York City', 'Buffalo', 'Yonkers', 'Rochester', 'Syracuse'],
    'North Carolina': ['Charlotte', 'Raleigh', 'Greensboro', 'Durham', 'Winston-Salem'],
    'North Dakota': ['Fargo', 'Bismarck', 'Grand Forks', 'Minot', 'West Fargo'],
    'Ohio': ['Columbus', 'Cleveland', 'Cincinnati', 'Toledo', 'Akron'],
    'Oklahoma': ['Oklahoma City', 'Tulsa', 'Norman', 'Broken Arrow', 'Lawton'],
    'Oregon': ['Portland', 'Eugene', 'Salem', 'Gresham', 'Hillsboro'],
    'Pennsylvania': ['Philadelphia', 'Pittsburgh', 'Allentown', 'Reading', 'Erie'],
    'Rhode Island': ['Providence', 'Cranston', 'Warwick', 'Pawtucket', 'East Providence'],
    'South Carolina': ['Charleston', 'Columbia', 'North Charleston', 'Mount Pleasant', 'Rock Hill'],
    'South Dakota': ['Sioux Falls', 'Rapid City', 'Aberdeen', 'Brookings', 'Watertown'],
    'Tennessee': ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Clarksville'],
    'Texas': ['Houston', 'San Antonio', 'Dallas', 'Fort Worth', 'Austin'],
    'Utah': ['Salt Lake City', 'West Valley City', 'West Jordan', 'Provo', 'St. George'],
    'Vermont': ['Burlington', 'South Burlington', 'Colchester', 'Rutland', 'Essex Junction'],
    'Virginia': ['Virginia Beach', 'Chesapeake', 'Arlington', 'Norfolk', 'Richmond'],
    'Washington': ['Seattle', 'Spokane', 'Tacoma', 'Vancouver', 'Bellevue'],
    'West Virginia': ['Charleston', 'Huntington', 'Morgantown', 'Parkersburg', 'Wheeling'],
    'Wisconsin': ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine'],
    'Wyoming': ['Cheyenne', 'Casper', 'Gillette', 'Laramie', 'Rock Springs'],
}

# ── Pagination config ────────────────────────────────────────────────────────
MAX_PAGES = 5  # max pages to check per sub-category before giving up

# ── Fashion / Accessories config ─────────────────────────────────────────────
CATEGORY_NAME = "Fashion / Accessories"
CATEGORY_SLUG = "fashion_accessories"
SOURCE        = "www.etsy.com"
ITEMS_PER_CITY = 5  # pick 5 out of 6 subcategories per city (rotate)

SUB_CATEGORIES = [
    ("womens_dresses",  "/c/clothing/womens-clothing/dresses"),
    ("womens_shoes",    "/c/shoes/womens-shoes"),
    ("handbags",        "/c/bags-and-purses/handbags"),
    ("scarves_wraps",   "/c/accessories/scarves-and-wraps"),
    ("mens_jackets",    "/c/clothing/mens-clothing/jackets-and-coats"),
    ("jewelry",         "/c/jewelry"),
]

# ── Browser helpers ──────────────────────────────────────────────────────────
def create_driver():
    """Create an undetected Chrome driver."""
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options, headless=False)
    driver.set_page_load_timeout(30)
    return driver


def fetch_page(driver, url, retries=3):
    """Navigate to URL and return page source. Retries on captcha/failure."""
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            wait = random.uniform(6, 9)
            time.sleep(wait)

            if "captcha" in driver.page_source[:3000].lower():
                log.warning(f"  CAPTCHA detected (attempt {attempt}/{retries}), waiting longer...")
                time.sleep(15)
                if "captcha" in driver.page_source[:3000].lower():
                    if attempt < retries:
                        log.warning("  Still captcha, restarting driver...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        time.sleep(5)
                        driver = create_driver()
                        continue
                    else:
                        return None, driver

            return driver.page_source, driver

        except Exception as e:
            log.error(f"  Page load error (attempt {attempt}): {e}")
            if attempt < retries:
                time.sleep(5)
            else:
                return None, driver

    return None, driver


# ── Extraction ───────────────────────────────────────────────────────────────
def _extract_card(card):
    """Extract fields from a single listing card. Returns dict or None."""
    # Product URL — skip cards without one (UI widgets)
    link = card.find("a", class_="listing-link")
    if not link:
        link = card.find("a", href=lambda h: h and "/listing/" in h)
    if not link or not link.get("href"):
        return None
    product_url = link["href"].split("?")[0]

    # Title (h3 on /c/ pages, h2 as fallback)
    title = ""
    for tag in ["h3", "h2"]:
        el = card.find(tag)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

    # Price
    price_el = card.find("span", class_="currency-value")
    price = price_el.get_text(strip=True) if price_el else ""

    if not title or not price:
        return None

    # Shop name (only on ad cards)
    shop = ""
    for span in card.find_all("span"):
        t = span.get_text(strip=True)
        if t.startswith("From shop "):
            shop = t.replace("From shop ", "")
            break

    # Rating
    rating_input = card.find("input", {"name": "rating"})
    rating_raw = rating_input.get("value") if rating_input else ""
    try:
        rating = str(round(float(rating_raw), 2))
    except (ValueError, TypeError):
        rating = ""

    # Image
    img = card.find("img")
    img_src = (img.get("src", "") or img.get("data-src", "")) if img else ""
    img_full = img_src.replace("il_300x300", "il_fullxfull").replace("il_340x270", "il_fullxfull")

    is_ad = "ad by" in card.get_text().lower()

    return {
        "store_name": shop,
        "description": title,
        "price": price,
        "star_rating": rating,
        "product_url": product_url,
        "photo_url": img_full,
        "is_ad": is_ad,
    }


def extract_listings(html):
    """Extract all listings from an Etsy /c/ page. Returns (ads, non_ads)."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.find_all("div", attrs={"data-listing-id": True})

    ads, non_ads = [], []
    for card in cards:
        item = _extract_card(card)
        if not item:
            continue
        is_ad = item.pop("is_ad")
        if is_ad:
            ads.append(item)
        else:
            non_ads.append(item)

    return ads, non_ads


def fetch_shop_name_from_listing(driver, listing_url):
    """Visit an individual listing page to get the shop name."""
    try:
        html, driver = fetch_page(driver, listing_url)
        if not html:
            return "", driver

        soup = BeautifulSoup(html, "lxml")

        # Try: link to shop page
        shop_link = soup.find("a", href=lambda h: h and "/shop/" in h)
        if shop_link:
            href = shop_link.get("href", "")
            parts = href.split("/shop/")
            if len(parts) > 1:
                return parts[1].split("?")[0].split("/")[0], driver

        # Try: JSON-LD brand name
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                brand = data.get("brand", {}).get("name", "")
                if brand:
                    return brand, driver
            except (json.JSONDecodeError, AttributeError):
                pass

        return "", driver
    except Exception as e:
        log.error(f"  Error fetching shop name: {e}")
        return "", driver


# ── Scraping logic ───────────────────────────────────────────────────────────
def scrape_city(driver, state, city, sub_categories, seen_urls, items_per_city=5, city_index=0):
    """Scrape products for one city (items_per_city items, rotating subcategories).

    When len(sub_categories) > items_per_city, rotates which subcategory is
    skipped based on city_index so all subcategories get even coverage.

    Uses /c/ URLs with locationQuery for real geographic filtering.
    Paginates through pages (&page=N) to find unique products.
    seen_urls is shared globally to avoid duplicates across all cities.
    """
    abbrev = STATE_ABBREV.get(state, state)
    location = quote(f"{city}, {abbrev}")

    city_items = []

    # Rotate: if more subcategories than items_per_city, skip one per city
    if len(sub_categories) > items_per_city:
        skip_idx = city_index % len(sub_categories)
        active_subs = [sc for i, sc in enumerate(sub_categories) if i != skip_idx]
        log.info(f"  Rotation: skipping '{sub_categories[skip_idx][0]}' for {city}")
    else:
        active_subs = list(sub_categories)

    for label, path in active_subs:
        picked = None

        for page_num in range(1, MAX_PAGES + 1):
            page_param = f"&page={page_num}" if page_num > 1 else ""
            url = f"https://www.etsy.com{path}?locationQuery={location}&ship_to=US{page_param}"

            if page_num > 1:
                log.info(f"  [{city}] {label}: page {page_num} (looking for unique product)")

            html, driver = fetch_page(driver, url)
            if not html:
                log.warning(f"  [{state}/{city}] {label}: page {page_num} load failed")
                break

            ads, non_ads = extract_listings(html)

            # No listings at all → stop paginating this sub-category
            if not ads and not non_ads:
                log.info(f"  [{city}] {label}: no listings on page {page_num}, stopping pagination")
                break

            # Priority 1: ad listings (have shop name)
            for ad in ads:
                if ad["product_url"] not in seen_urls:
                    picked = ad
                    seen_urls.add(ad["product_url"])
                    break

            # Priority 2: non-ad listings (need to fetch shop name)
            if not picked:
                for item in non_ads:
                    if item["product_url"] not in seen_urls:
                        log.info(f"  [{city}] {label}: no unique ads, fetching shop name from listing page...")
                        shop_name, driver = fetch_shop_name_from_listing(driver, item["product_url"])
                        item["store_name"] = shop_name
                        picked = item
                        seen_urls.add(item["product_url"])
                        break

            if picked:
                break

            # Delay between pagination requests
            time.sleep(random.uniform(1.5, 3.0))

        if picked:
            city_items.append(picked)
            log.info(f"  [{city}] {label}: {picked['store_name']:20s} | ${picked['price']:>8s} | {picked['star_rating']}")
        else:
            log.warning(f"  [{city}] {label}: no unique products found after {MAX_PAGES} pages")

        # Delay between sub-category requests
        time.sleep(random.uniform(1.5, 3.0))

    return city_items, driver


# ── Save functions ───────────────────────────────────────────────────────────
def save_category_xlsx(rows):
    """Save scraped data to output/categories/fashion_accessories_marketplace.xlsx."""
    os.makedirs(CATEGORIES_DIR, exist_ok=True)
    filepath = os.path.join(CATEGORIES_DIR, f"{CATEGORY_SLUG}_marketplace.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    headers = ["State", "City", "Store Name", "Item Description", "Price",
               "Star Rating", "Product URL", "Product Photo URL"]
    ws.append(headers)

    for row in rows:
        ws.append([
            row["state"],
            row["city"],
            row["store_name"],
            row["description"],
            row["price"],
            row["star_rating"],
            row["product_url"],
            row["photo_url"],
        ])

    wb.save(filepath)
    log.info(f"Saved {len(rows)} rows to {filepath}")
    return filepath


def update_metadata(category_name, count, source):
    """Update metadata.json with this category's info."""
    meta = {}
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)

    meta[category_name] = {
        "date_extracted": str(date.today()),
        "source": source,
        "count": count,
    }

    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    log.info(f"Updated metadata.json: {category_name} = {count} rows")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fashion / Accessories — Etsy product scraper")
    parser.add_argument("--test", action="store_true", help="Test mode: 1 state only (25 rows)")
    args = parser.parse_args()

    # Select states to scrape
    if args.test:
        states_to_scrape = {"Alabama": STATES["Alabama"]}
        log.info(f"TEST MODE: scraping 1 state (Alabama), expecting ~25 rows")
    else:
        states_to_scrape = STATES
        log.info(f"FULL MODE: scraping {len(STATES)} states, expecting ~{len(STATES) * 5 * 5} rows")

    log.info(f"Category: {CATEGORY_NAME}")
    log.info(f"Sub-categories: {[sc[0] for sc in SUB_CATEGORIES]}")

    # Create browser
    driver = create_driver()
    all_rows = []
    skipped_cities = []
    seen_urls = set()  # global dedup across all cities
    global_city_idx = 0  # for rotation across all cities

    try:
        for state_idx, (state, cities) in enumerate(states_to_scrape.items(), 1):
            log.info(f"\n{'='*60}")
            log.info(f"State {state_idx}/{len(states_to_scrape)}: {state}")
            log.info(f"{'='*60}")

            for city_idx, city in enumerate(cities, 1):
                log.info(f"\n--- {city}, {state} ({city_idx}/5) ---")

                city_items, driver = scrape_city(
                    driver, state, city, SUB_CATEGORIES, seen_urls,
                    items_per_city=ITEMS_PER_CITY, city_index=global_city_idx,
                )
                global_city_idx += 1

                for item in city_items:
                    all_rows.append({
                        "state": state,
                        "city": city,
                        **item,
                    })

                if len(city_items) < ITEMS_PER_CITY:
                    skipped_cities.append(f"{city}, {state} ({len(city_items)}/{ITEMS_PER_CITY})")

                log.info(f"  -> {len(city_items)}/{ITEMS_PER_CITY} products for {city}")

    except KeyboardInterrupt:
        log.warning("\nInterrupted by user. Saving collected data...")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Save results
    if all_rows:
        save_category_xlsx(all_rows)
        update_metadata(CATEGORY_NAME, len(all_rows), SOURCE)

        log.info(f"\n{'='*60}")
        log.info(f"DONE: {len(all_rows)} rows collected")
        log.info(f"States: {len(set(r['state'] for r in all_rows))}")
        log.info(f"Cities: {len(set((r['state'], r['city']) for r in all_rows))}")
        if skipped_cities:
            log.info(f"Cities with < 5 products:")
            for sc in skipped_cities:
                log.info(f"  {sc}")
    else:
        log.error("No data collected!")


if __name__ == "__main__":
    main()
