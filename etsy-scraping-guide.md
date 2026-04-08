# Etsy Scraping Reference

Etsy-specific patterns and gotchas. For general scraping logic (bot protection, CAPTCHA, crash recovery, Chrome setup, dedup, delays), see [CLAUDE.md](CLAUDE.md).

---

## URL Pattern — Use `/c/` Pages, Not Search

- Etsy `/c/` (category) pages support `locationQuery` for **real geo-filtering** per city
- Search pages (`/search?q=`) have weaker geo-filtering and more overlap between cities
- URL format: `https://www.etsy.com/c/{category-path}?locationQuery={city,STATE_ABBREV}&ship_to=US`
- Use state abbreviations (AL, CA, NY) not full names
- URL-encode the location: `quote(f"{city}, {abbrev}")`

---

## Two Scrapers Per Category

Each Etsy category needs **two separate scrapers** run in order:

### 1. etsy_products.py (Marketplace data) — run first
- Scrapes product listings from `/c/` category pages
- Outputs `{slug}_marketplace.xlsx`

### 2. etsy_shops.py (Directory data) — run second
- Reads marketplace file to get unique shop names
- Visits each shop's profile page (`etsy.com/shop/{name}`) to extract location, rating, icon
- Etsy shops typically don't have phone or website — store as `"N/A"`

---

## Sub-Category Rotation

- One `/c/` page returns only one product type — need multiple sub-categories per category
- Pick a subset per city, rotate which is skipped using `city_index % len(sub_categories)`
- Research the Etsy `/c/` structure fresh for each new category — use `firecrawl_map` on the category page
- Once discovered, document paths below so they never need to be looked up again

---

## Known Sub-Category Paths Per Category

### Fashion / Accessories
```python
SUB_CATEGORIES = [
    ("womens_dresses",  "/c/clothing/womens-clothing/dresses"),
    ("womens_shoes",    "/c/shoes/womens-shoes"),
    ("handbags",        "/c/bags-and-purses/handbags"),
    ("scarves_wraps",   "/c/accessories/scarves-and-wraps"),
    ("mens_jackets",    "/c/clothing/mens-clothing/jackets-and-coats"),
    ("jewelry",         "/c/jewelry"),
]
```

### Electronics / Gadgets
```python
SUB_CATEGORIES = [
    ("gadgets",      "/c/electronics-and-accessories/gadgets"),
    ("headphones",   "/c/electronics-and-accessories/audio/headphones-and-stands/headphones"),
    ("cameras",      "/c/electronics-and-accessories/cameras-and-equipment/cameras"),
    ("audio",        "/c/electronics-and-accessories/audio"),  # keyboards path returned 0 geo-filtered results
    ("phone_cases",  "/c/electronics-and-accessories/electronics-cases/phone-cases"),
    ("video_games",  "/c/electronics-and-accessories/video-games"),
]
```

### Home and Garden
```python
SUB_CATEGORIES = [
    ("outdoor_garden",  "/c/home-and-living/outdoor-and-garden"),
    ("furniture",       "/c/home-and-living/furniture"),
    ("home_decor",      "/c/home-and-living/home-decor"),
    ("kitchen_dining",  "/c/home-and-living/kitchen-and-dining"),
    ("lighting",        "/c/home-and-living/lighting"),
    ("storage",         "/c/home-and-living/storage-and-organization"),
]
```

---

## Shop Name Extraction (Products Scraper)

- **Ad listings** include shop name in the card HTML (`"From shop {name}"`)
- **Non-ad listings do NOT** — shop name is only on the individual product page
- Strategy: prioritize ad listings first (free to extract)
- Only visit product page for non-ads if no unique ads found
- On product page: find shop name via `/shop/` link in href, or JSON-LD `brand.name`

---

## Etsy-Specific Delays

- Product page loads: 6-9 seconds random
- Shop profile pages: 5-8 seconds
- Between sub-categories / pagination: 1.5-3 seconds
- After CAPTCHA: 15 seconds

---

## Pagination

- Use `&page=N` parameter on `/c/` URLs
- Set MAX_PAGES limit (used 5 for Fashion)
- If a page returns 0 listings, stop paginating that sub-category
- Paginate only when dedup exhausts page 1

## Fallback Sub-Category Logic

When a sub-category returns 0 listings for a city, automatically try the rotated-out (skipped) sub-category as a fallback before giving up. This maximises yield per city without changing the rotation pattern.

- Split subs into `active_subs` (5) + `fallbacks` (the 1 skipped sub)
- Extract `_try_subcategory(driver, city, state, label, path, location, seen_urls)` as a helper
- In the main loop: if `_try_subcategory` returns `None` → pop next fallback and try it
- `fallback_idx` pointer ensures each fallback is only tried once per city
- `seen_urls` dedup applies to both primary and fallback attempts

---

## Deduplication (Etsy-specific)

- Clean product URL by stripping query params: `link["href"].split("?")[0]`
- Etsy shows same popular products in nearby cities — global dedup is critical

---

## Card Extraction Selectors (as of March 2026 — verify before reuse)

| Field | Selector |
|-------|----------|
| Card container | `div[data-listing-id]` |
| Product link | `a.listing-link` or `a[href*="/listing/"]` |
| Title | `h3` first, `h2` fallback |
| Price | `span.currency-value` |
| Shop name (ads only) | `span` containing text starting with `"From shop "` |
| Rating | `input[name="rating"]` → `.value` attribute |
| Image | `img` → `src` or `data-src`, replace `il_300x300`/`il_340x270` with `il_fullxfull` |
| Is ad? | Card text contains `"ad by"` (lowercase) |

**Filter rule:** Skip cards missing both title AND price.

---

## Shop Profile Selectors (as of March 2026 — verify before reuse)

- **Location**: `<p class="sb-shop-location">`
- **Rating**: JSON-LD `aggregateRating.ratingValue`, fallback `input[name="rating"]`
- **Shop icon**: `<img class="shop-icon-external">` → largest from `srcset`, fallback `src`

---

## Image URLs

- Listing cards serve thumbnails (`il_300x300` or `il_340x270`)
- Replace with `il_fullxfull` for high-res

---

## Fields That Can Be Empty

- **Star Rating**: New shops/products have no rating — normal, use empty string
- **Price**: Should never be empty — skip the card if it is
- **Phone / Website** (directory): Always `"N/A"` for Etsy shops

---

## Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Using `/search?q=` instead of `/c/` | Always use `/c/` paths for geo-filtering |
| Short waits (< 5s) | Use 6-9s random waits |
| No global dedup | Global `seen_urls` set |
| Fetching shop name for every card | Prioritize ad cards first |
| Forgetting to run shops scraper | Always run etsy_shops.py after etsy_products.py |
| Storing price with `$` | Plain number, format in Excel |
| Reusing Fashion sub-categories for new category | Research `/c/` paths fresh each time |
