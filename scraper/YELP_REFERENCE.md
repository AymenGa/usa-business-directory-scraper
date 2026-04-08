# Yelp Scraping Reference

Yelp-specific patterns and gotchas. For general scraping logic (bot protection, CAPTCHA, crash recovery, Chrome setup, dedup, delays), see [CLAUDE.md](../CLAUDE.md).

---

## Lessons Learned — Apply to Every Category (not just Home & Garden)

Mistakes made during Home & Garden that cost multiple reruns. Never repeat these.

### 1. Pre-audit Yelp categories before writing filter rules
Before writing any code, search Yelp for 5–10 cities in the target category. Open each result, record every category tag that appears. Build `ALLOWED_CATEGORIES` and `REJECT_CATEGORIES` from real observed data — not guesses. Skipping this caused 4+ reruns to fix categories we should have caught upfront.

### 2. Check city on the listing page before visiting the detail page
Yelp search returns businesses from the whole metro area, not just the target city. The listing page often shows partial address info. If the suburb name is visible (e.g. "Royal Oak" when searching Detroit) → skip immediately, no detail page visit. This alone eliminates ~50% of wasted page loads and CAPTCHA triggers.

### 3. Double geo-signal in the search URL
Current pattern returns too many suburbs:
```
find_desc=home decor store&find_loc=Detroit, MI
```
Better — add city name inside the query AND use zip code in find_loc:
```
find_desc=home decor store in Detroit&find_loc=Detroit, MI 48201
```
Forces Yelp to prioritize businesses actually inside the city boundary.

### 4. Rotate 2–3 search terms per city, in priority order
One broad search term pulls in art galleries, coffee shops, gift shops — anything loosely related. Use a priority list instead:
1. Most precise term first (e.g. `"furniture store"`)
2. If under quota → broader term (e.g. `"home decor"`)
3. If still under quota → alternate (e.g. `"garden center"`)

Each term pulls different, cleaner business types. Less filtering overhead.

### 5. Target 5 businesses per city, not 3
With 3 per city, one wrong-city rejection or CAPTCHA risks ending up with 1–2 rows and forcing pagination. With 5 as the target there's buffer — even after 2 rejections you hit 3 clean rows without paginating. Pagination is where most CAPTCHAs happen.

### 6. Filter by listing-page categories before visiting detail page
Yelp search results show category tags on the card. Run the hard-reject check right there. If the listing-page categories already contain a hard-reject keyword (e.g. `art galleries`, `coffee & tea`) → skip the detail page visit entirely. Only visit detail pages for businesses that pass the listing-page pre-filter.

### 7. One audit pass at the end — not iterative reruns
After the full run, run a single audit script that flags all suspicious rows. Review everything in one session, reject the bad ones, re-scrape all affected cities in a single batch. Home & Garden required 4 reruns because we reviewed and fixed one batch at a time. One pass = one rerun.

### 8. Primary-category rule for ambiguous categories
Some categories (e.g. `accessories`) are ambiguous — they can mean home accessories or fashion accessories. Rule: reject only if it is the **first** (primary) category AND no home-related category (`home decor`, `furniture`, `home & garden`) appears alongside it. Never hard-reject an ambiguous category in all positions — it removes legitimate businesses.

---

## URL Pattern

```
https://www.yelp.com/search?find_desc={query}&find_loc={city}, {state}
```
Pagination: `&start=10`, `&start=20`, etc. (10 results per page).

---

## Two-Phase Verification

**Most important Yelp pattern.** Never trust search page categories alone.

1. **Search page** gives candidates — names, profile URLs, approximate categories
2. **Detail page** (`/biz/...`) gives real data — actual categories, phone, website, address, rating, image

Businesses that look correct on search can turn out to be wrong category on detail page.

---

## Category Filtering

Each category defines its own:
- **ALLOWED_CATEGORIES** — Yelp category strings that belong to this milestone
- **REJECT_CATEGORIES** — categories to reject even if an allowed keyword is present
- **REJECT_NAME_KEYWORDS** — business names to skip (no page visit needed)

### Matching order:
1. Reject by name keywords (no page visit needed)
2. Quick reject by search-page categories if clearly wrong
3. Visit detail page → get real categories
4. Reject if any REJECT keyword appears in the category string
5. Accept if any ALLOWED keyword matches
6. No categories found → accept only if name contains relevant hints

### Partial match direction (critical):
- **REJECT**: check if `reject_keyword in category` — catches "auto accessories" when "auto" is in reject list
- **ALLOW**: bidirectional — `allowed in category` or `category in allowed`
- Wrong direction caused false positives (e.g., "accessories" matching "auto accessories")

---

## Required Fields

We require both **Phone** and **Website** for every business. If either is missing from the detail page, skip that business. Keeps data clean but some cities may have fewer rows.

---

## City Verification at Scrape Time (mandatory)

**Do this inside the scraper, not as a post-fix.** Fashion scraping skipped this — 195 wrong-city rows had to be fixed after the fact with a separate script. Never repeat this.

After extracting the address from the detail page, check that the target city name appears in it before accepting the result:

```python
CITY_ALIASES = {
    "new york city": "new york",
    "east honolulu":  "honolulu",
    "knik-fairview":  "wasilla",   # Yelp returns Wasilla-area results
    "enterprise":     "las vegas",
}

addr_lower  = address.lower()
city_lower  = city.lower()
check_city  = CITY_ALIASES.get(city_lower, city_lower)

if addr_lower and check_city not in addr_lower:
    log.info(f"REJECTED (wrong city): {addr}")
    continue   # keep searching, don't save this row
```

Define `CITY_ALIASES` at the **top of every Yelp scraper** (not inline inside a loop).

---

## Location Overrides for Yelp-Unrecognised Cities

Some cities in our 250-city list aren't known to Yelp. Without an override Yelp either returns 0 results or silently returns a nearby area.

```python
LOCATION_OVERRIDES = {
    "badger": "99705",   # Badger, AK — Yelp ignores "Badger, Alaska"; use zip code
}
```

Usage when building the search URL:

```python
city_lower  = city.lower()
search_loc  = LOCATION_OVERRIDES.get(city_lower, f"{city}, {state}")
location    = quote_plus(search_loc)
url         = f"https://www.yelp.com/search?find_desc={query}&find_loc={location}"
```

**0 rows for a problem city is the correct outcome** — better than wrong data. Log it clearly.

**Known problem cities (apply to every category's Yelp scraper):**

| City | State | Problem | Fix |
|------|-------|---------|-----|
| Knik-Fairview | AK | Yelp doesn't know it | alias → "wasilla" in city check |
| Badger | AK | Yelp doesn't know it | search with zip "99705" |
| East Honolulu | HI | Returns Honolulu results | alias → "honolulu" in city check |
| Enterprise | NV | Returns Las Vegas results | alias → "las vegas" in city check |
| New York City | NY | Yelp uses "New York" | alias → "new york" in city check |

Add to this table whenever a new problem city is discovered during any category scrape.

---

## Yelp-Specific Delays

- Page loads: 4-7 seconds random
- Between detail pages: 2-4 seconds
- Between cities: 3-6 seconds
- After CAPTCHA: 20 seconds
- Before driver restart: 5-10 seconds

---

## Progress & Checkpointing

- Progress JSON file — array of `"State|City"` keys for completed cities
- Save progress AND data together every 5 cities and at script end
- `KeyboardInterrupt` → save immediately
- Resume: load progress, skip done cities, load existing rows, continue
- Re-scrape failed cities: remove their keys from progress file and re-run

---

## Data Cleaning

Yelp-specific issues to handle:
- **Address prefix junk**: Yelp injects "Open until 9:00 PM" or "Closed" into address text. Strip with: `re.sub(r"(Open|Closed)\s+(until|now).*?(AM|PM)\s*", "", address, flags=re.I)`
- **Placeholder images**: Generic `yelp_og_image` when no photo exists — detect and set to empty
- **Numbered names**: Search results prefix "1. ", "2. " — strip with `re.sub(r"^\d+\.\s*", "")`
- **Rating format**: JSON-LD gives float, round to 2 decimals

---

## HTML Selectors (as of March 2026 — verify before reuse)

### Search Page
- Business links: `a[href^="/biz/"]`
- Rating: `[aria-label*="star"]`
- Cards: `[data-testid="serp-ia-card"]` with fallbacks
- Walk up DOM from link to find containing card

### Detail Page
- Phone: `a[href^="tel:"]`
- Website: `a[href*="biz_redir"]`
- Address: `<address>` tag or JSON-LD
- Rating: JSON-LD `aggregateRating.ratingValue`
- Image: `<meta property="og:image">`
- Categories: JSON-LD `additionalType`, or `a[href*="cflt="]`

---

## Category Audit File (mandatory for every Yelp scraper)

Every Yelp scraper must save a JSON audit file alongside the xlsx output:
`output/categories/{slug}_yelp_categories_audit.json`

**Why:** The grey zone problem — some categories (gift shops, plant stores, consignment, discount stores) are borderline. We can't just reject them all (less data) or accept them all (wrong rows). Instead:
- Accept them if they also have a clear home/garden category
- Save the real categories for every accepted row to the audit file
- Flag rows where the only categories are grey-zone keywords as `suspicious: true`
- After the run, review ~30-40 flagged rows manually, remove truly wrong ones, re-scrape those cities

**Audit record format:**
```json
{
  "state": "Alabama",
  "city": "Huntsville",
  "name": "HomeGoods",
  "categories": "Home Decor",
  "profile_url": "https://www.yelp.com/biz/...",
  "suspicious": false
}
```

**Suspicious flag:** mark `true` if accepted categories contain any of:
`gift`, `craft`, `fabric`, `art`, `discount`, `bargain`, `consign`, `thrift`, `florist`, `flower`, `book`, `hobby`, `plant`, `nursery`

Save audit JSON at every checkpoint (same frequency as xlsx), never separately.

---

## Closed Business Detection

Yelp shows a banner for closed businesses. Detect it in the detail page HTML before extracting anything:

```python
if "yelpers report this location has closed" in detail_html.lower():
    log.info(f"    REJECTED (closed): {biz['name']}")
    continue
```

---

## Empty Categories = Reject

If the detail page returns no categories at all, reject the business — we can't verify it belongs to the category:

```python
if not real_cats:
    log.info(f"    REJECTED (no categories on detail page): {biz['name']}")
    continue
```

Never fall back to name-hint guessing — that caused wrong businesses (JOANN, Hobby Lobby) to slip through.

---

## Rejected Businesses File (mandatory for every Yelp scraper)

Every Yelp scraper must append wrong-category businesses to a shared file:
`output/categories/yelp_rejected_all.json`

**Why:** After all 12 categories are scraped, a classifier reads this file, scores each business against all category lists, and routes each one to the right category. Data that looks wrong for one category may be exactly right for another.

**Save a rejected record only if ALL of these are true:**
1. Rejected because wrong Yelp categories (detail-page check only — not name/city/closed rejections)
2. Has phone + website + address + image (complete data, no placeholder images)
3. Passed city check (not wrong city) and closed check (not closed)

**Record format:**
```json
{
  "state": "Alabama",
  "city": "Montgomery",
  "name": "Montgomery Overstock",
  "categories": "Electronics, Furniture Stores, Mattresses",
  "phone": "(334) 213-0399",
  "website": "https://...",
  "address": "123 Main St Montgomery, AL",
  "rating": "3.5",
  "profile_url": "https://www.yelp.com/biz/...",
  "image_url": "https://...",
  "rejected_from": "home_and_garden",
  "reject_reason": "electronics"
}
```

**Implementation pattern:**
- `REJECTED_FILE = os.path.join(CATEGORIES_DIR, "yelp_rejected_all.json")` — same shared file every category
- `load_rejected()` / `save_rejected()` — load at start, save at every checkpoint and interrupt
- `is_home_garden_business()` (or equivalent) must return `(bool, reason)` so `reject_reason` is populated
- Append to `rejected_records` list at the detail-page category rejection point, after data is verified
- Save with `save_rejected()` at the same frequency as audit JSON (every 5 cities + interrupt + end)

---

## Post-Run Review: False Positives (mandatory for every Yelp scraper)

After the full run, review accepted businesses that may be wrong category using the audit JSON.

**Run:**
```
python scripts/review_audit.py --category home_and_garden
```

**What it does (interactive):**
- Shows each `suspicious: true` row from the audit JSON: name + real categories
- You type `k` (keep) or `w` (wrong) for each one
- For every row marked **wrong**:
  1. Pulls the full record from `{slug}_yelp_directory.xlsx`
  2. Appends it to `yelp_rejected_all.json` with `rejected_from: "{slug}"` and `reject_reason: "false positive"`
  3. Removes it from the xlsx
  4. Removes its `"State|City"` key from `{slug}_yelp_progress.json`
- Writes cities that need re-scraping to `{slug}_rescrape_cities.json`

**Then re-scrape the flagged cities:**
```
python scraper/{slug}/yelp.py
```
The scraper sees those cities as not done. It checks `existing_count` per city and only collects `needed = 3 - existing_count` new rows — so it replaces exactly the removed rows, nothing more.

**Why this approach (not just deleting):**
- No data is thrown away — wrong-category businesses go to `yelp_rejected_all.json` for the cross-category classifier
- Cities always end up with the correct number of rows (3)
- Same process works for all 12 categories

**Typical volume:** ~30–40 suspicious rows per category, ~10–15 actually wrong after review.

---

## Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Trusting search page categories | Always verify on detail page |
| Wrong partial match direction | Reject keywords as substrings of category, not reverse |
| Saving progress separately from data | Save both atomically |
| Errored cities marked done with no data | Use try/except per city + driver health checks |
| Headless mode | Yelp blocks it instantly |
| Not capturing new driver from fetch_page | Always: `html, driver = fetch_page(driver, url)` |
| Accepting businesses with no categories | Reject if detail page returns empty categories |
| Not detecting closed businesses | Check for "yelpers report this location has closed" in HTML |
| No audit trail for accepted categories | Always save audit JSON with real categories + suspicious flag |
| Discarding wrong-category businesses | Append complete rejected records to yelp_rejected_all.json for cross-category classifier |
| Deleting false positive rows without replacing | Move to yelp_rejected_all.json + remove city from progress + re-scrape to fill the gap |
