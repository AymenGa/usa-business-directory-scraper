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
