# Yelp Scraping Reference

Yelp-specific patterns and gotchas. For general scraping logic (bot protection, CAPTCHA, crash recovery, Chrome setup, dedup, delays), see [CLAUDE.md](../CLAUDE.md).

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

## Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Trusting search page categories | Always verify on detail page |
| Wrong partial match direction | Reject keywords as substrings of category, not reverse |
| Saving progress separately from data | Save both atomically |
| Errored cities marked done with no data | Use try/except per city + driver health checks |
| Headless mode | Yelp blocks it instantly |
| Not capturing new driver from fetch_page | Always: `html, driver = fetch_page(driver, url)` |
