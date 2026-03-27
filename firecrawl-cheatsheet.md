# Firecrawl MCP Cheat Sheet

## Tool Decision Tree

```
Need web data?
├── Know the exact URL?
│   ├── Single page → firecrawl_scrape
│   └── Multiple pages / whole site → firecrawl_crawl
├── Don't know which URL has the info?
│   ├── Quick keyword search → firecrawl_search
│   └── Find pages within a known site → firecrawl_map → then firecrawl_scrape
├── Need the same structured data from several URLs → firecrawl_extract
├── Complex multi-source research (no clear URL) → firecrawl_agent
└── Need to interact with a live browser (login, click, forms) → firecrawl_browser_*
```

---

## 1. `firecrawl_scrape` — Single Page Extraction

**Default tool.** Use this first whenever you know the URL.

### Format Selection (critical)

| Use `json` when... | Use `markdown` when... |
|--------------------|------------------------|
| Extracting specific fields (price, name, specs) | Reading a full article or blog post |
| API parameters, structured data | Summarizing entire page content |
| Lists of items or properties | User explicitly wants full page |

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `url` | string | Target URL *(required)* |
| `formats` | array | `["markdown"]`, `["json"]`, `["links"]`, `["screenshot"]`, `["branding"]`, etc. |
| `onlyMainContent` | bool | Strip nav/footer/ads |
| `waitFor` | number | ms to wait for JS to render (e.g. `5000`) |
| `maxAge` | number | Use cached result — up to 5× faster |
| `proxy` | string | `"basic"` / `"stealth"` / `"enhanced"` / `"auto"` |
| `mobile` | bool | Simulate mobile viewport |
| `jsonOptions` | object | `prompt` + `schema` for structured extraction |
| `actions` | array | Browser actions before scraping (click, scroll, type…) |

### Examples

```json
// Full article as markdown
{
  "url": "https://example.com/article",
  "formats": ["markdown"],
  "onlyMainContent": true
}

// Structured data extraction with schema
{
  "url": "https://example.com/pricing",
  "formats": ["json"],
  "jsonOptions": {
    "prompt": "Extract all pricing plans with name, price, and features",
    "schema": {
      "type": "object",
      "properties": {
        "plans": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name":     { "type": "string" },
              "price":    { "type": "string" },
              "features": { "type": "array", "items": { "type": "string" } }
            }
          }
        }
      }
    }
  }
}

// JS-heavy SPA — wait for render
{
  "url": "https://spa-site.com/dashboard",
  "formats": ["markdown"],
  "waitFor": 5000
}

// Extract brand identity (colors, fonts, UI)
{
  "url": "https://example.com",
  "formats": ["branding"]
}

// Fast scrape using cache
{
  "url": "https://example.com",
  "formats": ["markdown"],
  "maxAge": 3600000
}
```

### Fallback Strategy (when scrape returns empty/bad content)
1. Add `"waitFor": 5000` — page may need JS to render
2. Try the base URL instead of a hash-fragment URL (`#section`)
3. Use `firecrawl_map` with `search` to find the correct page URL
4. Last resort: `firecrawl_agent`

---

## 2. `firecrawl_search` — Web Search

Search the web and optionally scrape results. Supports operators.

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `query` | string | Search query *(required)* |
| `limit` | number | Max results |
| `sources` | array | `[{ "type": "web" }]`, `"images"`, `"news"` |
| `scrapeOptions` | object | Auto-scrape results (keep `limit` ≤ 5) |

### Search Operators

| Operator | Example | Effect |
|----------|---------|--------|
| `""` | `"exact phrase"` | Exact string match |
| `-` | `-site:reddit.com` | Exclude domain/keyword |
| `site:` | `site:docs.python.org` | Limit to domain |
| `intitle:` | `intitle:tutorial` | Word must be in page title |
| `inurl:` | `inurl:api` | Word must be in URL |

### Examples

```json
// Basic search (preferred — get URLs first, then scrape selectively)
{
  "query": "Claude API rate limits 2024",
  "limit": 5,
  "sources": [{ "type": "web" }]
}

// News search
{
  "query": "AI regulation EU 2024",
  "limit": 10,
  "sources": [{ "type": "news" }]
}

// Search + auto-scrape top results (keep limit low)
{
  "query": "firecrawl MCP setup guide",
  "limit": 3,
  "sources": [{ "type": "web" }],
  "scrapeOptions": {
    "formats": ["markdown"],
    "onlyMainContent": true
  }
}
```

**Optimal workflow:** Search without `scrapeOptions` → get URLs → call `firecrawl_scrape` on the relevant ones.

---

## 3. `firecrawl_map` — Discover URLs on a Site

Returns all indexed URLs on a domain. Fast and cheap — use it to find the right page before scraping.

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `url` | string | Root URL to map *(required)* |
| `search` | string | Filter returned URLs by keyword |
| `limit` | number | Max URLs to return |
| `includeSubdomains` | bool | Include subdomains |
| `sitemap` | string | `"include"` / `"skip"` / `"only"` |

### Examples

```json
// Map entire site
{ "url": "https://docs.example.com" }

// Find pages related to a topic
{
  "url": "https://docs.example.com",
  "search": "authentication",
  "limit": 20
}
```

**Key use case:** `firecrawl_scrape` on `/api-docs` returns empty → run `firecrawl_map` with `search: "webhook"` → get the exact URL `/api-docs/webhooks` → scrape that page directly.

---

## 4. `firecrawl_crawl` — Multi-Page Crawl (Async)

Crawls a site section, extracting content from every discovered page. Returns a **job ID** — poll with `firecrawl_check_crawl_status`.

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `url` | string | Start URL *(required)* |
| `maxDiscoveryDepth` | number | How many link levels deep to follow |
| `limit` | number | Max pages to crawl |
| `includePaths` | array | Only crawl these path patterns |
| `excludePaths` | array | Skip these path patterns |
| `allowExternalLinks` | bool | Follow links off-domain |
| `deduplicateSimilarURLs` | bool | Skip near-duplicate URLs |
| `scrapeOptions` | object | Format/extraction options applied to each page |
| `sitemap` | string | `"include"` / `"skip"` / `"only"` |

### Example

```json
{
  "url": "https://example.com/blog",
  "maxDiscoveryDepth": 2,
  "limit": 20,
  "allowExternalLinks": false,
  "deduplicateSimilarURLs": true,
  "scrapeOptions": {
    "formats": ["markdown"],
    "onlyMainContent": true
  }
}
```

> **Warning:** Keep `limit` ≤ 20 and `maxDiscoveryDepth` ≤ 3 to avoid token overflow. For large sites, prefer `firecrawl_map` + targeted `firecrawl_scrape` calls.

---

## 5. `firecrawl_check_crawl_status` — Poll Crawl Progress

```json
{ "id": "your-crawl-job-id" }
```

Returns status (`scraping` / `completed` / `failed`), page count, and results so far.

---

## 6. `firecrawl_extract` — Structured Extraction Across Multiple URLs

Extract the same data schema from a list of pages in one call.

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `urls` | array | List of URLs *(required)* |
| `prompt` | string | What to extract |
| `schema` | object | JSON schema for output |
| `enableWebSearch` | bool | Allow web search for extra context |
| `allowExternalLinks` | bool | Follow external links |

### Example

```json
{
  "urls": [
    "https://company-a.com/about",
    "https://company-b.com/about"
  ],
  "prompt": "Extract company name, founding year, and CEO",
  "schema": {
    "type": "object",
    "properties": {
      "company": { "type": "string" },
      "founded": { "type": "string" },
      "ceo":     { "type": "string" }
    }
  }
}
```

---

## 7. `firecrawl_agent` — Autonomous Research Agent (Async)

An AI agent that independently browses, searches, and gathers information. Returns a **job ID** immediately — poll with `firecrawl_agent_status`.

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `prompt` | string | Natural language research task *(required, max 10k chars)* |
| `urls` | array | Optional URLs to focus on |
| `schema` | object | Optional JSON schema for structured output |

### Polling with `firecrawl_agent_status`

```json
{ "id": "your-agent-job-id" }
```

| Status | Action |
|--------|--------|
| `processing` | Keep polling (every 15–30s) |
| `completed` | Retrieve results |
| `failed` | Stop |

Poll for **at least 2–3 minutes** before giving up. Complex research can take 5+ minutes.

### Example

```json
{
  "prompt": "Find the top 5 open-source LLM frameworks from 2024, their GitHub stars, and primary use case",
  "schema": {
    "type": "object",
    "properties": {
      "frameworks": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name":     { "type": "string" },
            "stars":    { "type": "string" },
            "use_case": { "type": "string" }
          }
        }
      }
    }
  }
}
```

**Use the agent when:** You don't know which URLs to target, the topic spans many sites, or `map` + `scrape` has already failed.

---

## 8. Browser Tools — Live Browser Automation

For pages that require login, form fills, clicks, or heavy JS interaction.

### Workflow

```
firecrawl_browser_create → firecrawl_browser_execute (repeat) → firecrawl_browser_delete
```

### `firecrawl_browser_create`

```json
{
  "ttl": 300,
  "profile": { "name": "my-session", "saveChanges": true }
}
```

Returns: `sessionId`, CDP URL, live view URL. Use `profile` to persist cookies/localStorage across sessions.

### `firecrawl_browser_execute`

Runs `bash` (agent-browser), `python` (Playwright), or `node`.

#### Common agent-browser bash commands

```bash
agent-browser open https://example.com      # Navigate to URL
agent-browser snapshot                      # Accessibility tree with clickable refs
agent-browser snapshot -i -c               # Interactive elements only, compact
agent-browser click @e5                    # Click element by ref from snapshot
agent-browser type @e3 "search term"       # Type into element
agent-browser fill @e3 "value"             # Clear then fill element
agent-browser get text @e1                 # Get element text
agent-browser get title                    # Current page title
agent-browser get url                      # Current URL
agent-browser screenshot                   # Take screenshot
agent-browser scroll down                  # Scroll page
agent-browser wait 2000                    # Wait 2 seconds
agent-browser --help                       # Full command reference
```

#### Python / Playwright example

```json
{
  "sessionId": "abc123",
  "code": "await page.goto('https://example.com')\nawait page.fill('#email', 'user@example.com')\nawait page.fill('#password', 'secret')\nawait page.click('#login-btn')\nprint(await page.title())",
  "language": "python"
}
```

### `firecrawl_browser_list`

```json
{ "status": "active" }
```

### `firecrawl_browser_delete`

```json
{ "sessionId": "abc123" }
```

---

## Quick Reference

### All Scrape Formats

| Format | Description |
|--------|-------------|
| `markdown` | Clean markdown — best for LLM consumption |
| `html` | Cleaned HTML |
| `rawHtml` | Unprocessed HTML |
| `json` | Structured extraction (requires `jsonOptions`) |
| `links` | All hyperlinks on the page |
| `screenshot` | PNG snapshot |
| `summary` | Short AI-generated summary |
| `branding` | Colors, fonts, spacing, UI components |
| `changeTracking` | Detect page changes over time |

### Proxy Options

| Value | Use case |
|-------|---------|
| `basic` | Default, fast |
| `stealth` | Bypass basic bot detection |
| `enhanced` | Stronger anti-bot bypass |
| `auto` | Let Firecrawl choose |

### Performance Tips

- Use `maxAge` on `firecrawl_scrape` to hit cache and get results ~5× faster
- Search without `scrapeOptions` first, then scrape only the URLs you need
- Keep crawl limits low (`maxDiscoveryDepth` ≤ 3, `limit` ≤ 20)
- Prefer `map` + targeted `scrape` over full `crawl` for large sites
- Use `onlyMainContent: true` to strip boilerplate and reduce token usage
